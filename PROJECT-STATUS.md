# EDRXDR–Morpheus–NEXUS: implementation status

Updated 6 November 2026 from operator-confirmed evidence through source checkpoint `2e1dc9f`. This is a navigation and status record, not a new architecture specification or production acceptance. Recheck runtime and the original observer before further operations.

## Start here

1. Read [the latest paused handoff](https://github.com/thammasatmaturos2545/EDRXDR-Morpheus-BlueField-DOCA/blob/work/nexus-exact-ai-v1/training/HANDOFF-PAUSED-DFP-ENDPOINT-20261105.md).
2. Read [the project handoff](https://github.com/thammasatmaturos2545/EDRXDR-Morpheus-BlueField-DOCA/blob/work/nexus-exact-ai-v1/training/HANDOFF-PROJECT-NEXUS-ENDPOINT-20261105.md) and its linked Architecture v2, if present in this checkout. Architecture v2 remains the target authority; historical v1 handoffs do not override it.
3. Use the status table below to distinguish the target diagram from implemented behavior.
4. Read [source checkpoint scope](https://github.com/thammasatmaturos2545/EDRXDR-Morpheus-BlueField-DOCA/blob/work/nexus-exact-ai-v1/training/experiments/agent003-source-checkpoint-20261106/UPLOAD-SCOPE.md) before opening candidate copies.

## Target diagram versus evidence

| Diagram stage | Evidence available | Remaining work / limit |
| --- | --- | --- |
| Wazuh / endpoint telemetry | Existing Wazuh forwarder, normalizer and indexer; Agent003 test delivery verified | Source exposure and independent endpoint identity still need acceptance. Network/VPN are outside the current scope. |
| Ingestion, parsing, normalization | Existing transport plus offline auth normalization candidate tested | Do not imply every stage runs inside a single deployed Morpheus pipeline. Candidate journal normalization is not a live detector. |
| Feature extraction / routing | Auth-count engineering features and endpoint file-behavior tests | Freeze and accept feature/source contracts before live integration. Missing coverage is not a zero-event window. |
| DFP model inference | Two per-account CPU development models; fit/save/reload/scoring verified | Representative baseline, accepted coverage, independent evaluation and threshold pending. BERT has not been replaced. |
| Behavior anomaly score | Reconstruction loss available in native units | Loss is not a probability, attack label or calibrated severity. No validated alert threshold. |
| Ransomware memory/process inference | Sample/replay work exists; class mapping and live telemetry compatibility unresolved | No live process classifier accepted. No BlueField work in the current scope. Wazuh FIM does not supply a substitute for AppShield process/memory features. |
| Endpoint file behavior | Isolated test delivery 12/12, then controlled modifications 20/20 verified | These are delivery results, not ransomware accuracy. Normal bulk and controlled fast updates had identical case aggregate signatures. Protected paths must be chosen by the owner. |
| Post-processing / trusted publishing | Offline publisher, revision and evaluation candidates tested | Candidates are not deployed trusted-alert publishing. Require accepted evidence, scope and integration review. |
| SIEM / NEXUS | Diagnostic UI and Model Lab deployed according to prior operator checks; Model Lab 773 replay/sample observations | Those observations are not 773 validated detections. Legacy quality reports are not DFP/endpoint quality evidence. |
| Human Review / reports | Named reviewer staging and authenticated empty-catalog preview verified | No accepted live catalog workflow established by that preview. Latest preview/observer state must be checked; do not restart them from this document. |
| Response playbook | Review foundation; automated response remains disabled | No isolation/blocking/process termination enabled. Response needs separate scope, controls and acceptance. |

## Where the code belongs

| Location | How to interpret it |
| --- | --- |
| `frontend/` | Current branch UI/API source. Deployed runtime is a separate release directory; a Git push is not a deployment. |
| `normalizer/`, `indexer/`, `morpheus/` | Pipeline implementation source. Presence in Git does not prove deployment or operational quality. |
| `history/`, `uid_lookup/` | History and identity utilities. Do not run sync/probe scripts merely because they are present. |
| `training/experiments/agent003-source-checkpoint-20261106/` | Frozen source snapshots and design drafts. Duplicate candidate modules are intentional snapshots, not alternate production entry points. Do not deploy or auto-run them. |
| `training/HANDOFF-*.md`, `training/START-HERE-*.md` | Dated evidence/navigation. Read the latest paused/project handoffs first; older architecture and deployment statements are historical. |

Private datasets, models, registries, keys and raw logs remain outside this publication. Seven runtime evidence files remained untracked after the source push; they were not deleted or published.

## Next work, without reopening paused experiments

- Read-only reconciliation of the original observer completion and current runtime, within the owner's scope. No new observation or extension.
- Review source coverage and define representative baseline and chronological independent evaluation; keep final holdout closed.
- Agree and evaluate thresholds only under an approved protocol; keep account models and evaluation partitions separate.
- Integrate the trusted publisher and named-reviewer workflow only after review and runtime authorization.
- Obtain owner-selected endpoint protection paths and acceptance criteria before protection deployment.

Do not start GPU, training, logging, collector/observer rounds, live BERT cutover or automated response from this document. Agent004 remains paused; BlueField and Network remain outside the current scope. Preserve staged/untracked work and all private evidence.
