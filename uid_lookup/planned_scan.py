"""Run bounded scans against an explicit, validated backfill plan."""

from uid_lookup.bounded_scan import SEARCH_PATH, scan_wazuh
from uid_lookup.checkpoint import make_plan


def scan_planned_slice(
    request,
    plan,
    slice_id,
    *,
    page_size=100,
    max_documents=2000,
):
    if not isinstance(plan, dict):
        raise ValueError("Invalid backfill plan")

    if plan != make_plan(
        plan.get("source_indices"),
        plan.get("slices"),
    ):
        raise ValueError("Backfill plan mismatch")

    if (
        type(slice_id) is not int
        or not 0 <= slice_id < plan["slices"]
    ):
        raise ValueError("Invalid slice ID")

    source_indices = plan["source_indices"]
    allowed = set(source_indices)

    search_path = (
        "/" + ",".join(source_indices)
        + "/_search?scroll=1m"
    )

    def scoped_request(method, path, body):
        if method == "POST" and path == SEARCH_PATH:
            query = dict(body)

            query["slice"] = {
                "id": slice_id,
                "max": plan["slices"],
            }

            return request(method, search_path, query)

        return request(method, path, body)

    result = scan_wazuh(
        scoped_request,
        page_size=page_size,
        max_documents=max_documents,
    )

    for record in result["records"]:
        source = record["_source"]

        if source["source_index"] not in allowed:
            raise ValueError(
                "Document outside planned source indices"
            )

    return result
