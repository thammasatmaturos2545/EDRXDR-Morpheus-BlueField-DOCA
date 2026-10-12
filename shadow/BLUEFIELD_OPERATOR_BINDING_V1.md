# Canonical review binding — offline fixture scope

This step adds BoundReviewBook.reserve_fixture, not a sender. It accepts a plan
hash and reads the actual approval from the same private canonical journal.
There is no external approval argument. Within one SQLite transaction it checks
review/audit integrity, exact UID/name ownership, current expiry after locking,
fixture namespace, source coordinates, retention bounds and original byte hash.
It then writes the existing compatible intent chain and metadata binding atomically.
A failure rolls back; an uncertain commit must be inspected, never blindly retried.
The existing duplicate approval/source+destination reservation guards still apply.

Only synthetic_fixture evidence_kind and opread-<32 hex> run IDs are accepted.
This is a namespace restriction and explicit scope, NOT provenance authentication.
Real quarantine is rejected until a trusted quarantine sink reader is integrated.
The prior fixture envelope was locally generated, not authenticated sink evidence.
Do not relabel it as genuine quarantine or as a live measurement.

No existing journal needs migration during installation. fixture_bindings is created
only in the same transaction as a successful explicit offline fixture reservation.
Tests use private temporary journals and synthetic approvals. Installation never
creates an operational approval, reserves an actual record or consumes a real approval.
There is no runtime CLI or network client in the new binding module.

Raw bytes are verified in memory and not stored. Caller must later obtain them
from the verified Kafka reader, rather than from user-provided files. This API
cannot establish byte origin. Identity must come from the host authenticated
session; do not take it from an approval JSON or container user name. Shared Linux
accounts identify accounts, not individual people.

Transport remains disabled. Existing lower-level Journal.reserve is still an offline
primitive and must NOT be exposed as a replay bypass. inspect_binding is for audit,
not a bearer authorization token. Future real replay needs authoritative evidence,
host operator decision, source reread, durable binding and controlled destination
publication in one guarded workflow. No replay or production readiness is claimed.
