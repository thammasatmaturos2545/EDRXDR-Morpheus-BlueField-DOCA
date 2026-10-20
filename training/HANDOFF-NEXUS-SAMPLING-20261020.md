# Bounded Wazuh sampling — 2026-10-20

- Latest 4 MiB from verified manager; timeout 10 s and maxBuffer 5 MiB.
- Malformed/partial JSON lines skipped; at most 100 selected rows.
- Up to 25 recent file positions per agent in rounds, then fill recent positions.
  This is not a strict per-agent cap or event-time chronology guarantee.
- UID and severity fields unchanged. Counts refer to selected rows only.
- Events outside byte window and some agents when over 100 agents may be absent.
- Actual sampler route tests cover partial first line, 100 unique UIDs,
  source identity, bounds and unavailable states with mocked Docker.
- Offline tests/typecheck/whitespace required; no live reads or coverage proof.
- No GPU, build, restart, deployment or commit. UI/history WIP excluded.
