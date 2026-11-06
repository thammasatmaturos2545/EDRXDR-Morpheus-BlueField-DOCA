"""Fail-closed validation of OpenSearch bulk create responses."""

from uid_lookup.bulk_payload import (
    TARGET_INDEX,
    build_bulk_payload,
)


def verify_bulk_created(records, response):
    """Return confirmed count only when every create succeeded."""

    # Validate the expected input first.
    build_bulk_payload(records)

    if not isinstance(response, dict):
        raise ValueError("Invalid bulk response")

    if response.get("errors") is not False:
        raise ValueError("Bulk response contains errors")

    items = response.get("items")

    if not isinstance(items, list):
        raise ValueError("Missing bulk items")

    if len(items) != len(records):
        raise ValueError("Bulk response count mismatch")

    for expected, item in zip(records, items):
        if not isinstance(item, dict):
            raise ValueError("Invalid bulk item")

        result = item.get("create")

        if not isinstance(result, dict):
            raise ValueError("Unexpected bulk operation")

        if result.get("_index") != TARGET_INDEX:
            raise ValueError("Unexpected target index")

        if result.get("_id") != expected["_id"]:
            raise ValueError("Bulk document ID mismatch")

        if result.get("status") != 201:
            raise ValueError("Bulk document not created")

        if result.get("result") != "created":
            raise ValueError("Unconfirmed bulk creation")

    return len(records)
