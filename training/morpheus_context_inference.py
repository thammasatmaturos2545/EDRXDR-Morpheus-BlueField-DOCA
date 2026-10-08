"""Project-local Morpheus adapter for experimental single-logit Wazuh severity.

No package patches, pickle model loading, or sigmoid inside the saved model.
Use preprocessing with the uncased hash, lowercasing, special tokens, truncation,
feature_length=256 and column='text_input'. Input text must follow the v2 builder.
"""
import json
from pathlib import Path

import cupy as cp
import torch
from transformers import AutoModelForSequenceClassification

from morpheus.messages.memory.tensor_memory import TensorMemory
from morpheus.stages.inference.pytorch_inference_stage import (
    PyTorchInferenceStage,
    _PyTorchInferenceWorker,
)


class ContextSeverityWorker(_PyTorchInferenceWorker):
    def init(self):
        checkpoint = Path(self._model_filename)
        if not (checkpoint / "RUN_COMPLETE").is_file():
            raise ValueError("Incomplete v2 checkpoint")
        report = json.loads((checkpoint / "training_report.json").read_text())
        if report.get("smoke") is not False or report.get("max_length") != self._seq_length:
            raise ValueError("Require full-training checkpoint and matching sequence length")
        if report.get("experiment") != "wazuh-severity-context-v2":
            raise ValueError("Wrong checkpoint experiment")
        if not (checkpoint / "model.safetensors").is_file():
            raise ValueError("Expected local safetensors weights")
        self._model = AutoModelForSequenceClassification.from_pretrained(
            checkpoint, local_files_only=True, use_safetensors=True
        ).to("cuda").eval()
        if self._model.config.num_labels != 1:
            raise ValueError("Expected one logit per event")
        self._use_bf16 = bool(report.get("bf16")) and torch.cuda.is_bf16_supported()

    def calc_output_dims(self, msg):
        # Fixed architecture: avoid the upstream random token/dictionary probe.
        return (msg.tensor_count(), 1)

    def process(self, batch, callback):
        ids = batch.tensors().get_tensor("input_ids")
        mask = batch.tensors().get_tensor("input_mask")
        if ids.ndim != 2 or ids.shape != mask.shape or ids.shape[1] != self._seq_length:
            raise ValueError("Unexpected token tensor shape")
        if ids.shape[0] != batch.tensor_count():
            raise ValueError("Tensor count mismatch")
        # DLPack passes GPU memory directly; integer tensors retain token IDs.
        input_ids = torch.utils.dlpack.from_dlpack(cp.asarray(ids, dtype=cp.int64))
        attention_mask = torch.utils.dlpack.from_dlpack(cp.asarray(mask, dtype=cp.int64))
        if input_ids.numel() and (input_ids.min().item() < 0 or
                                  input_ids.max().item() >= self._model.config.vocab_size):
            raise ValueError("Token ID outside vocabulary")
        if not ((attention_mask == 0) | (attention_mask == 1)).all().item():
            raise ValueError("Attention mask must contain only zero or one")
        if not (attention_mask.sum(dim=1) > 0).all().item():
            raise ValueError("Attention mask contains an entirely masked row")
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=self._use_bf16):
            logits = self._model(input_ids=input_ids, token_type_ids=None,
                                 attention_mask=attention_mask).logits.float()
        if logits.shape != (batch.tensor_count(), 1):
            raise ValueError(f"Output shape mismatch: actual={tuple(logits.shape)}, "
                             f"expected={(batch.tensor_count(), 1)}, input_shape={tuple(input_ids.shape)}")
        if not torch.isfinite(logits).all().item():
            details = dict(error="nonfinite_model_logits", input_shape=list(input_ids.shape),
                           output_shape=list(logits.shape), bf16=self._use_bf16,
                           nonfinite_count=int((~torch.isfinite(logits)).sum().item()),
                           mask_token_counts=attention_mask.sum(dim=1).tolist(),
                           token_id_min=int(input_ids.min().item()), token_id_max=int(input_ids.max().item()))
            frame = batch.payload().get_data()
            if "audit_id" in frame.columns:
                details["payload_audit_ids"] = frame["audit_id"].to_arrow().to_pylist()
            raise ValueError(json.dumps(details))
        probs = logits.sigmoid().contiguous()
        callback(TensorMemory(count=batch.tensor_count(), tensors={"probs": cp.from_dlpack(probs)}))


class ContextSeverityInferenceStage(PyTorchInferenceStage):
    """Experimental offline stage; checkpoint is a directory, not a pickle file."""
    def __init__(self, c, checkpoint):
        if c.feature_length != 256:
            raise ValueError("v2 requires feature_length=256")
        super().__init__(c, Path(checkpoint))

    def _get_inference_worker(self, inf_queue):
        return ContextSeverityWorker(inf_queue, self._config, self._model_filename)

    def supports_cpp_node(self):
        return False
