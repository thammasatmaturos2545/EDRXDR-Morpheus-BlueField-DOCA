"""Finite replay inference using the existing verified Morpheus stages."""
from pathlib import Path


def score_texts(texts, checkpoint, vocab_hash_file):
    if not texts or any(not isinstance(text, str) for text in texts):
        raise ValueError("Expected a nonempty list of strings")
    checkpoint = Path(checkpoint)
    vocab_hash_file = Path(vocab_hash_file)
    if not vocab_hash_file.is_file():
        raise ValueError("Missing vocabulary hash file")

    import numpy as np
    import cudf
    import torch
    from transformers import AutoTokenizer
    from morpheus.config import Config, PipelineModes, ExecutionMode
    from morpheus.pipeline.linear_pipeline import LinearPipeline
    from morpheus.stages.input.in_memory_source_stage import InMemorySourceStage
    from morpheus.stages.preprocess.deserialize_stage import DeserializeStage
    from morpheus.stages.preprocess.preprocess_nlp_stage import PreprocessNLPStage
    from morpheus.stages.output.in_memory_sink_stage import InMemorySinkStage

    # /scripts must be on PYTHONPATH when running the container.
    from check_morpheus_offline import SourceFrames
    from morpheus_bert_special_tokens import BertSpecialTokensStage
    from morpheus_context_inference import ContextSeverityInferenceStage

    tokenizer = AutoTokenizer.from_pretrained(
        checkpoint, local_files_only=True
    )
    if (tokenizer.cls_token_id, tokenizer.sep_token_id,
            tokenizer.pad_token_id) != (101, 102, 0):
        raise ValueError("Unexpected special-token IDs")

    checked = set()

    class CheckTokensStage(InMemorySinkStage):
        @property
        def name(self):
            return "replay-check-tokens"

        def _append_message(self, message):
            frame = message.payload().get_data()
            row_ids = frame["audit_id"].to_arrow().to_pylist()
            batch_texts = frame["text_input"].to_arrow().to_pylist()
            for row_id, text in zip(row_ids, batch_texts):
                if row_id in checked or not 0 <= row_id < len(texts):
                    raise ValueError("Invalid or duplicate input row")
                if text != texts[row_id]:
                    raise ValueError("Input text alignment mismatch")
                checked.add(row_id)

            expected = tokenizer(
                batch_texts, max_length=256, truncation=True,
                padding="max_length", return_tensors="np"
            )
            tensors = message.tensors()
            for actual_name, expected_name in (
                ("input_ids", "input_ids"),
                ("input_mask", "attention_mask"),
            ):
                actual = tensors.get_tensor(actual_name).get()
                if not np.array_equal(actual, expected[expected_name]):
                    raise ValueError("Token/mask parity failed")

            sequences = tensors.get_tensor("seq_ids").get()
            if sequences.shape[0] != len(row_ids):
                raise ValueError("Sequence count mismatch")
            if not np.array_equal(sequences[:, 0], np.arange(len(row_ids))):
                raise ValueError("Sequence mapping mismatch")
            return message

    config = Config()
    config.mode = PipelineModes.NLP
    config.execution_mode = ExecutionMode.GPU
    config.feature_length = 256
    config.num_threads = 1
    config.pipeline_batch_size = 16
    config.model_max_batch_size = 8
    config.class_labels = ["high_severity_score"]

    frame = cudf.DataFrame({
        "audit_id": list(range(len(texts))),
        "text_input": texts,
    })
    pipeline = LinearPipeline(config)
    pipeline.set_source(InMemorySourceStage(
        config, SourceFrames([frame])
    ))
    pipeline.add_stage(DeserializeStage(config))
    pipeline.add_stage(PreprocessNLPStage(
        config, vocab_hash_file=str(vocab_hash_file),
        truncation=True, do_lower_case=True,
        add_special_tokens=False, column="text_input",
    ))
    pipeline.add_stage(BertSpecialTokensStage(config))
    pipeline.add_stage(CheckTokensStage(config))
    pipeline.add_stage(ContextSeverityInferenceStage(config, checkpoint))
    sink = pipeline.add_stage(InMemorySinkStage(config))
    pipeline.run()
    torch.cuda.synchronize()

    scores = {}
    for message in sink.get_messages():
        row_ids = message.payload().get_data()["audit_id"].to_arrow().to_pylist()
        probs = message.tensors().get_tensor("probs").get()
        if probs.shape != (len(row_ids), 1):
            raise ValueError("Invalid output shape")
        for row_id, value in zip(row_ids, probs[:, 0]):
            if row_id in scores or row_id not in checked:
                raise ValueError("Invalid or duplicate output row")
            score = float(value)
            if not np.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid output score")
            scores[row_id] = score

    expected_ids = set(range(len(texts)))
    if checked != expected_ids or set(scores) != expected_ids:
        raise ValueError("Missing input/output rows")
    return [scores[index] for index in range(len(texts))]
