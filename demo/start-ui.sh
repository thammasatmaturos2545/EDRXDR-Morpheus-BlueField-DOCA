#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[ -d "$repo/frontend/node_modules" ] || { echo 'STOP: frontend dependencies missing'; exit 1; }
if ss -ltn | awk '{print $4}' | grep -Eq ':3001$'; then echo 'STOP: port 3001 in use'; exit 1; fi
ui=$(mktemp -d "$HOME/edrxdr-demo-ui.XXXXXX")
cp -R "$repo/frontend/src" "$ui/src"
[ ! -d "$repo/frontend/public" ] || cp -R "$repo/frontend/public" "$ui/public"
for name in package.json package-lock.json tsconfig.json next-env.d.ts next.config.ts postcss.config.mjs eslint.config.mjs; do
  [ ! -f "$repo/frontend/$name" ] || cp "$repo/frontend/$name" "$ui/$name"
done
ln -s "$repo/frontend/node_modules" "$ui/node_modules"
backend=$(timeout 10s docker inspect edrxdr-replay-opensearch-1 --format '{{with index .NetworkSettings.Networks "edrxdr-replay_replay-net"}}{{.IPAddress}}{{end}}')
[[ "$backend" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 1
export SHADOW_OPENSEARCH_URL="http://$backend:9200"
export REPLAY_OPENSEARCH_URL="$SHADOW_OPENSEARCH_URL"
export BLUEFIELD_HISTORY_OPENSEARCH_URL="$SHADOW_OPENSEARCH_URL"
cd "$ui"
printf 'Isolated frontend build: %s\n' "$ui"
npm run typecheck
node "$repo/frontend/node_modules/next/dist/bin/next" build
printf 'Open http://172.16.30.147:3001/\nOverview: /overview · Experiments: /experiments\nCtrl+C stops this frontend only.\n'
exec npm run start -- --hostname 0.0.0.0 --port 3001
