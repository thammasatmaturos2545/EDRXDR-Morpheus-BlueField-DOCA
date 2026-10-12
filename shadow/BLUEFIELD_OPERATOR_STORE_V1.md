# Operator review v1 — step 2: offline local audit journal

Base checkpoint: `af0c55e`, branch `work/bluefield-shadow-quarantine`.
Adds a stdlib SQLite journal and synthetic tests; no existing checkpoint file is replaced.
There is still NO Kafka replay command, live integration, service change, driver action,
GPU access, automatic approval or automated response.

## Implemented

- Explicit new-journal initialization, refusing overwrite. Opening a missing journal fails;
  it never silently creates a replacement database. Use one canonical trusted local path.
- On POSIX, require owner-only parent directory and database. Symlink paths are rejected.
  Windows ACL enforcement is outside this implementation. Network filesystems are unsupported.
- SQLite DELETE journal mode, synchronous FULL and BEGIN IMMEDIATE serialize reservations.
- The exact allowlisted review plan, quarantine envelope, approval and external operator
  identity are stored with authorization digest and chained review/approved/intent events.
  No raw Kafka value, raw_event or literal capture_scope is stored.
- Approval validity is rechecked after the database write lock is acquired. Source coordinate,
  watermark and byte-hash checks are required before intent is inserted.
- Attempt ID, approval ID and source+input-hash+destination key are unique in the journal.
  New approval IDs do not permit a second reservation for the same record and destination.
  Distinct destinations require distinct approved plans; policy limiting those belongs to
  the upcoming trusted operator workflow.
- Approval consumption and intent are atomic. A storage/commit error returns no success.
  A post-commit error can still leave an intent; subsequent reservation is blocked.
- An intent found after reopening means pending reconciliation, not permission to resend.
  Unknown outcomes and acknowledgements are terminal. No automatic retry/reconciliation
  or record deletion method is provided.
- ACK metadata must name the approved isolated destination, partition 0 and a valid offset.
  Metadata is supplied by a trusted caller; this offline module cannot prove a broker ACK.
  If final audit storage fails, the prior intent remains pending.

## API boundaries

`initialize(path)` is a deliberate provisioning operation. `Journal.reserve(...)` validates
one supplied approval/source and persists intent; its result explicitly has transport_enabled=false.
`record_outcome(...)` records supplied ACK metadata or an unknown outcome. `inspect(...)`
validates the stored chain and returns metadata with retry_allowed=false.

`trusted_operator` must eventually come from an authenticated local execution context, not
from an approval JSON field. No login, signature verifier or approval CLI exists yet.
Supplied source bytes/watermarks will need to come from an exact original Kafka read.
An in-memory successful reservation is NOT a reusable sending capability.

Validation failures before reservation leave no new intent. This step does not yet implement
a separate durable log for denied review/approval attempts; that is required in the operator
workflow before claiming complete operator auditing. Expiry, source validation and service
state must also be checked in the eventual broker-facing execution path.

Hash chains/seals detect accidental inconsistency, not a malicious journal owner rewriting
history. Restoring an old database or using a second path can defeat deduplication; operational
identity, backups and reconciliation policy must be reviewed before transport integration.
FULL synchronization relies on local filesystem/hardware guarantees. No power-loss testing
or cross-system exactly-once guarantee is claimed.

## Validation

Local Windows Python venv: existing 15 contract tests plus 19 store tests PASS on 2026-10-13.
Tests exercise two independent processes, competing connections, duplicate approval/replay,
expiry, missing approval/source/hash failures, atomic rollback, injected ambiguous commit,
reopen-after-intent, outcome write failure, invalid ACK metadata and corrupted audit records.
All records and acknowledgements are synthetic. POSIX permission enforcement and the same
suite still need verification on the VM. No production database is created by installation;
tests use temporary directories removed after completion.

Next step: guarded operator review/approval workflow with authenticated actor attribution,
denial audit and read-only source inspection. Review that implementation before enabling
any separate bounded replay command. Keep BlueField inactive/dead/disabled, use no live
bluefield-events and preserve the original checkpoints.
