"""Bounded, read-only Wazuh Indexer scanner."""

from uid_lookup.lookup_docs import build_lookup_doc

SEARCH_PATH = "/wazuh-alerts-4.x-*/_search?scroll=1m"
SCROLL_PATH = "/_search/scroll"


def scan_wazuh(request, *, page_size=100, max_documents=2000):
    """
    request(method, path, body) -> parsed JSON.

    Read Wazuh documents in bounded batches.
    Never writes to source indices.
    """
    if type(page_size) is not int or not 1 <= page_size <= 200:
        raise ValueError("Invalid page_size")

    if type(max_documents) is not int or not 1 <= max_documents <= 2000:
        raise ValueError("Invalid max_documents")

    query = {
        "size": min(page_size, max_documents),
        "_source": ["manager.name", "agent.id", "id"],
        "sort": ["_doc"],
        "query": {
            "bool": {
                "filter": [
                    {"exists": {"field": "manager.name"}},
                    {"exists": {"field": "agent.id"}},
                    {"exists": {"field": "id"}},
                ]
            }
        },
    }

    records = []
    scanned = 0
    rejected = 0
    scroll_id = None

    try:
        response = request("POST", SEARCH_PATH, query)

        while True:
            if not isinstance(response, dict):
                raise ValueError("Invalid search response")

            current_id = response.get("_scroll_id")
            if isinstance(current_id, str) and current_id:
                scroll_id = current_id

            shards = response.get("_shards")

            if (
                response.get("timed_out") is not False
                or not isinstance(shards, dict)
                or type(shards.get("total")) is not int
                or shards["total"] < 1
                or type(shards.get("successful")) is not int
                or shards["successful"] < 1
                or type(shards.get("failed")) is not int
                or shards["failed"] != 0
                or type(shards.get("skipped", 0)) is not int
                or shards["successful"] + shards.get("skipped", 0)
                != shards["total"]
            ):
                raise ValueError("Incomplete OpenSearch shard response")

            hits = response["hits"]["hits"]
            if not isinstance(hits, list):
                raise ValueError("Invalid search hits")

            if not hits:
                return {
                    "records": records,
                    "scanned": scanned,
                    "rejected": rejected,
                    "complete": True,
                }

            for hit in hits:
                if scanned >= max_documents:
                    break

                scanned += 1

                try:
                    records.append(build_lookup_doc(hit))
                except ValueError:
                    rejected += 1

            if scanned >= max_documents:
                return {
                    "records": records,
                    "scanned": scanned,
                    "rejected": rejected,
                    "complete": False,
                }

            if not scroll_id:
                raise ValueError("Missing scroll ID")

            response = request(
                "POST",
                SCROLL_PATH,
                {
                    "scroll": "1m",
                    "scroll_id": scroll_id,
                },
            )

    finally:
        if scroll_id:
            request(
                "DELETE",
                SCROLL_PATH,
                {"scroll_id": [scroll_id]},
            )
