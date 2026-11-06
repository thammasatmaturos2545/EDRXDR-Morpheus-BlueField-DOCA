import unittest

from uid_lookup.index_mapping import (
    LOOKUP_INDEX_BODY,
    get_index_definition,
)
from uid_lookup.bulk_payload import (
    TARGET_INDEX,
    FIELDS,
)


class TestIndexMapping(unittest.TestCase):

    def test_index_name(self):
        definition = get_index_definition()

        self.assertEqual(
            definition["index"],
            TARGET_INDEX,
        )

    def test_strict_mapping(self):
        mapping = LOOKUP_INDEX_BODY["mappings"]

        self.assertEqual(mapping["dynamic"], "strict")
        self.assertTrue(mapping["_source"]["enabled"])

    def test_exact_keyword_fields(self):
        props = LOOKUP_INDEX_BODY["mappings"]["properties"]

        self.assertEqual(
            props["event_uid"]["type"],
            "keyword",
        )
        self.assertEqual(
            props["source_index"]["type"],
            "keyword",
        )
        self.assertEqual(
            props["source_document_id"]["type"],
            "keyword",
        )

    def test_minimal_schema(self):
        props = LOOKUP_INDEX_BODY["mappings"]["properties"]

        self.assertEqual(set(props), FIELDS)
        self.assertEqual(
            props["production_ready"]["type"],
            "boolean",
        )
        self.assertEqual(
            props["automated_response_allowed"]["type"],
            "boolean",
        )
        self.assertNotIn("full_log", props)


if __name__ == "__main__":
    unittest.main()
