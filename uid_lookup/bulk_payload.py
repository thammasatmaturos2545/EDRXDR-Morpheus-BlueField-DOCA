"""Prepare safe, bounded UID lookup bulk payloads."""

import hashlib
import json
import re

from uid_lookup.lookup_docs import SCHEMA, INDEX_PATTERN

TARGET_INDEX = "edrxdr-wazuh-uid-lookup-v1"

HEX64 = re.compile(r"[0-9a-f]{64}")

FIELDS = {
    "schema_version",
    "event_uid",
    "source_index",
    "source_document_id",
    "production_ready",
    "automated_response_allowed",
}


def build_bulk_payload(records):
    if not isinstance(records, list) or not 1 <= len(records) <= 100:
        raise ValueError("Bulk batch must contain 1-100 records")

    lines = []
    seen = set()

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid lookup record")

        document_id = record.get("_id")
        source = record.get("_source")

        if not isinstance(source, dict) or set(source) != FIELDS:
            raise ValueError("Invalid lookup schema")

        if not isinstance(document_id, str) or not HEX64.fullmatch(document_id):
            raise ValueError("Invalid lookup document ID")

        uid = source["event_uid"]
        index = source["source_index"]
        original_id = source["source_document_id"]

        if not isinstance(uid, str) or not HEX64.fullmatch(uid):
            raise ValueError("Invalid event_uid")

        if not isinstance(index, str) or not INDEX_PATTERN.fullmatch(index):
            raise ValueError("Invalid source index")

        if not isinstance(original_id, str) or not 0 < len(original_id) <= 512:
            raise ValueError("Invalid source document ID")

        reference = "|".join(
            f"{len(v.encode('utf-8'))}:{v}"
            for v in (index, original_id)
        )
        expected_id = hashlib.sha256(reference.encode()).hexdigest()

        if document_id != expected_id:
            raise ValueError("Lookup ID does not match source reference")

        if (
            source["schema_version"] != SCHEMA
            or source["production_ready"] is not False
            or source["automated_response_allowed"] is not False
        ):
            raise ValueError("Invalid safety contract")

        if document_id in seen:
            raise ValueError("Duplicate document within bulk batch")

        seen.add(document_id)

        lines.append(json.dumps({
            "create": {
                "_index": TARGET_INDEX,
                "_id": document_id,
            }
        }, separators=(",", ":")))

        lines.append(json.dumps(
            source, separators=(",", ":")
        ))

    return "\n".join(lines) + "\n"
