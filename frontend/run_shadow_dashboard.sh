#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Resolve the current container address; do not hard-code a changing Docker IP.
backend=$(docker inspect edrxdr-replay-opensearch-1 \
  --format '{{with index .NetworkSettings.Networks "edrxdr-replay_replay-net"}}{{.IPAddress}}{{end}}')
[[ "$backend" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Replay OpenSearch network/IP not found'; exit 1; }
export SHADOW_OPENSEARCH_URL="http://$backend:9200"
export BLUEFIELD_HISTORY_OPENSEARCH_URL="$SHADOW_OPENSEARCH_URL"
# Read-only connectivity checks. Never fall back to host localhost:9200 (live).
for kind in severity behavioral; do
  curl --noproxy '*' -fsS --connect-timeout 3 --max-time 10 \
    "$SHADOW_OPENSEARCH_URL/shadow-$kind-v1/_count"
  printf '\n'
done
curl --noproxy '*' -fsS --connect-timeout 3 --max-time 10 \
  "$BLUEFIELD_HISTORY_OPENSEARCH_URL/review-bluefield-20261012t141653z-6396a0d3/_count"
printf '\n'
echo 'Open http://172.16.30.147:3000/shadow ; Ctrl+C stops only this frontend process.'
exec npm run start -- --hostname 0.0.0.0 --port 3000
