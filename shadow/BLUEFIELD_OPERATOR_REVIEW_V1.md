# Controlled Quarantine Replay / Operator Review v1 — step 1

Base: work/bluefield-shadow-quarantine, 829169b. This step adds OFFLINE CONTRACTS ONLY.
No approval issuer, Kafka replay command, OpenSearch writer or durable audit store exists in this patch.

## Checkpoint evidence reviewed

The user supplied clean Git status at 829169b and inactive/dead/disabled service state. Archived quarantine verification records two valid docs, one quarantine envelope, input offset 3/3. Recovery records six unique docs at 6/6. Source code writes quarantine index then Kafka, and commits only after both acknowledgements. These are prior bounded tests, not a new integration run. HANDOFF says isolated resources were cleaned up: never assume source offsets still exist.

training/HANDOFF_SHA256.json is stale for HANDOFF.md and LATEST_STATUS.md in this archive. This step does not rewrite that historical manifest or any checkpoint files.

## Contracts implemented

- Strict allowlisted quarantine envelope; original document-ID algorithm checked against the checkpoint implementation.
- Review plan binds evidence hash, evidence ID, exact source coordinates, original input SHA256, isolated destination, timestamp and one-record limit.
- No function generates an approval. A caller must supply an explicit approve decision, operator, approval ID, matching plan hash, reason code and validity interval (maximum one hour).
- trusted_operator is an external authenticated context, NOT authentication implemented here. A matching text name is not proof of identity. Future integration must not derive trusted_operator from the submitted approval. No production security claim.
- Source verification requires exact topic/partition/offset, fresh watermark range and original byte SHA256. No archived-file fallback, JSON rewriting or poison correction. carrier=2 remains carrier=2.
- Audit event builder allowlists fields/reasons and chains hashes. Success requires an intent state; unknown delivery is terminal in v1, requiring separate operator reconciliation. No automatic retry.

The audit builder is a pure data contract: it does not enforce durable storage, authenticate the operator, prevent concurrent attempts or deduplicate records. Hash chaining is not a digital signature or tamper-proof storage. Review plan and approval artifacts must be retained and their hashes linked in the future durable attempt ledger, which must atomically consume approval and reserve an attempt before publish. No command here can publish or commit a source offset.

## Tests and limitations

15 synthetic offline tests passed locally in a Python venv on 2026-10-13. They cover approval presence/identity/expiry/binding, unsafe flags, extra payload fields, source position/retention/hash failure, exact poison bytes, audit ordering/tampering and unknown-outcome retry rejection. These tests do not establish real retention behavior, authenticated operator approval, audit-storage outage handling or exactly-once delivery.

## Next review steps (not executed)

1. Add durable fail-closed audit/attempt journal and trusted local operator approval workflow. Audit write/fsync failure must prevent publish; crash after intent must require reconciliation. Persist approval linkage and destination coordinates from broker ACK. Test concurrency, repeated approval use and recovery.
2. Add read-only inspect with strict broker/topic allowlists and exact assign/seek, no commits or auto-create. Check service remains inactive/dead/disabled and reject unexpected broker topology. The source may have expired or been deleted.
3. Add separate explicit replay command with bounded runtime, default mutation gate off, and revalidate approval and original bytes immediately before sending. Use one isolated destination per approved review, no main/live topic and no existing consumer group offsets. Keep historical=true, production_ready=false and automated_response_allowed=false in metadata.
4. Test on NEW isolated fixtures; do not rerun setup/repair against old checkpoint resources. Replaying bytes does not make poison valid. Do not open interfaces, enable services, install drivers, use GPU or automated response.

Run offline tests: `python -B shadow/test_bluefield_operator_contract.py` inside a project venv.
