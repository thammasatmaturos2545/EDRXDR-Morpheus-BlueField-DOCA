# Dashboard navigation and evidence display — 2026-10-20

- Source reviewed from fixed 14-file archive; hash verified locally.
- Offline isolated tests/typecheck required before commit. No deployment implied.
- History reuses complete AI reader with bounded batches and page deadline.
- Browser missing evidence times stay null; unknown health stays unknown.
- History query script and SQLite database remain external operator dependencies.
- Source history/ and uid_lookup/ data, historical evidence and older handoffs
  remain outside this batch. Dedicated read-only credentials and production
  authorization, retention and Analyst semantic review remain pending.
- BlueField live and automated response stay disabled. No GPU/training.
