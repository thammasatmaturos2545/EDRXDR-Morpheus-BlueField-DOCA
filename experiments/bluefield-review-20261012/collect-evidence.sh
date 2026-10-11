#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
monitor="$HOME/edrxdr-bluefield-nullcheck.Bn44DZ"
normalizer="$HOME/edrxdr-bluefield-normalize.udX6v2"
monitor_files=(unit-tests.txt configure.txt compile.txt monitor.jsonl monitor.stderr)
normalizer_files=(tests.txt input-sha256.txt input-sha256-after.txt result.txt normalized.jsonl summary.txt)
# Check every input before creating anything. Never collect binaries, venvs or secrets.
test ! -e evidence || { echo 'evidence already exists; inspect it before retrying' >&2; exit 1; }
for f in "${monitor_files[@]}"; do test -f "$monitor/$f" || { echo "Missing: $monitor/$f" >&2; exit 1; }; done
for f in "${normalizer_files[@]}"; do test -f "$normalizer/$f" || { echo "Missing: $normalizer/$f" >&2; exit 1; }; done
mkdir -p evidence/monitor evidence/normalizer
for f in "${monitor_files[@]}"; do cp -- "$monitor/$f" "evidence/monitor/$f"; cmp -- "$monitor/$f" "evidence/monitor/$f"; done
for f in "${normalizer_files[@]}"; do cp -- "$normalizer/$f" "evidence/normalizer/$f"; cmp -- "$normalizer/$f" "evidence/normalizer/$f"; done
sha256sum evidence/monitor/* evidence/normalizer/* > evidence/SHA256SUMS
sha256sum -c evidence/SHA256SUMS
echo 'Evidence copied byte-for-byte. No services started or source files replaced.'
