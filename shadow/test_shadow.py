"""CPU-only contract/failure tests. Kafka, Torch and GPU are not required.

Replay validators are AST-loaded as pure functions without their Kafka imports.
This is explicitly NOT a Kafka/Morpheus integration test.
"""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shadow"))
import common
import runtime
import validation
import pilot


def load_pure_validator(name):
    tree = ast.parse((ROOT / "replay" / (name + ".py")).read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"validate", "valid_number"}]
    mod = types.ModuleType(name)
    mod.__dict__.update(hashlib=hashlib, json=json, math=math, re=re, HASH_RE=re.compile(r"[0-9a-f]{64}"))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), name, "exec"), mod.__dict__)
    return mod


class Producer:
    def __init__(self, error=None, remaining=0, callback=True, crash=False):
        self.error, self.remaining, self.callback, self.crash = error, remaining, callback, crash
        self.sent = []

    def produce(self, topic, **kwargs):
        if self.crash:
            raise RuntimeError("injected send failure")
        self.sent.append(topic)
        if self.callback:
            kwargs["on_delivery"](self.error, None)

    def flush(self, timeout):
        return self.remaining


def sample():
    raw = dict(manager={"name": "synthetic-manager"}, agent={"id": "1"}, id="synthetic-1",
               rule={"id": "2901", "level": 3, "description": "synthetic"}, full_log="synthetic")
    value = json.dumps(raw, indent=2).encode()
    return common.envelope(value, "source-cluster", "wazuh-alerts", 0, 123, 1234), raw, value


def severity():
    env, raw, _ = sample()
    out = common.result_fields(env, "severity")
    out.update(model_name="test", text_contract_version="wazuh-context-v2-raw-1",
               high_severity_score=0.9, threshold=0.5, predicted_label="high_severity",
               wazuh_rule_id="2901", wazuh_rule_level=3,
               artifact_hashes={key: "a" * 64 for key in (
                   "checkpoint_weights_sha256", "adapter_sha256", "preprocessing_adapter_sha256",
                   "raw_adapter_sha256", "text_builder_sha256")},
               vocab_hash_sha256="b" * 64, engine_sha256="c" * 64, worker_sha256="d" * 64,
               weak_label_disagreement=True, false_positive_candidate=True)
    return out


def behavior():
    env, _, _ = sample()
    out = common.result_fields(env, "behavioral")
    out.update(model_version="behavioral-v1.4", analysis_state="insufficient_feature_diversity",
               routing_status="local_model", train_cohort_support=240,
               ae_reconstruction_error=None, ae_threshold=None, ae_ratio=None, ae_anomaly=None,
               semantic_novelty=False, command_class="missing", command_class_train_support=240,
               package_argument_count=0, wazuh_rule_id="2901", wazuh_rule_level=3,
               runtime_manifest_sha256="a" * 64, model_sha256=None, ae_scored=False)
    return out


class Contracts(unittest.TestCase):
    def test_validators_without_kafka_dependency(self):
        import builtins
        real_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split('.')[0] in {"kafka", "confluent_kafka", "indexer_replay", "behavioral_indexer"}:
                raise ModuleNotFoundError(name)
            return real_import(name, *args, **kwargs)
        validation.legacy_validator.cache_clear()
        with patch.object(builtins, "__import__", side_effect=guarded):
            for kind, event in (("severity", severity()), ("behavioral", behavior())):
                self.assertTrue(validation.validate(kind, event, event["event_uid"].encode()))

    def test_validator_source_hash_required(self):
        validation.legacy_validator.cache_clear()
        with patch.object(validation, "digest", return_value="wrong"), self.assertRaises(ValueError):
            validation.legacy_validator("behavioral")

    def test_exact_raw_bytes_and_legacy_uid(self):
        env, raw, value = sample()
        self.assertEqual(env["raw_json"].encode(), value)
        self.assertEqual(common.unpack(env, env["event_uid"].encode()), raw)
        expected = hashlib.sha256(json.dumps(["synthetic-manager", "1", "synthetic-1"]).encode()).hexdigest()
        self.assertEqual(expected, env["event_uid"])

    def test_corrupt_raw_or_key_rejected(self):
        env, _, _ = sample()
        with self.assertRaises(ValueError):
            common.unpack(env, b"wrong")
        env["raw_json"] += " "
        with self.assertRaises(ValueError):
            common.unpack(env, env["event_uid"].encode())

    def test_invalid_identity_and_nonfinite_json(self):
        _, raw, _ = sample()
        raw["id"] = True
        with self.assertRaises(ValueError):
            common.uid(raw)
        with self.assertRaises(ValueError):
            common.strict_json('{"x":NaN}')

    def test_delivery_failure_does_not_commit(self):
        for params in ({"error": "failed"}, {"remaining": 1}, {"callback": False}, {"crash": True}):
            calls = []
            with self.subTest(params=params), self.assertRaises(RuntimeError):
                common.publish_then_commit(Producer(**params), common.RAW_TOPIC, b"key", {}, lambda: calls.append(1))
            self.assertEqual(calls, [])

    def test_commit_only_after_delivery(self):
        producer = Producer()
        calls = []
        common.publish_then_commit(producer, common.RAW_TOPIC, b"key", {}, lambda: calls.append(len(producer.sent)))
        self.assertEqual(calls, [1])

    def test_nonshadow_destinations_rejected_before_send(self):
        for topic in ("wazuh-alerts", "morpheus-output", "replay-morpheus-output", "shadow-other"):
            p = Producer()
            with self.assertRaises(ValueError):
                common.publish_then_commit(p, topic, b"key", {}, lambda: self.fail("commit"))
            self.assertEqual(p.sent, [])

    def test_retry_document_id_stable_but_source_occurrences_distinct(self):
        out = severity()
        key = out["event_uid"].encode()
        first = validation.validate("severity", out, key)
        retry = copy.deepcopy(out)
        retry["scored_at_utc"] = "2099-01-01T00:00:00+00:00"
        retry["capture_to_score_ms"] = common.latency_ms(retry["captured_at_utc"], retry["scored_at_utc"])
        self.assertEqual(first, validation.validate("severity", retry, key))
        retry["source"]["offset"] += 1
        self.assertNotEqual(first, validation.validate("severity", retry, key))

    def test_safety_flags_modes_and_raw_fields_rejected(self):
        for field, value in (("processing_mode", "replay"), ("production_ready", True),
                             ("automated_response_allowed", True), ("raw_event", {}),
                             ("high_severity_score", float("nan")), ("false_positive_candidate", False)):
            out = severity()
            out[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validation.validate("severity", out, out["event_uid"].encode())

    def test_not_scored_preserved(self):
        out = behavior()
        self.assertTrue(validation.validate("behavioral", out, out["event_uid"].encode()))
        out["ae_scored"] = True
        with self.assertRaises(ValueError):
            validation.validate("behavioral", out, out["event_uid"].encode())

    def test_no_raw_nested_source(self):
        out = severity()
        out["source"]["full_log"] = "must not be indexed"
        with self.assertRaises(ValueError):
            validation.validate("severity", out, out["event_uid"].encode())

    def test_bounds(self):
        for n, seconds in ((0, 1), (101, 1), (1, 0), (1, 121)):
            with self.assertRaises(ValueError):
                runtime.collect(None, n, seconds)

    def test_gate_defaults_closed(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(RuntimeError):
            runtime.require_enabled()

    def backend(self, target=False):
        names = runtime.REPLAY_TOPICS if target else runtime.LIVE_TOPICS
        return types.SimpleNamespace(cluster_id=runtime.EXPECTED_CLUSTER_ID,
            brokers={1: types.SimpleNamespace(host="kafka" if target else "172.16.30.147",
                                              port=29092 if target else 9092)},
            topics={name: types.SimpleNamespace(error=None) for name in names})

    def test_shared_id_with_verified_deployments_allowed(self):
        source, target = self.backend(), self.backend(True)
        with patch.object(runtime, "metadata", side_effect=[source, target]):
            self.assertEqual(runtime.check_clusters(), (source, target))

    def test_same_broker_on_both_endpoints_rejected(self):
        for meta in (self.backend(), self.backend(True)):
            with patch.object(runtime, "metadata", return_value=meta), self.assertRaises(RuntimeError):
                runtime.check_clusters()

    def test_incorrect_deployment_signatures_rejected(self):
        for target in (False, True):
            endpoint = runtime.TARGET if target else runtime.SOURCE
            for fault in ("id", "host", "missing", "foreign", "error"):
                meta = self.backend(target)
                if fault == "id": meta.cluster_id = "unexpected"
                elif fault == "host": meta.brokers[1].host = "unknown"
                elif fault == "missing": meta.topics.pop(next(iter(meta.topics)))
                elif fault == "foreign": meta.topics["wazuh-alerts" if target else "shadow-wazuh-raw-v1"] = types.SimpleNamespace(error=None)
                else: meta.topics[next(iter(meta.topics))].error = "unavailable"
                with self.subTest(target=target, fault=fault), self.assertRaises(RuntimeError):
                    runtime.validate_backend(endpoint, meta)

    def test_shadow_topics_on_replay_allowed(self):
        meta = self.backend(True)
        meta.topics.update({name: types.SimpleNamespace(error=None) for name in common.TOPICS})
        runtime.validate_backend(runtime.TARGET, meta)

    def test_start_boundary_and_restart_resume(self):
        for saved, capture, expected in ((-1001, True, 20), (12, True, 12), (-1001, False, 5)):
            state = {}
            class Partition:
                def __init__(self, topic, partition):
                    self.topic, self.partition, self.offset, self.error = topic, partition, saved, None
            class Client:
                def __init__(self, config): state["config"] = config
                def committed(self, parts, timeout): return parts
                def get_watermark_offsets(self, p, timeout, cached): return (5, 20)
                def assign(self, parts): state["assigned"] = parts[0].offset
                def commit(self, offsets, asynchronous):
                    state["committed"] = offsets[0].offset
                    return offsets
                def close(self): pass
            lib = types.SimpleNamespace(Consumer=Client, TopicPartition=Partition, OFFSET_INVALID=-1001)
            meta = types.SimpleNamespace(cluster_id="cluster", topics={
                "wazuh-alerts": types.SimpleNamespace(partitions={0: None}),
                common.RAW_TOPIC: types.SimpleNamespace(partitions={0: None})})
            with patch.dict(sys.modules, confluent_kafka=lib), patch.object(runtime, "metadata", return_value=meta), patch.object(runtime, "report"):
                runtime.consumer("capture" if capture else "severity", "wazuh-alerts" if capture else common.RAW_TOPIC, capture=capture)
            self.assertEqual(state["assigned"], expected)
            self.assertEqual(state["committed"], expected)
            self.assertFalse(state["config"]["enable.auto.commit"])
            self.assertEqual(state["config"]["auto.offset.reset"], "error")
            self.assertTrue(state["config"]["group.id"].startswith("edrxdr-shadow-"))

    def test_retention_gap_rejected(self):
        class Partition:
            def __init__(self, topic, partition): self.offset, self.error = 1, None
        class Client:
            def __init__(self, config): pass
            def committed(self, parts, timeout): return parts
            def get_watermark_offsets(self, p, timeout, cached): return (5, 20)
            def close(self): pass
            def commit(self, **kwargs): raise AssertionError("Must not skip lost data")
        lib = types.SimpleNamespace(Consumer=Client, TopicPartition=Partition, OFFSET_INVALID=-1001)
        meta = types.SimpleNamespace(topics={common.RAW_TOPIC: types.SimpleNamespace(partitions={0: None})})
        with patch.dict(sys.modules, confluent_kafka=lib), patch.object(runtime, "metadata", return_value=meta), self.assertRaises(RuntimeError):
            runtime.consumer("severity", common.RAW_TOPIC)

    def test_index_ack_failure_does_not_commit(self):
        out = severity()
        row = types.SimpleNamespace(value=lambda: common.encode(out), key=lambda: out["event_uid"].encode())
        client = types.SimpleNamespace(close=lambda: None)
        args = types.SimpleNamespace(kind="severity", limit=1, seconds=1)
        for reply in ((500, {}), (201, {"_id": "wrong"}),
                      (201, {"_id": validation.validate("severity", out, row.key()), "_shards": {"failed": 1}})):
            with patch.object(pilot, "request", side_effect=[(200, {}), reply]), patch.object(runtime, "consumer", return_value=(client, "id")), patch.object(runtime, "collect", return_value=[row]), patch.object(runtime, "commit") as commit, self.assertRaises(RuntimeError):
                pilot.index(args)
            commit.assert_not_called()

    def test_index_ack_success_commits(self):
        out = severity()
        row = types.SimpleNamespace(value=lambda: common.encode(out), key=lambda: out["event_uid"].encode())
        doc = validation.validate("severity", out, row.key())
        client = types.SimpleNamespace(close=lambda: None)
        args = types.SimpleNamespace(kind="severity", limit=1, seconds=1)
        with patch.object(pilot, "request", side_effect=[(200, {}), (201, {"_id": doc, "_index": common.INDEXES["severity"], "_shards": {"failed": 0, "successful": 1}})]) as request, patch.object(runtime, "consumer", return_value=(client, "id")), patch.object(runtime, "collect", return_value=[row]), patch.object(runtime, "commit") as commit, patch.object(runtime, "report"):
            pilot.index(args)
        commit.assert_called_once_with(client, row)
        self.assertTrue(request.call_args.args[0].startswith("/shadow-severity-v1/_doc/"))

    def test_scored_state_without_evidence_rejected(self):
        out = behavior()
        out["analysis_state"] = "baseline_consistent"
        with self.assertRaises(ValueError):
            validation.validate("behavioral", out, out["event_uid"].encode())


if __name__ == "__main__":
    unittest.main(verbosity=2)
