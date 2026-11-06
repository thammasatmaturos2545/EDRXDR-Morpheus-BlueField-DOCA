"""Fail-closed reconciliation for resumed UID lookup bulk writes."""

import json

from uid_lookup.bulk_payload import (
    TARGET_INDEX,
    build_bulk_payload,
)


def same_source(actual, expected):
    if not isinstance(actual, dict):
        return False

    try:
        return json.dumps(
            actual,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) == json.dumps(
            expected,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return False


def reconcile_bulk(records, response, fetch_existing):
    """
    fetch_existing(document_id) must perform a read-only lookup.

    A 409 conflict is accepted only when the existing document
    is verified to be exactly identical.
    """

    build_bulk_payload(records)

    if not callable(fetch_existing):
        raise ValueError("Missing existing-document verifier")

    if (
        not isinstance(response, dict)
        or type(response.get("errors")) is not bool
        or not isinstance(response.get("items"), list)
        or len(response["items"]) != len(records)
    ):
        raise ValueError("Invalid bulk response")

    created = 0
    verified_existing = 0
    had_conflict = False

    for expected, item in zip(records, response["items"]):
        if not isinstance(item, dict) or set(item) != {"create"}:
            raise ValueError("Unexpected bulk operation")

        result = item["create"]

        if (
            not isinstance(result, dict)
            or result.get("_index") != TARGET_INDEX
            or result.get("_id") != expected["_id"]
        ):
            raise ValueError("Bulk identity mismatch")

        status = result.get("status")

        if type(status) is not int:
            raise ValueError("Invalid bulk status")

        if status == 201:
            if (
                result.get("result") != "created"
                or "error" in result
            ):
                raise ValueError("Unconfirmed creation")

            created += 1

        elif status == 409:
            had_conflict = True

            error = result.get("error")

            if (
                not isinstance(error, dict)
                or error.get("type")
                != "version_conflict_engine_exception"
            ):
                raise ValueError("Unexpected conflict type")

            existing = fetch_existing(expected["_id"])

            if (
                not isinstance(existing, dict)
                or existing.get("found") is not True
                or existing.get("_index") != TARGET_INDEX
                or existing.get("_id") != expected["_id"]
                or not same_source(
                    existing.get("_source"),
                    expected["_source"],
                )
            ):
                raise ValueError("Existing document mismatch")

            verified_existing += 1

        else:
            raise ValueError("Unconfirmed bulk operation")

    if response["errors"] is not had_conflict:
        raise ValueError("Inconsistent bulk error flag")

    return {
        "created": created,
        "verified_existing": verified_existing,
    }
