import unittest

from uid_lookup.bulk_payload import TARGET_INDEX
from uid_lookup.bulk_result import verify_bulk_created
from uid_lookup.lookup_docs import build_lookup_doc


def record(doc_id="doc-1"):
    return build_lookup_doc({
        "_index": "wazuh-alerts-4.x-2026.10.15",
        "_id": doc_id,
        "_source": {
            "manager": {"name": "manager"},
            "agent": {"id": "001"},
            "id": "123",
        },
    })


def created(item):
    return {
        "create": {
            "_index": TARGET_INDEX,
            "_id": item["_id"],
            "status": 201,
            "result": "created",
        }
    }


class TestBulkResult(unittest.TestCase):

    def test_success(self):
        rows = [record("a"), record("b")]
        response = {
            "errors": False,
            "items": [created(x) for x in rows],
        }

        self.assertEqual(
            verify_bulk_created(rows, response), 2
        )

    def test_missing_response(self):
        with self.assertRaises(ValueError):
            verify_bulk_created([record()], {})

    def test_count_mismatch(self):
        with self.assertRaises(ValueError):
            verify_bulk_created(
                [record()],
                {"errors": False, "items": []},
            )

    def test_conflict_rejected(self):
        row = record()
        item = created(row)
        item["create"]["status"] = 409

        with self.assertRaises(ValueError):
            verify_bulk_created(
                [row],
                {"errors": True, "items": [item]},
            )

    def test_wrong_id_rejected(self):
        row = record()
        item = created(row)
        item["create"]["_id"] = "wrong-id"

        with self.assertRaises(ValueError):
            verify_bulk_created(
                [row],
                {"errors": False, "items": [item]},
            )

    def test_unconfirmed_creation_rejected(self):
        row = record()
        item = created(row)
        item["create"]["result"] = "updated"

        with self.assertRaises(ValueError):
            verify_bulk_created(
                [row],
                {"errors": False, "items": [item]},
            )


if __name__ == "__main__":
    unittest.main()
