import unittest

from uid_lookup.bulk_payload import TARGET_INDEX
from uid_lookup.bulk_reconcile import reconcile_bulk
from uid_lookup.lookup_docs import build_lookup_doc


def record(document_id="doc-1"):
    return build_lookup_doc({
        "_index": "wazuh-alerts-4.x-2026.10.15",
        "_id": document_id,
        "_source": {
            "manager": {"name": "manager"},
            "agent": {"id": "001"},
            "id": "123",
        },
    })


def item(row, status=201):
    data = {
        "_index": TARGET_INDEX,
        "_id": row["_id"],
        "status": status,
    }

    if status == 201:
        data["result"] = "created"
    elif status == 409:
        data["error"] = {
            "type": "version_conflict_engine_exception"
        }

    return {"create": data}


def existing(row):
    return {
        "found": True,
        "_index": TARGET_INDEX,
        "_id": row["_id"],
        "_source": dict(row["_source"]),
    }


class TestBulkReconcile(unittest.TestCase):

    def test_new_document(self):
        row = record()

        result = reconcile_bulk(
            [row],
            {"errors": False, "items": [item(row)]},
            lambda _: None,
        )

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["verified_existing"], 0)

    def test_verified_conflict(self):
        row = record()

        result = reconcile_bulk(
            [row],
            {"errors": True, "items": [item(row, 409)]},
            lambda _: existing(row),
        )

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["verified_existing"], 1)

    def test_conflicting_source_rejected(self):
        row = record()
        old = existing(row)
        old["_source"]["production_ready"] = True

        with self.assertRaises(ValueError):
            reconcile_bulk(
                [row],
                {"errors": True, "items": [item(row, 409)]},
                lambda _: old,
            )

    def test_missing_existing_rejected(self):
        row = record()

        with self.assertRaises(ValueError):
            reconcile_bulk(
                [row],
                {"errors": True, "items": [item(row, 409)]},
                lambda _: {"found": False},
            )

    def test_server_error_rejected(self):
        row = record()

        with self.assertRaises(ValueError):
            reconcile_bulk(
                [row],
                {"errors": True, "items": [item(row, 500)]},
                lambda _: None,
            )

    def test_error_flag_mismatch_rejected(self):
        row = record()

        with self.assertRaises(ValueError):
            reconcile_bulk(
                [row],
                {"errors": False, "items": [item(row, 409)]},
                lambda _: existing(row),
            )

    def test_wrong_document_id_rejected(self):
        row = record()
        bad = item(row)
        bad["create"]["_id"] = "wrong"

        with self.assertRaises(ValueError):
            reconcile_bulk(
                [row],
                {"errors": False, "items": [bad]},
                lambda _: None,
            )


if __name__ == "__main__":
    unittest.main()
