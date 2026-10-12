# BlueField Shadow isolated recovery test

Purpose: verify restart/resume behavior independently from the verified
`shadow-bluefield-input-v1` / `shadow-bluefield-v1` pilot.

Each run uses unique resources derived from `BLUEFIELD_RECOVERY_RUN_ID`:

- Kafka topic: `shadow-bluefield-recovery-<run-id>`
- consumer group: `edrxdr-shadow-bluefield-recovery-<run-id>`
- OpenSearch index: `shadow-bluefield-recovery-<run-id>`

Expected sequence:

1. setup an empty isolated topic/index;
2. publish the same six committed archived normalized records;
3. phase1 indexes exactly three records and commits offset 3;
4. the process exits;
5. phase2 starts in a fresh container, resumes at offset 3, indexes the
   remaining three records and commits offset 6;
6. rerun processes zero records;
7. verify requires six unique documents, offset 6, lag 0 and preserved
   null/zero semantics.

Safety boundaries:

- replay Kafka/OpenSearch only;
- never uses `bluefield-events`;
- does not start `edrxdr-bluefield.service`;
- no GPU;
- no network driver/interface changes;
- no automated response;
- recovery index stores only a safe subset of the archived normalized
  record; it does not store `raw_event` or literal `capture_scope`.

Example:

    export RUN_ID="$(date -u +%Y%m%dt%H%M%Sz | tr '[:upper:]' '[:lower:]')"

    docker compose -f shadow/compose.bluefield.recovery.yml \
      --profile manual run -T --rm \
      -e BLUEFIELD_RECOVERY_RUN_ID="$RUN_ID" inspect

Mutation steps additionally require:

    -e BLUEFIELD_RECOVERY_RUN_ALLOWED=1

Do not use `docker compose up`. All workers are finite one-shot containers.
