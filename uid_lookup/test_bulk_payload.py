import json
import unittest

from uid_lookup.bulk_payload import build_bulk_payload
from uid_lookup.lookup_docs import build_lookup_doc


def sample():
    return build_lookup_doc({
        "_index": "wazuh-alerts-4.x-2026.10.15",
        "_id": "sample-123",
        "_source": {
            "manager": {"name": "manager"},
            "agent": {"id": "001"},
            "id": "123",
            "full_log": "PRIVATE TEST LOG",
        },
    })


class TestBulkPayload(unittest.TestCase):

    def test_create_action(self):
        lines = build_bulk_payload([sample()]).splitlines()

        self.assertEqual(len(lines), 2)
        self.assertIn("create", json.loads(lines[0]))
        self.assertNotIn("index", json.loads(lines[0]))

    def test_no_raw_log(self):
        payload = build_bulk_payload([sample()])
        self.assertNotIn("PRIVATE TEST LOG", payload)

    def test_reject_duplicate(self):
        record = sample()
        with self.assertRaises(ValueError):
            build_bulk_payload([record, record])

    def test_reject_invalid_safety(self):
        record = sample()
        record["_source"]["production_ready"] = True

        with self.assertRaises(ValueError):
            build_bulk_payload([record])

    def test_reject_wrong_lookup_id(self):
        record = sample()
        record["_id"] = "a" * 64

        with self.assertRaises(ValueError):
            build_bulk_payload([record])

    def test_batch_limit(self):
        with self.assertRaises(ValueError):
            build_bulk_payload([])

        with self.assertRaises(ValueError):
            build_bulk_payload([sample()] * 101)


if __name__ == "__main__":
    unittest.main()
