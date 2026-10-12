# BlueField Shadow fail-closed commit-boundary tests

These tests are isolated from the verified `shadow-bluefield-input-v1` /
`shadow-bluefield-v1` pilot.

Each run uses unique resources derived from `BLUEFIELD_FAILURE_RUN_ID`.

## Scenario A — poison record

The topic contains:

1. valid archived normalized record;
2. JSON-valid but strict-schema-invalid record (`carrier=2`);
3. another valid record.

Expected result:

- record 0 is indexed and Kafka commits offset 1;
- record 1 fails strict validation;
- Kafka remains committed at offset 1;
- a fresh process retries source offset 1 and fails closed again;
- the later valid record at offset 2 is not silently skipped.

## Scenario B — OpenSearch rejection before commit

A valid archived record is published to a separate isolated topic.
Its isolated OpenSearch index is intentionally created with a strict mapping
that omits `rx_bytes`, so the document is rejected.

Expected result:

- the valid record passes BlueField validation;
- OpenSearch rejects the write;
- Kafka has no committed offset for that group;
- the isolated index has zero documents;
- the isolated index is repaired (delete/recreate with the correct mapping);
- a fresh process retries the same source offset 0;
- after OpenSearch ACK, Kafka commits offset 1.

The failure injection does **not** stop or reconfigure the shared/replay
OpenSearch service.

## Safety

- replay Kafka/OpenSearch only;
- no `bluefield-events`;
- no `edrxdr-bluefield.service` start;
- no GPU;
- no driver/interface changes;
- no automated response;
- unique test topics/groups/indices;
- finite one-shot containers only.

## Suggested run ID

    export RUN_ID="$(date -u +%Y%m%dt%H%M%Sz | tr '[:upper:]' '[:lower:]')"

Run preflight first without mutation permission. All mutation actions require:

    -e BLUEFIELD_FAILURE_RUN_ALLOWED=1

Do not use `docker compose up`.
