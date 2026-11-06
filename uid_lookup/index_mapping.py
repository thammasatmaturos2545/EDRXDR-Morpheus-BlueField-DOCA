"""Dedicated OpenSearch mapping for exact Wazuh UID lookup."""

from uid_lookup.bulk_payload import TARGET_INDEX

LOOKUP_INDEX_BODY = {
    "mappings": {
        "dynamic": "strict",
        "_source": {
            "enabled": True
        },
        "properties": {
            "schema_version": {
                "type": "keyword"
            },
            "event_uid": {
                "type": "keyword"
            },
            "source_index": {
                "type": "keyword"
            },
            "source_document_id": {
                "type": "keyword",
                "ignore_above": 2048
            },
            "production_ready": {
                "type": "boolean"
            },
            "automated_response_allowed": {
                "type": "boolean"
            }
        }
    }
}


def get_index_definition():
    return {
        "index": TARGET_INDEX,
        "body": LOOKUP_INDEX_BODY
    }
