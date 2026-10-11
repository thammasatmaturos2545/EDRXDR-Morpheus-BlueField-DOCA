#!/usr/bin/env bash
# CPU-only verification. Does not start Docker containers, workers, web servers or training.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p training/evidence
evidence_dir=$(mktemp -d "$PWD/training/evidence/shadow-review-20261011.XXXXXX")
printf 'Evidence: %s\n' "$evidence_dir"
{
  date -Is
  git branch --show-current
  git log -1 --oneline
  git status --short --untracked-files=all
  git diff --check
} 2>&1 | tee "$evidence_dir/git.txt"
python3 - <<'PY' 2>&1 | tee "$evidence_dir/source-lock.txt"
import hashlib, json
from pathlib import Path
root = Path.cwd()
lock = json.loads((root / 'shadow/source-lock.json').read_text())
failures = []
for name, expected in lock['sha256'].items():
    p = root / name
    actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    if actual != expected:
        failures.append(name)
if failures:
    raise SystemExit('STOP: missing or changed pinned source: ' + ', '.join(failures))
print('Pinned replay/training source hashes PASS')
manifest = json.loads((root / 'shadow/PACKAGE_SHA256.json').read_text())
for name, expected in manifest.items():
    if hashlib.sha256((root / 'shadow' / name).read_bytes()).hexdigest() != expected:
        raise SystemExit('STOP: shadow package hash mismatch: ' + name)
print('Reviewed shadow package hashes PASS')
PY
python3 -B shadow/test_shadow.py 2>&1 | tee "$evidence_dir/worker-tests.txt"
python3 -B shadow/test_recovery.py 2>&1 | tee "$evidence_dir/recovery-tests.txt"
docker compose -f shadow/compose.yml config --quiet 2>&1 | tee "$evidence_dir/compose-config.txt"
(
  cd frontend
  node tests/shadow.cjs 2>&1 | tee "$evidence_dir/frontend-shadow-tests.txt"
  npm run typecheck 2>&1 | tee "$evidence_dir/typecheck.txt"
  npm run test:regression 2>&1 | tee "$evidence_dir/regression.txt"
  npm run lint 2>&1 | tee "$evidence_dir/lint.txt"
)
printf 'CPU verification PASS. No build, inference, training or services started. Logs: %s\n' "$evidence_dir" | tee "$evidence_dir/result.txt"
