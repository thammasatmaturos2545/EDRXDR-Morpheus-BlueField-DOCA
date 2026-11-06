# EDRXDR–Morpheus–NEXUS: implementation status

Updated 6 November 2026: Git publication evidence through `9dfe02f`, plus reported experiment results in the owner-supplied HANDOFF-EDRXDR-MORPHEUS-NEXUS-20261106.md. Experiment artifacts have not been independently rechecked in this documentation update. The handoff Git HEAD `84ade7f` is historical; inspect actual HEAD before further changes. This is a navigation and status record, not a new architecture specification or production acceptance. Recheck runtime and the original observer completion evidence before further operations. The handoff reports the original observer completed; do not start or extend a round.

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
| DFP model inference | Two saved CPU models reportedly passed native Morpheus observed replay: 62 windows / 219 included records from 348 records, with 129 unscored accounted separately; direct-vs-pipeline maximum delta 0.0 | Representative baseline, accepted coverage, independent evaluation and threshold pending. BERT has not been replaced. |
| Behavior anomaly score | Reconstruction loss available in native units | Loss is not a probability, attack label or calibrated severity. No validated alert threshold. |
| Ransomware memory/process inference | Sample/replay work exists; class mapping and live telemetry compatibility unresolved | No live process classifier accepted. The newer handoff records an owner-selected endpoint direction using file-behavior rules alongside DFP; a new ransomware AI classifier is not required for that direction. This is a change from the older process/memory target diagram, not evidence that FIM supplies AppShield features. No BlueField work. |
| Endpoint file behavior | Prior delivery tests 12/12 and 20/20; newer handoff reports four native lab cases: quiet/bulk/rename no response, rewrite-plus-extension-change SIGTERM to an enrolled simulator after 6 of 12 files | These are delivery results, not ransomware accuracy. Normal bulk and controlled fast updates had identical case aggregate signatures. Newer handoff records only `/var/tmp/edrxdr-response-lab` and test-created files/simulators as the selected lab scope. This does not authorize general data-directory protection. Inotify does not identify the writer process. |
| Post-processing / trusted publishing | Offline publisher, revision and evaluation candidates tested | Candidates are not deployed trusted-alert publishing. Require accepted evidence, scope and integration review. |
| SIEM / NEXUS | Diagnostic UI and Model Lab deployed according to prior operator checks; Model Lab 773 replay/sample observations | Those observations are not 773 validated detections. Legacy quality reports are not DFP/endpoint quality evidence. |
| Human Review / reports | Named reviewer staging and authenticated empty-catalog preview verified | No accepted live catalog workflow established by that preview. Latest preview/observer state must be checked; do not restart them from this document. |
| Response playbook | Review foundation; automated response remains disabled | Newer handoff reports one completed scoped simulator-stop test, not a persistent service. No general process termination, blocking or isolation is enabled by this result. Lab response did not invoke DFP/Morpheus and is not connected to NEXUS. |

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

- Reconcile the reported completed observer: 348 records, 219 candidate records, 129 unscored, 62 account-time buckets and 2,735 polls. Technical integrity is not accepted coverage, baseline or quality. No new observation or extension.
- Review source coverage and define representative baseline and chronological independent evaluation; keep final holdout closed.
- Agree and evaluate thresholds only under an approved protocol; keep account models and evaluation partitions separate.
- Integrate the trusted publisher and named-reviewer workflow only after review and runtime authorization.
- Use only the reported owner-selected simulator lab scope for planning; review normal workloads, actor identity, kill-switch, audit and postconditions before further authorized tests or integration. No inference of general process-control permission.

Do not start GPU, training, logging, collector/observer rounds, live BERT cutover or automated response from this document. Agent004 remains paused; BlueField and Network remain outside the current scope. Preserve staged/untracked work and all private evidence.

## New handoff integration boundary

The latest handoff reports real native Morpheus CPU execution and a separate scoped lab response test. Neither result is an accepted independent quality evaluation. The DFP scores are reconstruction loss, not ransomware probabilities or MITRE labels. No accepted baseline, coverage or DFP threshold is reported. The new 62-window result is not the deployed 12-window diagnostic page or 773-observation Model Lab.

Critical path: review contracts and normal workloads; integrate live projection, trusted producer/policy, typed evidence reader and private review provisioning; connect only an identity-bound executor with action audit and recovery; inventory BERT producers/consumers before an approved cutover. Do not set threshold zero to publish every replay window as an attack.

Target dates in the handoff are conditional: main work by 20 November, verification and rehearsal 21–25 November, examination 27 November 2026. No acceptance gate is waived by those dates. The supplied handoff file itself has not been added to Git by this update.
