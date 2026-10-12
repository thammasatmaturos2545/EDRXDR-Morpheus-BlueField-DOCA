# BlueField Shadow Quarantine v1 — isolated policy test

Purpose: prove a safe operator-visible quarantine path for a strict-schema
failure without silently skipping the bad record and without leaving the
entire input pipeline permanently pinned once quarantine storage succeeds.

Isolated data flow:

    input topic
      offset 0 valid
      offset 1 poison
      offset 2 valid
            |
            v
    strict validation
      |                 \
      | valid            \ poison
      v                   v
    valid index       quarantine envelope
      |                   |
      |                   +--> quarantine index ACK
      |                   +--> quarantine Kafka ACK
      |                              |
      +------------------------------+
                     |
                     v
             commit source offset

Source offset advances past a poison record only after BOTH quarantine sinks
acknowledge it.

The quarantine envelope intentionally stores no raw input body, `raw_event`,
literal `capture_scope`, interface counters, or validation error message.
It stores only:

- schema/version and mode;
- run ID;
- reason code and error class;
- validation stage;
- SHA-256 of the source input;
- quarantine timestamp;
- source topic/partition/offset;
- historical / production / automated-response safety flags.

Failure injection:

- the quarantine index is initially created with an intentionally
  incompatible strict mapping;
- the poison record must remain at source committed offset 1;
- quarantine Kafka must remain empty;
- after repairing only the isolated quarantine index, a fresh process
  retries source offset 1;
- source offset may then advance to 2 only after quarantine index and Kafka
  acknowledgements.

Expected final state:

- input offset 3 / end 3 / lag 0;
- valid index documents = 2 (source offsets 0 and 2);
- quarantine index documents = 1;
- quarantine Kafka records = 1;
- quarantine source offset = 1;
- raw poison payload stored = false.

Safety boundaries:

- replay Kafka/OpenSearch only;
- never use `bluefield-events`;
- do not start `edrxdr-bluefield.service`;
- no GPU;
- no network driver/interface changes;
- no automated response;
- finite one-shot containers only.

Suggested run ID:

    export RUN_ID="$(date -u +%Y%m%dt%H%M%Sz | tr '[:upper:]' '[:lower:]')"

Mutation steps additionally require:

    -e BLUEFIELD_QUARANTINE_RUN_ALLOWED=1

Do not use `docker compose up`.
