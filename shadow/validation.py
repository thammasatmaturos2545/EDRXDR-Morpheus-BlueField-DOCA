"""Explicit shadow contract plus the existing replay score validators."""
import ast
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from common import SOURCE_TOPIC, latency_ms, digest


@lru_cache(maxsize=2)
def legacy_validator(kind):
    filename, names = {
        "severity": ("indexer_replay.py", {"validate"}),
        "behavioral": ("behavioral_indexer.py", {"validate", "valid_number"}),
    }[kind]
    relative = "replay/" + filename
    path = Path(__file__).resolve().parents[1] / relative
    lock = json.loads(Path(__file__).with_name("source-lock.json").read_text())
    if digest(path) != lock["sha256"][relative]:
        raise ValueError("Reviewed validator hash mismatch")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(nodes) != len(names) or {node.name for node in nodes} != names:
        raise ValueError("Unexpected validator structure")
    namespace = dict(hashlib=hashlib, json=json, math=math, re=re,
                     HASH_RE=re.compile(r"[0-9a-f]{64}"))
    # Only frozen pure functions, never Kafka imports or the replay main().
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["validate"]

SEVERITY_FIELDS = {
    "model_name", "text_contract_version", "high_severity_score", "predicted_label",
    "threshold", "artifact_hashes", "vocab_hash_sha256", "engine_sha256", "worker_sha256",
    "weak_label_disagreement", "false_positive_candidate",
}
BEHAVIORAL_FIELDS = {
    "model_version", "analysis_state", "routing_status", "train_cohort_support",
    "ae_reconstruction_error", "ae_threshold", "ae_ratio", "ae_anomaly",
    "semantic_novelty", "command_class", "command_class_train_support",
    "package_argument_count", "runtime_manifest_sha256", "model_sha256", "ae_scored",
}
BASE_FIELDS = {
    "schema_version", "processing_mode", "event_uid", "source_type", "source", "raw_sha256",
    "captured_at_utc", "scored_at_utc", "capture_to_score_ms", "production_ready",
    "automated_response_allowed", "wazuh_rule_id", "wazuh_rule_level",
}


def validate(kind, event, key):
    if kind not in ("severity", "behavioral"):
        raise ValueError("Unknown output kind")
    expected_fields = BASE_FIELDS | (SEVERITY_FIELDS if kind == "severity" else BEHAVIORAL_FIELDS)
    if set(event) != expected_fields:
        raise ValueError("Unexpected/missing score fields (raw text forbidden)")
    if event["schema_version"] != f"shadow-{kind}-1" or event["processing_mode"] != "shadow":
        raise ValueError("Expected shadow schema/mode")
    if event["automated_response_allowed"] is not False or event["production_ready"] is not False:
        raise ValueError("Display-only guard violated")
    if not isinstance(event["raw_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", event["raw_sha256"]):
        raise ValueError("Invalid raw hash")
    source = event["source"]
    if set(source) != {"cluster_id", "topic", "partition", "offset", "timestamp_ms"}:
        raise ValueError("Unexpected source fields")
    if source["topic"] != SOURCE_TOPIC or not isinstance(source["cluster_id"], str) or not source["cluster_id"]:
        raise ValueError("Invalid source identity")
    for name in ("partition", "offset"):
        if type(source[name]) is not int or source[name] < 0:
            raise ValueError("Invalid source coordinate")
    if source["timestamp_ms"] is not None and type(source["timestamp_ms"]) is not int:
        raise ValueError("Invalid source timestamp")
    elapsed = event["capture_to_score_ms"]
    if type(elapsed) not in (int, float) or not math.isclose(
        elapsed, latency_ms(event["captured_at_utc"], event["scored_at_utc"]), abs_tol=0.001
    ):
        raise ValueError("Invalid latency")
    level = event["wazuh_rule_level"]
    if level is not None and (type(level) is not int or not 0 <= level <= 15):
        raise ValueError("Invalid Wazuh level")
    if type(event["wazuh_rule_id"]) not in (str, int):
        raise ValueError("Invalid Wazuh rule ID")
    # Compatibility projection ONLY for pure score validation. This copy is never
    # published/indexed and neither replay validator's main() is executed.
    projected = dict(event, schema_version=f"replay-{kind}-1", processing_mode="replay")
    if kind == "severity":
        legacy_validate = legacy_validator(kind)
        h = event["artifact_hashes"]
        required = {"checkpoint_weights_sha256", "adapter_sha256", "preprocessing_adapter_sha256",
                    "raw_adapter_sha256", "text_builder_sha256"}
        if set(h) != required or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for v in h.values()):
            raise ValueError("Invalid artifact hashes")
        for field in ("vocab_hash_sha256", "engine_sha256", "worker_sha256"):
            if not isinstance(event[field], str) or not re.fullmatch(r"[0-9a-f]{64}", event[field]):
                raise ValueError("Invalid source hash")
        for field, expected in {
            "weak_label_disagreement": ((event["high_severity_score"] >= 0.5) != (level >= 7)) if level is not None else None,
            "false_positive_candidate": (event["high_severity_score"] >= 0.5 and level < 7) if level is not None else None,
        }.items():
            if event[field] is not expected:
                raise ValueError("Invalid weak-label comparison")
    else:
        legacy_validate = legacy_validator(kind)
        scored = event["ae_reconstruction_error"] is not None
        if event["ae_scored"] is not scored:
            raise ValueError("Invalid coverage flag")
        if event["analysis_state"] in {"limited_history", "novel_cohort", "fallback_supported",
                                       "insufficient_feature_diversity", "no_temporal_dev_evidence"} and scored:
            raise ValueError("Not-scored state cannot contain AE score")
        if event["analysis_state"] in {"baseline_consistent", "behavioral_anomaly",
                                       "behavioral_anomaly+semantic_novelty", "semantic_novelty"} and not scored:
            raise ValueError("Scored state requires AE evidence")
    model_document = legacy_validate(projected, key)
    # Distinguish source occurrences and raw revisions; retries keep the same ID.
    identity = [event["schema_version"], model_document, source["cluster_id"],
                source["topic"], source["partition"], source["offset"], event["raw_sha256"]]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()
