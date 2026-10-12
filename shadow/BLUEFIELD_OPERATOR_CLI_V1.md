# Operator Review CLI v1 — step 3, offline only

Base checkpoint: 6c42322 on work/bluefield-shadow-quarantine.
Adds CLI, tests and this document only. No existing contract/store/checkpoint file changes.
There is NO Kafka import, source fetch, producer, offset commit, GPU work or service mutation.

## Commands

Run with the project's Python venv on Linux, directly as your non-root SSH account:

    python -B shadow/bluefield_operator_review.py --help

Commands: init, review, show, approve, reject, export-approval. No replay command exists.
Every command checks edrxdr-bluefield.service is inactive/dead/disabled. init creates a NEW
private local SQLite database with step-2 attempt tables and additional review/audit tables.
It does not migrate or overwrite an existing database. The parent must already exist,
be owned by the caller and have no group/other permissions. Do not use sudo for this CLI.
Use one canonical journal per deployment; never initialize a new one to bypass a decision.

review accepts an envelope JSON FILE, its original quarantine document ID and an isolated
destination topic name. It validates the envelope and binds a pending plan. This is offline
metadata review only, not proof that the envelope was fetched from a trusted broker/index,
that source bytes remain available, or that a destination exists or is unconsumed.
Do not treat a copied arbitrary JSON file as trusted evidence for future replay.

show reads the recorded plan/decision. approve displays that plan and the OS actor, requires
stdin and stdout TTYs and the exact text `APPROVE <full-plan-sha256>`. No --yes, operator-name
override, input-pipe approval or approval-by-default exists. The service is rechecked after
human input. TTL defaults to 600 seconds (maximum 3600). CLI never sets approval automatically.

The actor is POSIX real/effective UID plus pwd.getpwuid(uid).pw_name, not USER/LOGNAME/SUDO_USER
environment strings. Root or real/effective UID mismatch is refused. This attributes the
local account, not a unique person: if teammates share saiuser, audit cannot distinguish them.
No multi-person approval, remote identity authentication or cryptographic signature is claimed.

reject records a terminal decision with one of: needs_investigation, invalid_measurement,
source_unavailable, not_authorized. Approval/rejection and its audit event commit atomically.
Competing decisions serialize; only one wins. A decided review cannot be reissued, and a new
review for the same source/hash/destination is refused. v1 has no reapproval or revoke command;
expired decisions require a separately designed workflow, not a new database workaround.

export-approval writes an already approved artifact only for the deciding OS actor while it
is unexpired. It records export intent first, creates a 0600 file without overwrite, fsyncs
the file and parent directory, then records completion with the byte hash. If the final audit
write fails, the file may exist and export intent remains: report failure, inspect, and do
not overwrite/reissue automatically. The artifact is JSON, not a signed sending capability.
Re-export does not grant another replay; future replay must verify it against this journal
and consume it through the step-2 reservation transaction.

## Audit and trust limits

Audit includes account UID/name, timestamp, action, plan hash, fixed reason codes and artifact
hash. It does not log arbitrary failure text, input body, raw_event or capture_scope.
Malformed review requests, bad confirmation, non-TTY approval and rejected operations are
logged where a valid journal/actor is available. CLI usage errors rejected by argparse,
identity failure before journal access or an unavailable audit database cannot be logged
there; the command returns failure. No operation proceeds as a success when auditing fails.

Review/approval state is bound to matching audit events and hashes. Like step 2, hash chains
detect inconsistency, not a malicious owner rewriting the journal. It is a private local
filesystem design, not a remotely trusted approval service. Importing Python and invoking
the internal API is outside the interactive CLI enforcement boundary; possession of this
code or write access to the database must not be treated as independent authorization.

## Verification

20 new synthetic workflow tests passed locally in a Python venv, including noninteractive
denial, wrong confirmation, explicit rejection, concurrent decisions, audit rollback,
ambiguous commit, invalid payload handling and safe export. Authentication, TTY input and
systemctl are mocked in CLI unit tests: there is no real operator approval. Existing 15
contract and 19 store tests must also pass. Installation runs all suites on the VM before
adding files, but does not initialize an operational journal or issue any approval.

Next: inspect original source read-only with verified replay-broker/topic identities and
exact partition/offset, fresh watermarks and byte SHA256. Retention loss/hash mismatch must
fail closed. Only after review of that step should a distinct bounded replay implementation
be enabled. Keep the old quarantine checkpoints and source consumer offsets unchanged.
