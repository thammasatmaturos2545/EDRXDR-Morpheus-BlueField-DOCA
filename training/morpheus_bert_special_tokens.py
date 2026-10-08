"""Project-local BERT framing after native, explicitly no-special-token preprocessing."""
import cupy as cp
from morpheus.messages.memory.tensor_memory import TensorMemory
from morpheus.stages.output.in_memory_sink_stage import InMemorySinkStage


def frame_bert_tokens(ids, mask, xp=cp):
    """For uncased BERT, truncate body to 254, prepend CLS, append SEP, pad to 256.

    xp is injectable so the exact algorithm can be checked on CPU as well.
    The caller must supply body-only tokens with a binary, right-padded mask.
    """
    if ids.ndim != 2 or ids.shape != mask.shape or ids.shape[1] != 256:
        raise ValueError("Expected body tokens and mask shaped [N,256]")
    if not bool(((mask == 0) | (mask == 1)).all()):
        raise ValueError("Non-binary body mask")
    lengths = mask.sum(axis=1).astype(xp.int64)
    if not bool((mask == (xp.arange(256)[None, :] < lengths[:, None])).all()):
        raise ValueError("Body mask must be right-padded")
    lengths = xp.minimum(lengths, 254)
    result = xp.zeros(ids.shape, dtype=xp.int64)
    result[:, 0] = 101
    result[:, 1:255] = xp.where(xp.arange(254)[None, :] < lengths[:, None], ids[:, :254], 0)
    result[xp.arange(ids.shape[0]), lengths + 1] = 102
    result_mask = (xp.arange(256)[None, :] < (lengths + 2)[:, None]).astype(xp.int64)
    return result, result_mask


class BertSpecialTokensStage(InMemorySinkStage):
    """Pass-through stage: retain row metadata and replace only IDs and mask.

    Restricted to truncation=True, one tensor row per payload row, length 256.
    seq_ids are preserved; downstream non-windowed inference uses their row IDs.
    No messages are retained by this subclass.
    """
    @property
    def name(self):
        return "bert-special-tokens"

    def _append_message(self, message):
        if message.tensor_count() != message.payload().count:
            raise ValueError("Special-token stage requires one sequence per event")
        memory = message.tensors()
        ids, mask = frame_bert_tokens(memory.get_tensor("input_ids"), memory.get_tensor("input_mask"))
        seq_ids = memory.get_tensor("seq_ids")
        if seq_ids.shape[0] != ids.shape[0]:
            raise ValueError("Sequence metadata row count mismatch")
        message.tensors(TensorMemory(count=message.tensor_count(), tensors={
            "input_ids": ids, "input_mask": mask, "seq_ids": seq_ids,
        }))
        return message
