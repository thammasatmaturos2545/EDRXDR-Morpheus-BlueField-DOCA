# Isolated source-reader integration fixture (step 6)

Installer is offline and add-only. Runtime is separately gated by
BLUEFIELD_OPERATOR_FIXTURE_ALLOWED=1 and the host wrapper verifies the BlueField
service remains inactive/dead/disabled. Use the existing pinned image; no installs.

Runtime scope: explicitly create ONE fresh opread-UUID source topic, one partition,
replication factor 1, 24-hour record retention. Publish ONE synthetic JSON byte
string with carrier=2, require acknowledged partition 0 offset 0, then verify
original SHA256 using the step 5 reader and step 4 core. This is NEW synthetic data,
not historical telemetry and not a recovered quarantine record. The envelope and
plan are fixture metadata built locally, not retrieved/authenticated quarantine
sink evidence. No operator approval is issued; the plan destination is never created
or written. This is not controlled replay or a test of the full quarantine pipeline.

Negative checks: wrong expected hash, offset at log end, and another fresh missing
topic. Confirm missing topic stays absent and source watermark stays 0..1. Hash
mismatch uses a separately valid synthetic plan, not mutation of a frozen plan.
Actual retention expiry is NOT tested by the runtime; offline tests cover retention.

No consumer commit calls exist in the reader. This test does not independently
inspect broker consumer offsets or prove absence of all broker mutations. Its only
intended writes are explicit source-topic creation and one fixture record. No live
pipeline topic, OpenSearch index, GPU, network interface or service is changed.

The wrapper has a 120-second in-container deadline plus host timeout; logs emit
intent/run ID before creation, ACK coordinates, and final PASS or failure. Topic
creation or delivery uncertainty stops without retry/adopting an existing topic.
Each invocation is a NEW run. Do not blindly rerun after uncertainty; inspect the
printed run/topic first. No cleanup/delete command runs. Topics remain after record
retention; resource cleanup must be a separate reviewed action scoped to that run.

Run only after installation review:

    BLUEFIELD_OPERATOR_FIXTURE_ALLOWED=1 bash shadow/run_bluefield_operator_fixture.sh

Capture stdout/stderr and exit status in a new evidence directory. The wrapper
starts a bounded container using the pinned existing image, caps CPU/memory/PIDs,
mounts shadow read-only, drops capabilities, has no GPU request and never pulls.

PASS is source-reader integration only. Still pending: authoritative quarantine
retrieval, canonical approval/journal binding to transport, controlled publication,
and operator review/replay audit end-to-end. No production readiness is implied.
