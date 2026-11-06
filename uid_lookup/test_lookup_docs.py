import unittest

from uid_lookup.lookup_docs import build_lookup_doc


def sample_hit(document_id="document-1"):
    return {
        "_index": "wazuh-alerts-4.x-2026.10.15",
        "_id": document_id,
        "_source": {
            "manager": {"name": "manager"},
            "agent": {"id": "001"},
            "id": "123",
            "full_log": "SENSITIVE TEST LOG",
        },
    }


class TestLookupDocs(unittest.TestCase):

    def test_valid_document(self):
        result = build_lookup_doc(sample_hit())

        self.assertEqual(
            result["_source"]["schema_version"],
            "edrxdr-wazuh-uid-lookup-v1"
        )
        self.assertEqual(len(result["_source"]["event_uid"]), 64)
        self.assertFalse(result["_source"]["production_ready"])
        self.assertFalse(
            result["_source"]["automated_response_allowed"]
        )

    def test_deterministic_id(self):
        a = build_lookup_doc(sample_hit())
        b = build_lookup_doc(sample_hit())
        self.assertEqual(a["_id"], b["_id"])

    def test_distinct_documents_preserve_conflicts(self):
        a = build_lookup_doc(sample_hit("document-1"))
        b = build_lookup_doc(sample_hit("document-2"))

        self.assertEqual(
            a["_source"]["event_uid"],
            b["_source"]["event_uid"]
        )
        self.assertNotEqual(a["_id"], b["_id"])

    def test_no_raw_log_copied(self):
        result = build_lookup_doc(sample_hit())
        self.assertNotIn("full_log", result["_source"])
        self.assertNotIn(
            "SENSITIVE TEST LOG",
            str(result)
        )

    def test_invalid_identity_rejected(self):
        hit = sample_hit()
        del hit["_source"]["agent"]["id"]

        with self.assertRaises(ValueError):
            build_lookup_doc(hit)

    def test_invalid_index_rejected(self):
        hit = sample_hit()
        hit["_index"] = "other-index"

        with self.assertRaises(ValueError):
            build_lookup_doc(hit)


if __name__ == "__main__":
    unittest.main()
