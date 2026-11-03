# EDRXDR–Morpheus–NEXUS: master delivery acceptance

Prepared 2026-11-04 Asia/Bangkok. Status: DELIVERY_NOT_ACCEPTED.
This is the single work breakdown for the user's requested complete delivery.
Existing handoffs are historical evidence, not current runtime verification.

## What counts as finished

A teammate can install a pinned release, receive verified real telemetry, inspect
correctly attributed detections/evidence, operate approved response workflows,
recover after failures and restore from backup using the delivered documentation.
Each acceptance item needs a dated, reviewed evidence receipt bound to the tested
source/config/model versions. Mock/sample success is not live quality acceptance.
No item is passed merely because a menu, container, model or script exists.

The machine-readable acceptance.json lists required gates, dependencies, current
evidence and remaining tests. It initially passes no gate: historical partial
successes are recorded without pretending they cover the full acceptance scope.

## Current evidence and limits

- Last operator-confirmed Git HEAD b426351 on work/nexus-exact-ai-v1, with a
  staged handoff and existing untracked WIP. Do not reset/clean or stage broadly.
- NEXUS Model Lab deployed; operator-reported reader totals 773 sample/replay
  observations (666 DFP Duo, 107 Ransomware CPU). Not 773 live detections.
- DFP CPU prototype fit/reload/inference on twelve fitting windows, no independent
  evaluation or threshold. Raw frozen capture candidate matched 822 records,
  822 memberships and twelve feature/input windows; all windows incomplete.
- Owner approved a single 55-minute manager-wide archive pilot with restoration,
  200MiB soft growth guard and 10GiB minimum free disk. Successful preflight at
  /mnt/nexus-copilot-mQTssj/dfp-approved-preflight-qui6r9nz; runner instructions
  were delivered, now completed/restored with 920 lines; offline preparation yielded 845 Agent003 records and the frozen CPU diagnostic passed on twelve new windows. See ../DELIVERY-CHECKPOINT-20261104.md for bound receipts.
  Never start a duplicate pilot to find out whether it is running.
- Automated response off; DFP not deployed live; BERT not replaced. Ransomware
  live class mapping/telemetry not accepted. Host CUDA999 unresolved.

## Ordered implementation work

### A. Preserve and establish the release boundary

Collect read-only Git/runtime and pilot state. Preserve staged/untracked work.
Define pinned source, dependency/image/model/config manifests, private ownership
and supported deployment target. Inspect relevant AGENTS.md before repo writes.
Do not mistake the source checkout for the active runtime directory.

### B. Finish the Agent003 data path

Verify the authorized pilot's actual status and restoration first. Bind the new
capture and exposure ledger, independently review coverage and membership, retain
incomplete intervals/exclusions explicitly. Use versioned extractor source and
schema. Test restart, alias/rotation/truncation, partial records, retries and gaps.
No zero padding of unobserved windows or silent legacy UID changes.

### C. Establish DFP quality before changing production decisions

Freeze model/scaler/feature versions and score semantics. Define independent
chronological evaluation with representative activity and label limitations before
scoring. Specify performance/latency/resource and nuisance-alert criteria in a
reviewed protocol; numbers are not invented here. Twelve in-sample windows do
not satisfy this. Extra training/scoring/collection requires its approved scope.

### D. Establish Ransomware live compatibility

Confirm output class mapping from trusted model/training provenance. Select and
authorize compatible real endpoint telemetry and freeze snapshot/process/window
identity plus the 297-feature input contract. Preserve sample replay separately.
Independent evaluation and false-alert evidence precede any live routing.
Wazuh/FIM counts are not substitutes for AppShield features.

### E. Define the role of BERT and route each detector honestly

BERT severity, DFP behavioral anomaly and ransomware process classification solve
different tasks. Define which specific BERT function is retained/replaced and by
what evidence. Do not relabel a reconstruction loss as severity/probability.
Use explicit unavailable/not_scored/conflict states and independent versioned
schemas. Shadow results first; prove routing, idempotency and rollback before a
switch. Do not open protected BERT holdout or retrain as a shortcut.

### F. Complete user-facing and response workflows

NEXUS must separate live/replay and display true source time/identity, model
version, uncertainty/unavailability and citations. Authenticated real-browser
acceptance is required for Overview, Events, Model Lab and Copilot.
Copilot text remains an unreviewed draft, not a response authorization.

First implement reviewed manual response: permissions, exact target binding,
explicit action/expiry, audit trail, idempotency, rate bounds and rollback.
Then test a narrowly allowlisted automatic policy on an authorized test endpoint,
including false-alert suppression and a kill switch. No new response activation
is authorized by this document or the archive pilot approval.

### G. Operations, recovery and delivery

Validate retention/storage bounds, health/lag/error monitoring and operator alerts.
Pin a reproducible installation and verify restart/reboot behavior on a permitted
target. Test backup restore in isolation (not by overwriting production), verify
private secret handling, access controls and absence of raw data/keys in repo.
Run documented end-to-end and sustained failure/recovery tests, with observation
duration and acceptance criteria fixed before testing. Deliver setup, operation,
troubleshooting, rollback and data/model limitation documents and have a teammate
follow them on a clean target. Existing tar downloads are not restore acceptance.

## Scope decisions still required

The user now wants a complete delivery, but prior restrictions still defer
Agent004 and exclude Network/BlueField. Record an explicit inclusion/exclusion
decision and deliverable implications; do not silently mark them complete or
begin work on those devices/networks. Access, GPU bookings, telemetry installs,
reboots and response actions retain their separate authorization boundaries.

## Immediate next action

Run collect_status.py once. It verifies this package and runs synthetic readiness
tests, reads metadata/status only, and records private aggregate status without
opening model/data/key/config content. It checks the saved pilot attempt, unit
status and unauthenticated loopback HTTP behavior; never starts/retries a pilot.
Use its output to continue the existing pilot or restoration review, not launch
new logging. No repo/index/service changes or external publication.

After current state is established, install reviewed delivery sources into new
repo paths with exact-file review; keep the existing staged handoff separate.
No docs/code here have been installed or committed on VM merely by packaging.
