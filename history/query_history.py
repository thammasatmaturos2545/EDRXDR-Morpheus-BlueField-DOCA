import argparse
import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB = Path(__file__).resolve().parent / "history.sqlite3"
KNOWN_UID = (
    "5062c6e96485f0415cdbeeb57e2e899"
    "f18950aa85d79983b5c5c39591e9e62ef"
)

def query(conn, page=1, limit=100, hours="all", search=""):
    if not 1 <= page <= 10000:
        raise ValueError("Invalid page")
    if not 1 <= limit <= 100:
        raise ValueError("Invalid page size")
    if hours not in ("all", "24", "168", "720"):
        raise ValueError("Invalid time range")
    if len(search) > 128:
        raise ValueError("Search too long")

    filters = []
    params = []

    if hours != "all":
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(hours=int(hours))
        ).isoformat()
        filters.append("timestamp_utc >= ?")
        params.append(cutoff)

    if search:
        escaped = (
            search.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = "%" + escaped + "%"
        columns = (
            "event_uid", "rule_id", "agent_id",
            "agent_name", "description"
        )
        filters.append(
            "(" + " OR ".join(
                f"{column} LIKE ? ESCAPE '\\'"
                for column in columns
            ) + ")"
        )
        params.extend([pattern] * len(columns))

    where = " WHERE " + " AND ".join(filters) if filters else ""

    total = conn.execute(
        "SELECT COUNT(*) FROM events" + where,
        params
    ).fetchone()[0]

    rows = conn.execute(
        """
        SELECT event_key, event_uid, timestamp_utc,
               rule_id, agent_id, agent_name, description
        FROM events
        """
        + where +
        """
        ORDER BY timestamp_utc DESC, event_key DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, (page - 1) * limit]
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": limit,
        "total_pages": math.ceil(total / limit),
        "has_next": page * limit < total,
        "events": [dict(row) for row in rows]
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--hours", default="all")
    parser.add_argument("--search", default="")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if not DB.is_file() or DB.stat().st_size > 256 * 1024 * 1024:
        raise SystemExit("STOP: Invalid database or size limit exceeded")

    from urllib.parse import quote
    uri = "file:" + quote(str(DB)) + "?mode=ro"

    with sqlite3.connect(uri, uri=True, timeout=3) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=2000")

        if args.verify:
            first = query(conn, page=1)
            second = query(conn, page=2)
            last = query(
                conn, page=max(1, first["total_pages"])
            )
            matched = query(
                conn, search=KNOWN_UID
            )

            ids1 = {x["event_key"] for x in first["events"]}
            ids2 = {x["event_key"] for x in second["events"]}

            assert not (ids1 & ids2), "Overlapping pages"
            assert len(matched["events"]) == 1, "UID not found"

            print("=== HISTORY PAGINATION TEST ===")
            print("Total events:", first["total"])
            print("Total pages:", first["total_pages"])
            print("Page 1 count:", len(first["events"]))
            print("Page 2 count:", len(second["events"]))
            print("Last page count:", len(last["events"]))
            print("Pages overlap:", bool(ids1 & ids2))
            print("Known Morpheus UID matches:", matched["total"])
            print("=== PAGINATION TEST PASS ===")
        else:
            result = query(
                conn,
                page=args.page,
                limit=args.limit,
                hours=args.hours,
                search=args.search
            )
            print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
