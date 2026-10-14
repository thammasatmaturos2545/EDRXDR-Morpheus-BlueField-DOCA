"""CPU-only tests for live Kafka identity transport."""

import ast
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("normalizer.py")


def load_functions():
    tree = ast.parse(SOURCE.read_text())

    wanted = {
        "utc_now",
        "safe_int",
        "wazuh_event_uid",
        "attach_kafka_source",
        "normalized_kafka_key",
        "normalize_wazuh",
    }

    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in wanted
    ]

    found = {node.name for node in nodes}

    if found != wanted:
        raise RuntimeError(
            f"Unexpected normalizer functions: {found}"
        )

    module = ast.Module(
        body=nodes,
        type_ignores=[],
    )

    ns = {
        "datetime": datetime,
        "timezone": timezone,
        "hashlib": hashlib,
    }

    exec(
        compile(module, str(SOURCE), "exec"),
        ns,
    )

    return ns


class LiveTransportContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_functions()

    def event(self):
        return {
            "timestamp": "2026-10-14T15:01:07.742+0000",
            "id": "1791991000.1541940",
            "manager": {
                "name": "oa-hgx-h100-bu-02",
            },
            "agent": {
                "id": "001",
                "name": "windows-agent",
            },
            "rule": {
                "id": "60137",
                "level": 5,
                "description": "fixture",
            },
        }

    def test_source_coordinates_preserved_exactly(self):
        normalize = self.ns["normalize_wazuh"]
        attach = self.ns["attach_kafka_source"]

        row = attach(
            normalize(self.event()),
            "wazuh-alerts",
            0,
            26009,
        )

        self.assertEqual(
            row["source_topic"],
            "wazuh-alerts",
        )
        self.assertEqual(
            row["source_partition"],
            0,
        )
        self.assertEqual(
            row["source_offset"],
            26009,
        )

    def test_kafka_key_equals_event_uid(self):
        normalize = self.ns["normalize_wazuh"]
        key = self.ns["normalized_kafka_key"]

        row = normalize(self.event())

        self.assertEqual(
            key(row),
            row["event_uid"].encode("ascii"),
        )

    def test_uid_survives_transport_metadata(self):
        normalize = self.ns["normalize_wazuh"]
        attach = self.ns["attach_kafka_source"]

        row = normalize(self.event())
        before = row["event_uid"]

        attach(
            row,
            "wazuh-alerts",
            0,
            123,
        )

        self.assertEqual(
            before,
            row["event_uid"],
        )

    def test_invalid_coordinates_fail_closed(self):
        attach = self.ns["attach_kafka_source"]

        for args in (
            ({}, "", 0, 1),
            ({}, "wazuh-alerts", -1, 1),
            ({}, "wazuh-alerts", True, 1),
            ({}, "wazuh-alerts", 0, -1),
            ({}, "wazuh-alerts", 0, False),
        ):
            with self.assertRaises(ValueError):
                attach(*args)

    def test_bad_uid_cannot_become_kafka_key(self):
        key = self.ns["normalized_kafka_key"]

        with self.assertRaises(ValueError):
            key({"event_uid": "bad"})

    def test_non_identity_event_may_have_no_key(self):
        key = self.ns["normalized_kafka_key"]

        self.assertIsNone(
            key({
                "source_type": "bluefield"
            })
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
