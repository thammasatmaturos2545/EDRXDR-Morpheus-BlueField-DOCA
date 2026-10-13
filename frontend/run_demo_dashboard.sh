#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
backend=$(docker inspect edrxdr-replay-opensearch-1 --format '{{with index .NetworkSettings.Networks "edrxdr-replay_replay-net"}}{{.IPAddress}}{{end}}')
[[ "$backend" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Replay OpenSearch network/IP not found'; exit 1; }
export SHADOW_OPENSEARCH_URL="http://$backend:9200"
export REPLAY_OPENSEARCH_URL="$SHADOW_OPENSEARCH_URL"
export BLUEFIELD_HISTORY_OPENSEARCH_URL="$SHADOW_OPENSEARCH_URL"
curl --noproxy '*' -fsS --connect-timeout 3 --max-time 10 "$SHADOW_OPENSEARCH_URL/_cluster/health"
printf '\nOpen http://172.16.30.147:3000/ ; Ctrl+C stops this frontend only.\n'
exec npm run start -- --hostname 0.0.0.0 --port 3000
