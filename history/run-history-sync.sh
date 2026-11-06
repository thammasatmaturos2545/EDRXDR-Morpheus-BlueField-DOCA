#!/usr/bin/env bash
set -euo pipefail
umask 077

DIR="$HOME/nexus-history-preview-20261020"
SCRIPT="$DIR/sync_history.py"
DB="$DIR/history.sqlite3"
LOG="$DIR/history-sync.log"
LOCK="$DIR/history-sync.lock"

MODE="${1:---apply}"

if [[ "$MODE" != "--apply" &&
      "$MODE" != "--dry-run" ]]; then
  echo "STOP: Invalid sync mode" >&2
  exit 2
fi

if [[ "$(id -un)" != "saiuser" ]]; then
  echo "STOP: Unexpected Linux user" >&2
  exit 1
fi

test -f "$SCRIPT"
test -f "$DB"

# Prevent concurrent manual and scheduled syncs.
exec 9>"$LOCK"

if ! flock -n 9; then
  echo "$(date -Is) SKIPPED: Sync already running" >> "$LOG"
  exit 0
fi

# Keep one previous log when current log exceeds 1 MiB.
if [[ -f "$LOG" ]] &&
   [[ "$(stat -c '%s' "$LOG")" -ge 1048576 ]]; then
  mv -f "$LOG" "$LOG.previous"
fi

echo "$(date -Is) START $MODE" >> "$LOG"

if timeout --signal=TERM --kill-after=5s 180s \
  nice -n 15 \
  python3 -B "$SCRIPT" "$MODE" >> "$LOG" 2>&1
then
  echo "$(date -Is) PASS $MODE" >> "$LOG"
  echo "Sync completed: $MODE"
else
  result=$?
  echo "$(date -Is) FAILED $MODE exit=$result" >> "$LOG"
  echo "Sync FAILED: exit=$result" >&2
  exit "$result"
fi
