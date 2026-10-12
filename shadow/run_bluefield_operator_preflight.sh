#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
state=$(systemctl show edrxdr-bluefield.service --no-pager -p ActiveState -p SubState -p UnitFileState)
expected=$(printf '%s\n' 'ActiveState=inactive' 'SubState=dead' 'UnitFileState=disabled' | sort)
[ "$(printf '%s\n' "$state" | sort)" = "$expected" ] || { echo 'STOP: service state changed'; exit 1; }
image=sha256:66a654987f79ee7a929b8e24ea4e0f5eea8a02245131f0eeb97292beabcedc4e
timeout 10s docker image inspect "$image" --format '{{.Id}}'
timeout 10s docker network inspect edrxdr-replay_replay-net --format '{{.Name}}'
timeout --signal=TERM --kill-after=5s 45s docker run --rm --pull=never \
  --network edrxdr-replay_replay-net --user 1001:1002 --read-only \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --cpus 1 --memory 512m --pids-limit 64 \
  --mount "type=bind,src=$here,dst=/shadow,readonly" \
  --env PYTHONPATH=/shadow --env PYTHONDONTWRITEBYTECODE=1 \
  --entrypoint timeout "$image" --signal=TERM --kill-after=3s 30s \
  /opt/conda/envs/morpheus/bin/python -B /shadow/bluefield_operator_kafka.py preflight
