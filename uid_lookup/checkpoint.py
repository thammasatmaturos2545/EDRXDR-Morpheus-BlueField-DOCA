"""Durable checkpoints for exact UID backfill."""

import fcntl
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from uid_lookup.bulk_payload import TARGET_INDEX
from uid_lookup.lookup_docs import SCHEMA, INDEX_PATTERN

VERSION = "edrxdr-uid-backfill-checkpoint-v1"


def make_plan(source_indices, slices=32):
    if (
        not isinstance(source_indices, list)
        or not source_indices
        or len(source_indices) > 128
        or any(
            not isinstance(x, str)
            or not INDEX_PATTERN.fullmatch(x)
            for x in source_indices
        )
        or len(set(source_indices)) != len(source_indices)
    ):
        raise ValueError("Invalid source indices")

    if type(slices) is not int or not 1 <= slices <= 128:
        raise ValueError("Invalid slice count")

    return {
        "version": "uid-backfill-plan-v1",
        "source_indices": sorted(source_indices),
        "slices": slices,
        "target_index": TARGET_INDEX,
        "lookup_schema": SCHEMA,
        "identity_contract": "wazuh-v1",
    }


def plan_hash(plan):
    canonical = json.dumps(
        plan, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def load_checkpoint(path, plan):
    path = Path(path)

    if path.is_symlink():
        raise ValueError("Symlink checkpoint rejected")

    if not path.exists():
        return {
            "version": VERSION,
            "plan_hash": plan_hash(plan),
            "completed": {},
        }

    data = json.loads(path.read_text())

    if (
        not isinstance(data, dict)
        or set(data) != {"version", "plan_hash", "completed"}
        or data["version"] != VERSION
        or data["plan_hash"] != plan_hash(plan)
        or not isinstance(data["completed"], dict)
    ):
        raise ValueError("Checkpoint plan mismatch or invalid format")

    for key, entry in data["completed"].items():
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"0|[1-9][0-9]*", key)
            or int(key) >= plan["slices"]
            or not isinstance(entry, dict)
            or set(entry) != {
                "scanned", "created", "verified_existing"
            }
        ):
            raise ValueError("Invalid completed slice")

        numbers = list(entry.values())

        if (
            any(type(v) is not int or v < 0 for v in numbers)
            or entry["scanned"] != (
                entry["created"] + entry["verified_existing"]
            )
        ):
            raise ValueError("Unverified checkpoint counts")

    return data


def _atomic_write(path, data):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(
        prefix=".uid-checkpoint-",
        dir=path.parent,
    )

    try:
        os.fchmod(fd, 0o600)

        with os.fdopen(fd, "w") as f:
            json.dump(data, f, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(temporary, path)

        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def mark_complete(
    path, plan, slice_id, *,
    scan_complete, scanned, created, verified_existing
):
    if type(slice_id) is not int or not 0 <= slice_id < plan["slices"]:
        raise ValueError("Invalid slice ID")

    if scan_complete is not True:
        raise ValueError("Cannot checkpoint incomplete scan")

    counts = (scanned, created, verified_existing)

    if (
        any(type(v) is not int or v < 0 for v in counts)
        or scanned != created + verified_existing
    ):
        raise ValueError("Unconfirmed document count")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = path.with_name(path.name + ".lock")

    with open(lock_path, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)

        checkpoint = load_checkpoint(path, plan)
        key = str(slice_id)

        entry = {
            "scanned": scanned,
            "created": created,
            "verified_existing": verified_existing,
        }

        if key in checkpoint["completed"]:
            if checkpoint["completed"][key] != entry:
                raise ValueError("Conflicting completed slice")
            return checkpoint

        checkpoint["completed"][key] = entry
        _atomic_write(path, checkpoint)

        return checkpoint
