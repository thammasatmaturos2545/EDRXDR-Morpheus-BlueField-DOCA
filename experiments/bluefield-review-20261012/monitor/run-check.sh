#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
run=$(mktemp -d "$HOME/edrxdr-bluefield-nullcheck.XXXXXX")
printf 'Isolated output: %s\n' "$run"
mkdir -p "$run/tmp"
export TMPDIR="$run/tmp"
python3 -m venv "$run/.venv"
source "$run/.venv/bin/activate"
# Existing system C/DOCA tools are used read-only. No pip/apt/driver install.
python -B test_monitor.py 2>&1 | tee "$run/unit-tests.txt"
meson setup "$run/build" "$PWD" 2>&1 | tee "$run/configure.txt"
meson compile -C "$run/build" -j 2 2>&1 | tee "$run/compile.txt"
# Native bounded sampling; timeout is an additional guard, not expected success.
timeout --signal=TERM --kill-after=2s 15s "$run/build/bluefield_monitor" --samples 3 \
  > "$run/monitor.jsonl" 2> "$run/monitor.stderr"
cat "$run/monitor.stderr"
python - "$run/monitor.jsonl" <<'PY'
import json, sys
from pathlib import Path
rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
if not rows:
    raise SystemExit('FAIL: no records')
for row in rows:
    if row.get('schema_version') != 'bluefield-monitor-review-1':
        raise SystemExit('FAIL: wrong schema')
    for field in ('operstate', 'carrier', 'rx_packets', 'tx_packets', 'rx_bytes', 'tx_bytes', 'rx_errors', 'tx_errors'):
        if (row[field] is None) != (field in row['read_errors']):
            raise SystemExit(f'FAIL: inconsistent error state: {field}')
    print(json.dumps(row, ensure_ascii=False))
print(f'PASS: {len(rows)} observed records; not proof of traffic or end-to-end delivery')
PY
printf 'Completed. Evidence: %s\n' "$run"
