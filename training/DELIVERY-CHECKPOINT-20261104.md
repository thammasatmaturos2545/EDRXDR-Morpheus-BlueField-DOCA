# EDRXDR–Morpheus–NEXUS checkpoint — 2026-11-04

Status: FROZEN_CPU_NEW_CAPTURE_DIAGNOSTIC_VERIFIED; DELIVERY_NOT_ACCEPTED.
This document separates implementation evidence from model-quality acceptance.
Exact aggregate receipt hashes are verified by the installer before installation.

## Newly completed

- One owner-approved archive pilot completed and restored: logall_json=no,
  startup bytes/effective config restored and required Manager processes ready.
  920 captured lines / 788605 bytes. Raw data remains private on VM.
- New Agent003 data: 845 occurrences, twelve five-minute windows, three exact
  repeated-line occurrences retained. No raw-line hash overlap with prior fitting
  projection; all new event timestamps later than its latest event timestamp.
  This does not independently prove cross-capture event/physical-device identity.
- Exposure ledger: 607 checkpoints, maximum gap 5.596559757992509 seconds,
  stable observed file generation, zero draft clock indicators. Ten windows
  nominally inside observation interval, two boundary windows. Coverage still
  unknown; no window completeness flags upgraded.
- Existing frozen CPU model scored all twelve new windows representing 845
  records. No fitting, GPU, network, threshold selection or deployment occurred.
- Repeated-score parity and seven-feature transformed numeric MSE-mean parity
  passed. Actual fitted numeric scaler classes: seven StandardScaler instances.
- Previous failed diagnostic was caused by selecting the image's base Python
  without numpy. Corrected explicit /opt/conda/envs/morpheus/bin/python passed
  dependency imports and real frozen-model inference; no packages installed.

## Score interpretation

All twelve scores: minimum 0.15608443319797516, median 0.23594145476818085,
maximum 5.430511951446533. The ten nominal interior windows have that same maximum.
The two boundary windows range 0.2351214438676834 to 0.24487200379371643.
Only one window had the syscollector decoder indicator, and its score equals the
maximum. The capture contained 361 such indicated records. This association is
not proof of malicious activity or proof that syscollector caused the score.

Scores are mean squared reconstruction error after saved per-feature transforms,
not probabilities, z-scores, BERT severity or alerts. No threshold has been chosen.
The measured 0.00935114998719655 seconds covers the worker's scoring section only;
it excludes image/container startup, imports and model load and is not an end-to-end
latency benchmark or sustained throughput result.

## Evidence receipts

All paths below are private VM paths, not Git payloads:

- Capture SHA256: 6e8478a917eebe277e725b746c08b481f34f4b805f7a7d6e24a096ed1c68510f.
- Postcapture report:
  /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/dfp-postcapture-development-ksg7k9_y/aggregate-report.json
  SHA256 6de4aa5337450a5b3bf7359774169f04f22a8f63f00a72ff04dca985bdcb06df.
- Frozen CPU diagnostic report:
  /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/dfp-frozen-cpu-diagnostic-4itb1tqz/result/aggregate-report.json
  SHA256 e88839c64f9221b88c653126359046d2a053507f82653b249861eef13fdd6fc1.
- Model SHA256 ecacecb3128f9ac6987315e2a1861fb02ac873f9fc42ddc11798a9fc0c25157e.
- CPU source manifest SHA256 a32c517170fbf364581d65277ed9dc13ce497d1a1bd06b6b5a91c90e21183cc0.
- New features SHA256 90a5d3871341a6580bff524ff40edf75cc0cc4add1ea6d2841b2b895165d1fd2.
- Coverage sidecar SHA256 634382aa14562871d7dc5de6bbe9c6ab23458ab46c62297098b5c911f12e121f.

Only reviewed source, aggregate metadata/hashes and documentation belong in Git.
No capture, memberships, model, private scores, config, key or secret is included.

## Next work in order

1. Review coverage, source continuity and nuisance behavior. Define representative
   prospective calibration/evaluation data and label limitations before selecting
   any decision threshold. No independent quality evaluation is accepted yet.
2. Prepare DFP shadow transport/schema and NEXUS rendering with explicit source,
   model version, diagnostic/unknown coverage and no automatic response. Keep
   unavailable/not_scored/conflict distinct; never relabel loss as severity.
3. Validate shadow end-to-end and operational failure/retry behavior in isolation
   before any runtime switch. No DFP live collector is deployed by this checkpoint.
4. Continue the central 23-gate delivery plan at delivery-acceptance-v1/DELIVERY-PLAN.md.
   Ransomware remains sample replay; Agent004/Network/BlueField scope decisions
   and permissions remain outstanding. BERT is not replaced.

The old archive approval is consumed. Do not reopen logging, start training or
GPU work from this handoff. Current installer does not execute model/collection
code or modify runtime and does not push. Existing staged handoff/WIP stays intact.
