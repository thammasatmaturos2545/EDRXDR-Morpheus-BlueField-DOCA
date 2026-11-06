import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / "nexus-history-preview-20261020"
DB = ROOT / "history.sqlite3"
CONTAINER = "wazuh-wazuh.manager-1"
ACTIVE = "/var/ossec/logs/alerts/alerts.json"

MAX_ACTIVE = 4 * 1024 * 1024
MAX_ARCHIVE = 48 * 1024 * 1024
MAX_LINE = 1024 * 1024
MAX_ROWS = 25000

ARCHIVE_RE = re.compile(
    r"^/var/ossec/logs/alerts/20\d{2}/"
    r"[A-Za-z]{3}/ossec-alerts-\d{2}\.json(?:\.gz)?$"
)

def docker(*args, timeout=20):
    return subprocess.check_output(
        ["docker", "exec", CONTAINER, *args],
        timeout=timeout
    )

def metadata(path):
    raw = docker(
        "stat", "-c", "%i|%s|%y", path
    ).decode().strip()

    inode, size, modified = raw.split("|", 2)
    return inode, int(size), modified

def event_uid(event):
    manager = event.get("manager")
    agent = event.get("agent")

    if (
        not isinstance(manager, dict)
        or not isinstance(agent, dict)
        or manager.get("name") is None
        or agent.get("id") is None
        or event.get("id") is None
    ):
        raise ValueError("Missing Wazuh event identity")

    values = [
        str(manager["name"]),
        str(agent["id"]),
        str(event["id"])
    ]

    encoded = "wazuh-v1|" + "|".join(
        f"{len(v.encode('utf-8'))}:{v}"
        for v in values
    )

    return hashlib.sha256(encoded.encode()).hexdigest()

def parse_line(raw):
    if len(raw) > MAX_LINE:
        raise ValueError("Wazuh event exceeds line limit")

    text = raw.decode("utf-8").strip()

    if not text:
        return None

    event = json.loads(text)

    if not isinstance(event, dict):
        raise ValueError("Invalid Wazuh event")

    uid = event_uid(event)

    timestamp = datetime.fromisoformat(
        str(event["timestamp"]).replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        raise ValueError("Timestamp has no timezone")

    timestamp_utc = timestamp.astimezone(
        timezone.utc
    ).isoformat(timespec="microseconds")

    rule = event.get("rule") or {}
    agent = event["agent"]

    key = hashlib.sha256(
        ("nexus-sync-v1|" + uid).encode()
    ).hexdigest()

    return (
        key,
        uid,
        timestamp_utc,
        str(rule.get("id", "")),
        str(agent.get("id", "")),
        str(agent.get("name", "")),
        str(rule.get("description", "")),
        text
    )

def read_archive(path):
    command = (
        ["gzip", "-cd", path]
        if path.endswith(".gz")
        else ["cat", path]
    )
    proc = subprocess.Popen(
        ["docker", "exec", CONTAINER, *command],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    rows = []
    total_bytes = 0

    try:
        assert proc.stdout is not None

        for raw in proc.stdout:
            total_bytes += len(raw)

            if total_bytes > MAX_ARCHIVE:
                raise ValueError("Archive exceeds size limit")

            row = parse_line(raw)

            if row is not None:
                rows.append(row)

            if len(rows) > MAX_ROWS:
                raise ValueError("Archive exceeds event limit")

        if proc.wait(timeout=15) != 0:
            raise ValueError("Archive decompression failed")

        return rows

    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

def read_active(offset, size):
    count = min(size - offset, MAX_ACTIVE)

    if count <= 0:
        return [], offset

    proc = subprocess.Popen(
        [
            "docker", "exec", CONTAINER,
            "tail", "-c", f"+{offset + 1}", ACTIVE
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    try:
        assert proc.stdout is not None
        raw = proc.stdout.read(count)

    finally:
        if proc.poll() is None:
            proc.terminate()

        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    if len(raw) != count:
        raise ValueError("Active log changed during read")

    complete = raw.rfind(b"\n") + 1

    if complete == 0:
        raise ValueError("No complete line within read limit")

    rows = []

    for line in raw[:complete].splitlines():
        row = parse_line(line)

        if row is not None:
            rows.append(row)

    return rows, offset + complete

def save_source(conn, path, info, offset, completed):
    conn.execute("""
        INSERT INTO history_sync_state
          (path, inode, size, modified, offset, completed)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          inode=excluded.inode,
          size=excluded.size,
          modified=excluded.modified,
          offset=excluded.offset,
          completed=excluded.completed
    """, (
        path, info[0], info[1], info[2],
        offset, int(completed)
    ))

def insert_rows(conn, rows):
    inserted = 0

    for row in rows:
        result = conn.execute("""
            INSERT INTO events (
              event_key, event_uid, timestamp_utc,
              rule_id, agent_id, agent_name,
              description, raw_json
            )
            SELECT ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
              SELECT 1 FROM events WHERE event_uid=?
            )
        """, (*row, row[1]))

        inserted += result.rowcount

    return inserted

def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not DB.is_file():
        raise SystemExit("STOP: History database missing")

    mode = "rw" if args.apply else "ro"

    conn = sqlite3.connect(
        f"file:{DB}?mode={mode}",
        uri=True,
        timeout=5
    )

    conn.execute("PRAGMA busy_timeout=5000")

    if args.dry_run:
        conn.execute("PRAGMA query_only=ON")
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history_sync_state (
              path TEXT PRIMARY KEY,
              inode TEXT NOT NULL,
              size INTEGER NOT NULL,
              modified TEXT NOT NULL,
              offset INTEGER NOT NULL,
              completed INTEGER NOT NULL
            )
        """)

    has_state = conn.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table'
          AND name='history_sync_state'
    """).fetchone()[0] == 1

    raw_files = docker(
        "find",
        "/var/ossec/logs/alerts",
        "-type", "f",
        "-name", "ossec-alerts-*.json*",
        "-print",
        timeout=20
    ).decode().splitlines()

    archives = sorted(
        p for p in raw_files if ARCHIVE_RE.fullmatch(p)
    )

    if len(archives) > 150:
        raise ValueError("Too many archive files")

    sources = archives + [ACTIVE]

    checked = 0
    existing = 0
    new = 0
    duplicate = 0
    inserted = 0
    skipped = 0

    seen = set()

    for path in sources:
        info = metadata(path)
        old = None

        if has_state:
            old = conn.execute("""
                SELECT inode, size, modified,
                       offset, completed
                FROM history_sync_state
                WHERE path=?
            """, (path,)).fetchone()

        is_archive = path != ACTIVE

        if is_archive:
            if (
                old is not None
                and old[:3] == info
                and old[4] == 1
            ):
                skipped += 1
                continue

            rows = read_archive(path)
            offset = info[1]

        else:
            # Replay the bounded active log from the beginning.
            # This detects rewritten content even when inode and
            # file size remain unchanged.
            if info[1] > MAX_ACTIVE:
                raise ValueError(
                    "Active log exceeds replay limit; "
                    "refusing to skip events"
                )

            rows, offset = read_active(
                0, info[1]
            )

        after = metadata(path)

        if is_archive:
            if after != info:
                raise ValueError("Archive changed during read")
        else:
            if after[0] != info[0] or after[1] < info[1]:
                raise ValueError("Active log rotated during read")

        if args.dry_run:
            for row in rows:
                uid = row[1]
                checked += 1

                if uid in seen:
                    duplicate += 1
                    continue

                seen.add(uid)

                found = conn.execute(
                    "SELECT 1 FROM events "
                    "WHERE event_uid=? LIMIT 1",
                    (uid,)
                ).fetchone()

                if found:
                    existing += 1
                else:
                    new += 1
        else:
            try:
                conn.execute("BEGIN IMMEDIATE")

                added = insert_rows(conn, rows)

                save_source(
                    conn, path, info, offset, is_archive
                )

                conn.commit()
                inserted += added
                checked += len(rows)

            except Exception:
                conn.rollback()
                raise

    count = conn.execute(
        "SELECT COUNT(*) FROM events"
    ).fetchone()[0]

    print("Mode:", "APPLY" if args.apply else "DRY RUN")
    print("Archive files found:", len(archives))
    print("Sources skipped by checkpoint:", skipped)
    print("Candidate events read:", checked)

    if args.dry_run:
        print("Already in SQLite:", existing)
        print("Not yet in SQLite:", new)
        print("Repeated within scan:", duplicate)
        print("Database modified: NO")
    else:
        print("New events inserted:", inserted)

    print("Total database events:", count)
    print("=== HISTORY SYNC SCAN PASS ===")

    conn.close()

if __name__ == "__main__":
    main()
