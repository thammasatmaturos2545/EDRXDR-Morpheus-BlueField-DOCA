import tempfile
import unittest
from pathlib import Path

from uid_lookup.bulk_payload import TARGET_INDEX
from uid_lookup.checkpoint import make_plan
from uid_lookup.lookup_docs import build_lookup_doc
from uid_lookup.verified_checkpoint import commit_verified_slice


INDEX = "wazuh-alerts-4.x-2026.10.15"


def lookup(document_id):
    return build_lookup_doc({
        "_index": INDEX,
        "_id": document_id,
        "_source": {
            "manager": {"name": "manager"},
            "agent": {"id": "001"},
            "id": document_id,
        },
    })


def bulk_response(records, status=201):
    items = []

    for record in records:
        item = {
            "_index": TARGET_INDEX,
            "_id": record["_id"],
            "status": status,
        }

        if status == 201:
            item["result"] = "created"
        else:
            item["error"] = {
                "type": "version_conflict_engine_exception"
            }

        items.append({"create": item})

    return {
        "errors": status != 201,
        "items": items,
    }


def scan(records, complete=True, rejected=0):
    return {
        "records": records,
        "scanned": len(records) + rejected,
        "rejected": rejected,
        "complete": complete,
    }


class TestVerifiedCheckpoint(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "checkpoint.json"
        self.plan = make_plan([INDEX], slices=32)
        self.row = lookup("event-1")

    def commit(self, result, batches, fetch=lambda _: None):
        return commit_verified_slice(
            self.path,
            self.plan,
            0,
            result,
            batches,
            fetch,
        )

    def test_verified_creation(self):
        rows = [self.row]

        state = self.commit(
            scan(rows),
            [{
                "records": rows,
                "response": bulk_response(rows),
            }],
        )

        self.assertEqual(
            state["completed"]["0"]["created"], 1
        )

    def test_verified_existing(self):
        rows = [self.row]

        existing = {
            "found": True,
            "_index": TARGET_INDEX,
            "_id": self.row["_id"],
            "_source": dict(self.row["_source"]),
        }

        state = self.commit(
            scan(rows),
            [{
                "records": rows,
                "response": bulk_response(rows, 409),
            }],
            lambda _: existing,
        )

        self.assertEqual(
            state["completed"]["0"]["verified_existing"], 1
        )

    def test_incomplete_scan_rejected(self):
        with self.assertRaises(ValueError):
            self.commit(scan([self.row], complete=False), [])

        self.assertFalse(self.path.exists())

    def test_rejected_source_rejected(self):
        with self.assertRaises(ValueError):
            self.commit(scan([self.row], rejected=1), [])

        self.assertFalse(self.path.exists())

    def test_missing_bulk_batch_rejected(self):
        with self.assertRaises(ValueError):
            self.commit(scan([self.row]), [])

        self.assertFalse(self.path.exists())

    def test_duplicate_document_rejected(self):
        rows = [self.row, self.row]

        with self.assertRaises(ValueError):
            self.commit(scan(rows), [])

        self.assertFalse(self.path.exists())

    def test_empty_completed_slice(self):
        state = self.commit(scan([]), [])

        self.assertEqual(
            state["completed"]["0"]["scanned"], 0
        )


if __name__ == "__main__":
    unittest.main()
