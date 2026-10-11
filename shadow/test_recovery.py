"""CPU-only injected failure/retry checks. No sockets, models, Docker or source data.

Runs real publish/index control flow with fake broker/search clients. The validator
is a stub because source-locked replay validators are not in this review archive.
This checks acknowledgement ordering/retry, not schema/parity or real outages.
"""
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import pilot
import runtime
import validation


class Recovery(unittest.TestCase):
    def setUp(self):
        self.document = "test-document"
        self.payload = {"event_uid": "a" * 64, "test_only": True}
        self.row = types.SimpleNamespace(value=lambda: common.encode(self.payload), key=lambda: b"test")
        self.client = types.SimpleNamespace(close=lambda: None)
        self.args = types.SimpleNamespace(kind="severity", limit=1, seconds=1)
        self.index = common.INDEXES["severity"]

    def run_index(self, request, commit):
        with patch.object(validation, "validate", return_value=self.document), \
             patch.object(pilot, "request", side_effect=request), \
             patch.object(runtime, "consumer", return_value=(self.client, "cluster")), \
             patch.object(runtime, "collect", return_value=[self.row]), \
             patch.object(runtime, "commit", side_effect=commit), patch.object(runtime, "report"):
            pilot.index(self.args)

    def ack(self):
        return {"_id": self.document, "_index": self.index, "_shards": {"failed": 0, "successful": 1}}

    def test_incomplete_ack_never_commits(self):
        replies = [None, {}, {"_id": self.document}, {**self.ack(), "_index": "live-index"},
                   {**self.ack(), "_shards": {"failed": 0}},
                   {**self.ack(), "_shards": {"failed": 0, "successful": 0}},
                   {**self.ack(), "_shards": {"failed": 1, "successful": 1}}]
        for reply in replies:
            commits = []
            def request(_path, body=None, method="GET"):
                return (200, {}) if method == "GET" else (201, reply)
            with self.subTest(reply=reply), self.assertRaises(RuntimeError):
                self.run_index(request, lambda *_: commits.append(True))
            self.assertEqual(commits, [])

    def test_write_succeeds_ack_lost_then_retry_overwrites_one_document(self):
        stored, committed, attempts = {}, [], []
        def request(path, body=None, method="GET"):
            if method == "GET": return 200, {}
            stored[path] = body
            attempts.append(path)
            if len(attempts) == 1: raise TimeoutError("synthetic lost acknowledgement")
            return 200, self.ack()
        with self.assertRaises(TimeoutError):
            self.run_index(request, lambda *_: committed.append(True))
        self.assertEqual(committed, [])
        self.run_index(request, lambda *_: committed.append(True))
        self.assertEqual(len(stored), 1)
        self.assertEqual(attempts[0], attempts[1])
        self.assertEqual(committed, [True])

    def test_commit_failure_after_index_ack_is_retriable(self):
        stored, attempts, completed = {}, [], []
        def request(path, body=None, method="GET"):
            if method == "GET": return 200, {}
            stored[path] = body
            return 201, self.ack()
        def commit(*_):
            attempts.append(True)
            if len(attempts) == 1: raise RuntimeError("synthetic commit failure")
            completed.append(True)
        with self.assertRaises(RuntimeError): self.run_index(request, commit)
        self.run_index(request, commit)
        self.assertEqual(len(stored), 1)
        self.assertEqual(completed, [True])

    def test_missing_index_never_opens_consumer(self):
        with patch.object(pilot, "request", side_effect=RuntimeError("missing index")), \
             patch.object(runtime, "consumer") as consumer, self.assertRaises(RuntimeError):
            pilot.index(self.args)
        consumer.assert_not_called()

    def test_lost_publish_ack_can_duplicate_but_never_skip_input(self):
        messages, commits = [], []
        class Producer:
            lost = True
            def produce(self, topic, **kwargs):
                messages.append((topic, kwargs["value"]))
                kwargs["on_delivery"]("timeout" if self.lost else None, None)
            def flush(self, _timeout): return 0
        producer = Producer()
        with self.assertRaises(RuntimeError):
            common.publish_then_commit(producer, common.RAW_TOPIC, b"test", self.payload, lambda: commits.append(1))
        self.assertEqual(commits, [])
        producer.lost = False
        common.publish_then_commit(producer, common.RAW_TOPIC, b"test", self.payload, lambda: commits.append(1))
        self.assertEqual(messages[0], messages[1])
        self.assertEqual(commits, [1])

    def test_scoring_change_requires_parity_not_a_success_flag(self):
        # A source-lock mismatch is a failure; do not rewrite the pin to make tests pass.
        validation.legacy_validator.cache_clear()
        with patch.object(validation, "digest", return_value="0" * 64), self.assertRaises(ValueError):
            validation.legacy_validator("severity")

    def test_cache_config_and_closed_gates(self):
        compose = Path(__file__).with_name("compose.yml").read_text(encoding="utf-8")
        for entry in ("HOME: /tmp", "XDG_CACHE_HOME: /tmp/cache", "CUPY_CACHE_DIR: /tmp/cupy-cache", "CUDA_CACHE_PATH: /tmp/cuda-cache", 'SHADOW_RUN_ALLOWED: "0"', 'SHADOW_GPU_ALLOWED: "0"', 'restart: "no"', 'read_only: true'):
            self.assertIn(entry, compose)
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(RuntimeError):
            runtime.require_enabled()


if __name__ == "__main__":
    unittest.main(verbosity=2)
