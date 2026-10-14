"""CPU-only contract tests for live Wazuh identity."""

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
        "normalize_wazuh",
    }

    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in wanted
    ]

    found = {
        node.name
        for node in functions
    }

    if found != wanted:
        raise RuntimeError(
            f"Unexpected normalizer functions: {found}"
        )

    module = ast.Module(
        body=functions,
        type_ignores=[],
    )

    namespace = {
        "datetime": datetime,
        "timezone": timezone,
        "hashlib": hashlib,
    }

    exec(
        compile(
            module,
            str(SOURCE),
            "exec",
        ),
        namespace,
    )

    return namespace


class LiveIdentityContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_functions()

    def event(self, event_id="1791990450.1539281"):
        return {
            "timestamp": "2026-10-14T15:01:07.742+0000",
            "id": event_id,
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

    def test_identity_is_stable(self):
        fn = self.ns["wazuh_event_uid"]

        first = fn(self.event())
        second = fn(self.event())

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_normalized_event_contains_same_uid(self):
        fn = self.ns["wazuh_event_uid"]
        normalize = self.ns["normalize_wazuh"]

        event = self.event()

        self.assertEqual(
            normalize(event)["event_uid"],
            fn(event),
        )

    def test_different_event_id_changes_uid(self):
        fn = self.ns["wazuh_event_uid"]

        self.assertNotEqual(
            fn(self.event("1791990450.1")),
            fn(self.event("1791990450.2")),
        )

    def test_same_timestamp_does_not_force_match(self):
        fn = self.ns["wazuh_event_uid"]

        left = self.event("one")
        right = self.event("two")

        self.assertEqual(
            left["timestamp"],
            right["timestamp"],
        )

        self.assertNotEqual(
            fn(left),
            fn(right),
        )

    def test_missing_identity_fails_closed(self):
        fn = self.ns["wazuh_event_uid"]

        event = self.event()
        del event["id"]

        with self.assertRaises(ValueError):
            fn(event)


if __name__ == "__main__":
    unittest.main(verbosity=2)
