"""Commit slice checkpoints only after verified bulk reconciliation."""

from uid_lookup.bulk_reconcile import reconcile_bulk
from uid_lookup.checkpoint import make_plan, mark_complete


def commit_verified_slice(
    path, plan, slice_id, scan_result, batches, fetch_existing
):
    # Ensure the checkpoint is tied to a valid, fixed plan.
    if not isinstance(plan, dict):
        raise ValueError("Invalid backfill plan")

    if plan != make_plan(
        plan.get("source_indices"),
        plan.get("slices"),
    ):
        raise ValueError("Invalid backfill plan")

    if not isinstance(scan_result, dict):
        raise ValueError("Invalid scan result")

    if scan_result.get("complete") is not True:
        raise ValueError("Incomplete slice cannot be checkpointed")

    if scan_result.get("rejected") != 0:
        raise ValueError("Rejected source documents")

    records = scan_result.get("records")
    scanned = scan_result.get("scanned")

    if (
        not isinstance(records, list)
        or type(scanned) is not int
        or scanned != len(records)
    ):
        raise ValueError("Scan count mismatch")

    if not isinstance(batches, list) or not callable(fetch_existing):
        raise ValueError("Invalid bulk verification inputs")

    allowed_indices = set(plan["source_indices"])
    seen_ids = set()

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid lookup record")

        source = record.get("_source")
        if (
            not isinstance(source, dict)
            or source.get("source_index") not in allowed_indices
        ):
            raise ValueError("Source outside backfill plan")

        document_id = record.get("_id")

        if document_id in seen_ids:
            raise ValueError("Duplicate document in slice")

        seen_ids.add(document_id)

    # Validate complete batch coverage BEFORE reconciling anything.
    flattened = []

    for batch in batches:
        if not isinstance(batch, dict):
            raise ValueError("Invalid bulk batch")

        rows = batch.get("records")

        if not isinstance(rows, list) or not rows:
            raise ValueError("Invalid bulk batch records")

        flattened.extend(rows)

    if flattened != records:
        raise ValueError("Bulk batches do not cover exact scan result")

    created = 0
    verified_existing = 0

    for batch in batches:
        result = reconcile_bulk(
            batch["records"],
            batch.get("response"),
            fetch_existing,
        )

        created += result["created"]
        verified_existing += result["verified_existing"]

    if created + verified_existing != scanned:
        raise ValueError("Incomplete reconciliation")

    return mark_complete(
        path,
        plan,
        slice_id,
        scan_complete=True,
        scanned=scanned,
        created=created,
        verified_existing=verified_existing,
    )
