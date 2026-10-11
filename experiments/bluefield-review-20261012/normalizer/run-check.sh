#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
input=${1:-"$HOME/edrxdr-bluefield-nullcheck.Bn44DZ/monitor.jsonl"}
test -f "$input" || { printf 'Input missing: %s\n' "$input" >&2; exit 1; }
run=$(mktemp -d "$HOME/edrxdr-bluefield-normalize.XXXXXX")
printf 'Evidence directory: %s\n' "$run"
mkdir "$run/tmp"
export TMPDIR="$run/tmp"
python3 -m venv --without-pip "$run/.venv"
source "$run/.venv/bin/activate"
export PYTHONDONTWRITEBYTECODE=1
python -B test_normalize.py 2>&1 | tee "$run/tests.txt"
sha256sum "$input" > "$run/input-sha256.txt"
python -B normalize.py "$input" "$run/normalized.jsonl" \
  --capture-scope "$(hostname):$(dirname -- "$input")" | tee "$run/result.txt"
sha256sum "$input" > "$run/input-sha256-after.txt"
cmp "$run/input-sha256.txt" "$run/input-sha256-after.txt"
python - "$run/normalized.jsonl" <<'PY' | tee "$run/summary.txt"
import json, sys
from collections import Counter
from pathlib import Path
rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
print('Rows:', len(rows))
print('Interfaces:', dict(Counter(str(r['interface']) for r in rows)))
print('operstate:', dict(Counter(str(r['operstate']) for r in rows)))
print('carrier null:', sum(r['carrier'] is None for r in rows))
print('rx_bytes delta status:', dict(Counter(r['delta_status']['rx_bytes'] for r in rows)))
for r in rows:
    print(json.dumps({k:r[k] for k in ('timestamp','interface','operstate','carrier','rx_bytes','delta_rx_bytes','delta_status')}))
PY
printf 'Completed offline only. Evidence: %s\n' "$run"
