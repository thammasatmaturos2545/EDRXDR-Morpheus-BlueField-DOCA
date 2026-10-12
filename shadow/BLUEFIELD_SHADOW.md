# BlueField Shadow v1 — bounded archived pilot

Scope: archived BlueField normalized evidence only.  This package does not
start `edrxdr-bluefield.service`, does not read `bluefield-events`, does not
change network drivers/interfaces, does not use a GPU, and does not enable
automated response.

Data flow:

    committed archived normalized.jsonl
      -> replay Kafka topic shadow-bluefield-input-v1
      -> bounded/manual indexer
      -> replay OpenSearch index shadow-bluefield-v1

The indexed document is a display/evaluation contract:

- `processing_mode=shadow`
- `historical=true`
- `production_ready=false`
- `automated_response_allowed=false`
- `carrier: null` remains null/unknown
- real counter/delta zero remains numeric zero
- first-sample delta remains null
- `raw_event` and literal `capture_scope` are not indexed

Runtime mutations are fail-closed behind:

    BLUEFIELD_SHADOW_RUN_ALLOWED=1

Default Compose value is `0`.

CPU-only checks (no broker mutation):

    python3 -B shadow/test_bluefield_shadow.py
    docker compose -f shadow/compose.bluefield.yml config --quiet

Read-only preflight:

    docker compose -f shadow/compose.bluefield.yml \
      --profile manual run -T --rm inspect

Only after reviewing preflight and explicitly authorizing this bounded run:

    docker compose -f shadow/compose.bluefield.yml \
      --profile manual run -T --rm \
      -e BLUEFIELD_SHADOW_RUN_ALLOWED=1 admin

    docker compose -f shadow/compose.bluefield.yml \
      --profile manual run -T --rm \
      -e BLUEFIELD_SHADOW_RUN_ALLOWED=1 publish

    docker compose -f shadow/compose.bluefield.yml \
      --profile manual run -T --rm \
      -e BLUEFIELD_SHADOW_RUN_ALLOWED=1 index

    docker compose -f shadow/compose.bluefield.yml \
      --profile manual run -T --rm verify

Do not use `docker compose up`.  These are finite one-shot workers only.

This pilot intentionally does not solve live BlueField capture, continuous
normalization, poison-message policy, long-term retention, or production
readiness.  Those require a separate review.
