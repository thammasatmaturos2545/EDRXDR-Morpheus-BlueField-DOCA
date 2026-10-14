"""Fail-closed validation for an authorized EDR/XDR GPU reservation."""

import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


EXPECTED_UID = 1001
EXPECTED_GID = 1002


def parse_time(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing reservation timestamp")

    result = datetime.fromisoformat(value)

    if result.tzinfo is None:
        raise ValueError("Reservation timestamp must include timezone")

    return result


def validate_window(data, now, requested_seconds):
    start = parse_time(data.get("effective_from"))
    end = parse_time(data.get("reservation_end"))
    cutoff = parse_time(data.get("launcher_cutoff"))

    maximum = data.get("max_session_seconds")

    if (
        isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or maximum < 1
    ):
        raise ValueError("Invalid max_session_seconds")

    if (
        isinstance(requested_seconds, bool)
        or not isinstance(requested_seconds, int)
        or requested_seconds < 1
    ):
        raise ValueError("Invalid requested runtime")

    if requested_seconds > maximum:
        raise RuntimeError("Requested runtime exceeds reservation")

    if not start <= now < cutoff:
        raise RuntimeError("Outside authorized GPU launch window")

    if cutoff > end:
        raise ValueError("Launcher cutoff exceeds reservation end")

    finish = now + timedelta(seconds=requested_seconds)

    if finish >= cutoff:
        raise RuntimeError("Requested run would cross launcher cutoff")

    authorization = data.get("authorization")

    if not isinstance(authorization, str) or not authorization.strip():
        raise ValueError("Reservation authorization missing")

    return {
        "effective_from": start,
        "reservation_end": end,
        "launcher_cutoff": cutoff,
        "requested_seconds": requested_seconds,
        "max_session_seconds": maximum,
    }


def run(*argv):
    result = subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(argv)}: "
            f"{result.stderr.strip()}"
        )

    return result.stdout.strip()


def check_operator():
    if os.getuid() != EXPECTED_UID or os.getgid() != EXPECTED_GID:
        raise RuntimeError(
            f"Expected operator {EXPECTED_UID}:{EXPECTED_GID}"
        )


def check_bluefield():
    output = run(
        "systemctl",
        "show",
        "edrxdr-bluefield.service",
        "--no-pager",
        "-p", "ActiveState",
        "-p", "SubState",
        "-p", "UnitFileState",
    )

    state = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in output.splitlines()
        if "=" in line
    }

    expected = {
        "ActiveState": "inactive",
        "SubState": "dead",
        "UnitFileState": "disabled",
    }

    if state != expected:
        raise RuntimeError("BlueField safety state changed")

    return state


def check_gpu(reservation):
    expected_uuid = reservation.get("gpu_uuid")

    if not isinstance(expected_uuid, str) or not expected_uuid.startswith("GPU-"):
        raise ValueError("Invalid GPU UUID in reservation")

    inventory = run(
        "nvidia-smi",
        "--query-gpu=index,name,uuid",
        "--format=csv,noheader,nounits",
    )

    matches = []

    for line in inventory.splitlines():
        fields = [x.strip() for x in line.split(",")]

        if len(fields) != 3:
            continue

        index, name, uuid = fields

        if uuid == expected_uuid:
            matches.append((index, name, uuid))

    if len(matches) != 1:
        raise RuntimeError("Authorized GPU UUID not uniquely present")

    processes = run(
        "nvidia-smi",
        "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
        "--format=csv,noheader,nounits",
    )

    conflicts = []

    for line in processes.splitlines():
        if not line.strip():
            continue

        fields = [x.strip() for x in line.split(",")]

        if fields and fields[0] == expected_uuid:
            conflicts.append(line)

    if conflicts:
        raise RuntimeError(
            "Authorized GPU currently has compute process: "
            + " | ".join(conflicts)
        )

    index, name, uuid = matches[0]

    return {
        "index": index,
        "name": name,
        "uuid": uuid,
        "compute_processes": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--reservation",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--seconds",
        type=int,
        default=120,
    )

    args = parser.parse_args()

    data = json.loads(args.reservation.read_text())

    now = datetime.now().astimezone()

    check_operator()

    window = validate_window(
        data,
        now,
        args.seconds,
    )

    bluefield = check_bluefield()
    gpu = check_gpu(data)

    result = {
        "kind": "gpu_reservation_preflight",
        "status": "PASS",
        "checked_at": now.isoformat(),
        "gpu_uuid": gpu["uuid"],
        "gpu_index": gpu["index"],
        "gpu_name": gpu["name"],
        "requested_seconds": window["requested_seconds"],
        "max_session_seconds": window["max_session_seconds"],
        "launcher_cutoff": window["launcher_cutoff"].isoformat(),
        "compute_processes": gpu["compute_processes"],
        "bluefield": bluefield,
        "gpu_started": False,
        "inference_started": False,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
