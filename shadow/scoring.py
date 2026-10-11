"""Reuse frozen scoring functions; do not execute replay entry points."""
from pathlib import Path
import json

from common import digest, result_fields

CHECKPOINT = Path("/models/wazuh-severity-context-v2-balanced-20261008T190719Z-1398863")
PARITY = Path("/models/morpheus-raw-offline-check-20261008T203523Z-1803526/parity_report.json")
VOCAB = Path("/opt/conda/envs/morpheus/lib/python3.12/site-packages/morpheus/data/bert-base-uncased-hash.txt")


def severity(envelopes, raws):
    from raw_event_contract import event_text
    from morpheus_replay_engine import score_texts
    evidence = json.loads(PARITY.read_text())
    if evidence["status"] != "PASS" or evidence["issues"]:
        raise ValueError("Successful parity report required")
    paths = {
        "checkpoint_weights_sha256": CHECKPOINT / "model.safetensors",
        "adapter_sha256": Path("/scripts/morpheus_context_inference.py"),
        "preprocessing_adapter_sha256": Path("/scripts/morpheus_bert_special_tokens.py"),
        "raw_adapter_sha256": Path("/scripts/raw_event_contract.py"),
        "text_builder_sha256": Path("/scripts/build_context_dataset.py"),
    }
    hashes = {key: digest(path) for key, path in paths.items()}
    if any(value != evidence[key] for key, value in hashes.items()):
        raise ValueError("Parity artifact hash mismatch")
    texts = [event_text(raw) for raw in raws]
    # One finite Morpheus pipeline/model initialization for the entire pilot batch.
    scores = score_texts(texts, CHECKPOINT, VOCAB)
    if len(scores) != len(raws):
        raise ValueError("Missing severity results")
    outputs = []
    for item, raw, score in zip(envelopes, raws, scores):
        out = result_fields(item, "severity")
        level = raw["rule"].get("level")
        comparable = type(level) is int and 0 <= level <= 15
        out.update(model_name=CHECKPOINT.name, text_contract_version="wazuh-context-v2-raw-1",
                   high_severity_score=score, threshold=0.5,
                   predicted_label="high_severity" if score >= 0.5 else "low_severity",
                   wazuh_rule_id=raw["rule"].get("id"), wazuh_rule_level=level,
                   artifact_hashes=hashes, vocab_hash_sha256=digest(VOCAB),
                   engine_sha256=digest("/replay/morpheus_replay_engine.py"),
                   worker_sha256=digest(__file__),
                   weak_label_disagreement=(bool(score >= 0.5) != bool(level >= 7)) if comparable else None,
                   false_positive_candidate=(score >= 0.5 and level < 7) if comparable else None)
        outputs.append(out)
    return outputs


def behavioral_one(item, raw, runtime, library, manifest_hash):
    manifest, support, semantic, cohorts, models = runtime
    decoder = str(raw.get("decoder", {}).get("name", "[missing]"))
    location = str(raw.get("location", "[missing]"))
    key = (decoder, location)
    n = support.get(key, 0)
    routing = library.routing_status(n)
    command = raw.get("data", {}).get("command")
    command_cls = library.command_class(command)
    semantic_n = semantic.get((decoder, location, command_cls), 0)
    novel = semantic_n == 0
    error = threshold = ratio = anomaly = model_hash = None
    if routing == "local_model":
        cfg = cohorts.get(key)
        if cfg is None:
            raise ValueError("Local cohort missing runtime policy")
        if cfg.get("runtime_enabled"):
            spec = models[key]
            error, threshold, ratio, anomaly = library.score_model(spec, library.feature_values(raw))
            model_hash = spec["model_sha256"]
            state = ("behavioral_anomaly+semantic_novelty" if anomaly and novel else
                     "behavioral_anomaly" if anomaly else
                     "semantic_novelty" if novel else "baseline_consistent")
        else:
            state = cfg["runtime_reason"]
    else:
        state = routing
    out = result_fields(item, "behavioral")
    out.update(model_version="behavioral-v1.4", analysis_state=state, routing_status=routing,
               train_cohort_support=n, command_class=command_cls,
               command_class_train_support=semantic_n,
               package_argument_count=library.package_count(command),
               ae_reconstruction_error=error, ae_threshold=threshold, ae_ratio=ratio,
               ae_anomaly=anomaly, semantic_novelty=novel, ae_scored=error is not None,
               wazuh_rule_id=raw["rule"].get("id"), wazuh_rule_level=raw["rule"].get("level"),
               runtime_manifest_sha256=manifest_hash, model_sha256=model_hash)
    return out


def behavioral(envelopes, raws):
    import behavioral_replay as library
    runtime = library.load_runtime()  # CPU, once per finite batch; frozen models.
    manifest_hash = digest(library.MANIFEST)
    return [behavioral_one(item, raw, runtime, library, manifest_hash)
            for item, raw in zip(envelopes, raws)]
