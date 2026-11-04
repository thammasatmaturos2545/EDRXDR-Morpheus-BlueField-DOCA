# START HERE — EDRXDR–Morpheus–NEXUS handoff — 2026-11-04

> **ACTIVE ARCHITECTURE:** [EDRXDR–DFP–RANSOMWARE–NEXUS v1](../docs/architecture/EDRXDR-DFP-RANSOMWARE-NEXUS-v1.md). DFP and Ransomware Detection are the active target pipelines. BERT v4 is superseded as an active target; retain its historical code, datasets, weights, checkpoints and evaluation evidence. Architecture approval does not mean implementation or model acceptance is complete.

## Receiving AI: start here

VM: saiuser@172.16.30.147. Repo: /home/saiuser/EDRXDR-Morpheus.
Branch: work/nexus-exact-ai-v1. Last confirmed application source commit:
aed1715a080205dc92544ab8b4c84a144adba0c5. This handoff adds a documentation
commit after it; inspect actual HEAD and Git status, never assume they match.
Owner subsequently approved Architecture v1 and authorized staged documentation alignment and implementation planning. Use the committed Architecture v1 as the authoritative target. Runtime details below are a historical snapshot; re-verify services, runtime and artifacts before operational changes. Architecture approval does not establish model acceptance or production readiness.

Read in order:
1. This document (latest deployment update supersedes older preview-only notes).
2. training/HANDOFF-NEXUS-DFP-DIAGNOSTIC-20261104.md.
3. training/DELIVERY-CHECKPOINT-20261104.md and training/delivery-acceptance-v1/DELIVERY-PLAN.md.
4. training/HANDOFF-DFP-APPSHIELD-PROGRESS-20261103.md including Follow-up.
5. training/START-HERE-DFP-HANDOFF-20261103.md.
Check applicable AGENTS.md before editing. Missing files require investigation,
not fabricated contents or silently skipped requirements.

## Current deployment: operator-confirmed, not newly inspected by this author

Production unit: nexus-all-events-prod-3006.service, loopback 127.0.0.1:3006.
New runtime: /mnt/nexus-copilot-mQTssj/release-dfp-aed1715-1l2ozb3v/frontend.
Previous runtime retained: /mnt/nexus-copilot-mQTssj/release-appshield-41Z1YA3K/frontend.
Owner explicitly approved and ran the production switch. Output:
NEXUS_DFP_3006_SWITCH_PASS; authenticated DFP 12 windows / 845 records;
unauthenticated DFP 401; Model Lab all=773 / dfp=666 / ransomware=107;
History and existing APIs passed. Webpack build passed from committed source;
123 runtime source files matched the browser-tested candidate.

Private switch evidence:
/mnt/nexus-copilot-mQTssj/release-dfp-aed1715-1l2ozb3v/switch-attempt-eeq7a317/switch-result.json
Release plan: same release directory, switch-plan-private.json.
One new systemd drop-in was installed; its exact path is in those private receipts.
All older drop-ins and releases were retained. Do not guess a filename or remove
old overrides. ROLLBACK_PASS printed before the tests was a synthetic test marker,
not an actual rollback of the successful production deployment.

Real browser success-path checks passed on preview 3013 before deployment.
Production browser verification is still PENDING: the owner opened the production
URL but no completed UI check was recorded before pausing. Test loopback tunnel
http://127.0.0.1:13006/nexus/index.html#dfpdiagnostic. If unavailable, inspect the
tunnel separately from VM service health. Preview was limited to one hour;
expiry is normal. Do not extend or restart it under the old authorization.

## What the features mean

DFP Diagnostic is an authenticated, read-only viewer of frozen CPU results.
It does not collect events, invoke models, write Kafka/OpenSearch, select a
threshold or detect live attacks. Under Architecture v1, DFP and Ransomware Detection are the active target pipelines; BERT v4 is superseded as an active target and preserved as legacy. API is disabled by default;
production explicitly enables it with a server-pinned private artifact hash.
Model Lab is sample/replay: 666 Duo DFP observations and 107 ransomware CPU
observations (including AppShield replay). These counts are not live quality.

DFP model was fitted on 12 historical windows; CPU save/reload/inference passed.
A subsequent capture produced 12 windows / 845 Agent003 records and scored with
that frozen model, without fitting. Ten windows were nominally inside observation,
two were boundary windows. ALL have unknown/unaccepted source coverage;
independent quality-evaluation windows = 0. Repeated score and numeric-loss-mean
parity passed. Seven fitted numeric scalers were StandardScaler.
Score semantics: mean squared reconstruction error over transformed numeric
features; not probability, percent, severity or an attack verdict. Values above
one are valid. Maximum observed loss 5.430511951446533; association with a
syscollector-containing window does not establish maliciousness or causation.

Feature order: record_count, rows_with_structured_user,
rows_with_structured_source_ip, rows_with_fim_path, full_log_bytes_total,
distinct_decoder_names, full_log_bytes_mean. Five-minute UTC windows.

## Evidence anchors (private on VM)

Lab root: /home/saiuser/edrxdr-nvidia-lab-znmqaTGL.
- Model: dfp-archive-cpu-prototype-uy_2ita1/model-private.pkl.
  SHA256 ecacecb3128f9ac6987315e2a1861fb02ac873f9fc42ddc11798a9fc0c25157e.
- CPU report: dfp-frozen-cpu-diagnostic-4itb1tqz/result/aggregate-report.json.
  SHA256 e88839c64f9221b88c653126359046d2a053507f82653b249861eef13fdd6fc1.
- Postcapture preparation: dfp-postcapture-development-ksg7k9_y/aggregate-report.json.
  SHA256 6de4aa5337450a5b3bf7359774169f04f22a8f63f00a72ff04dca985bdcb06df.
- New capture SHA256 6e8478a917eebe277e725b746c08b481f34f4b805f7a7d6e24a096ed1c68510f.
- Published viewer artifact: /mnt/nexus-copilot-mQTssj/dfp-diagnostic-published-v1/diagnostic.json.
  SHA256 0c308abf281a18a60e22d9382b6c1553c5f4e2b3b19132dbf145635dff66975e.
Verify locally against receipts; do not export private contents into chat.

The approved 55-minute manager-wide archive probe finished and restored original
startup/effective configuration, logall_json=no, Manager ready. That approval was
one-shot and is consumed. No logging/collector should be presumed active now.
Capture completeness and physical device identity remain unverified.

## First read-only checks

On VM, not Windows PowerShell:
```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
date -Is
GIT_OPTIONAL_LOCKS=0 git branch --show-current
git --no-pager log -4 --oneline
GIT_OPTIONAL_LOCKS=0 git status --short
git --no-pager diff --check
systemctl --user show nexus-all-events-prod-3006.service --no-pager -p ActiveState -p SubState -p WorkingDirectory -p MainPID
systemctl --user list-units --all --no-pager 'nexus*' 'edrxdr-archive*'
systemctl --user list-timers --all --no-pager 'edrxdr-archive*'
docker ps --format 'table {{.Names}}	{{.Status}}'
curl --max-time 10 -sS -o /dev/null -w 'NEXUS_HTTP %{http_code}\n' http://127.0.0.1:3006/nexus/index.html
```
Read private receipts locally and print only allowlisted aggregate fields.
Never print /proc environments, Docker environment values, authentication files,
private configurations, raw log bodies or full API event responses.

## Next work, in order

1. Verify current Git/runtime and switch receipt; finish production UI success-path
   checks: 12 rows / 845 records, loss semantics, unknown coverage, reload, navigation
   and Model Lab 773/666/107. Distinguish preview checks from production checks.
2. Record aggregate evidence in a new docs-only commit while preserving staged WIP.
3. Plan DFP Agent003 source exposure and representative baseline/independent
   evaluation. Freeze coverage/identity/feature definitions and acceptance before
   collecting again. Do not label incomplete windows complete to advance a gate.
4. Implement/test an isolated prospective shadow candidate and failure/rotation/
   restart handling offline before proposing a bounded deployment. Do not turn
   the frozen-capture adapter into an accepted live identity contract by assertion.
5. Progress delivery acceptance honestly: operational monitoring, recovery/restore
   verification, reproducible artifacts and teammate instructions remain gates.

Ransomware remains sample/replay in the last verified runtime snapshot. Compatible live telemetry and class mapping remain implementation and acceptance gates under Architecture v1, not excluded from scope. BERT v4 is superseded as the active target by ../docs/architecture/EDRXDR-DFP-RANSOMWARE-NEXUS-v1.md. Its historical artifacts remain preserved and unchanged. Host CUDA error
999 was not resolved by these CPU diagnostics. No GPU or new training booking
is active. Automated response remains OFF; policy, approval, audit, rollback and
controlled end-to-end validation must precede any response automation.

## Preserve shared work and approval boundaries

Known staged work: training/START-HERE-DFP-HANDOFF-20261103.md (verify actual index).
Known untracked/WIP includes history/, uid_lookup/, older training handoffs,
training/DFP-RANSOMWARE-LAB-TRANSPORT-20261103.md, START-HERE-TEAM-20261101.md,
and training/evidence/nexus-reconciliation-20261020/ and nexus-systemd-20261020T012409921855Z/.
Preserve ALL actual WIP, not just this list. No reset/clean, broad git add,
force checkout, deletion or overwrite. No push was performed for this handoff.

No new GPU/training/logging/collector, runtime restart/switch, Kafka/OpenSearch
writes, threshold/class/label changes or changes to preserved BERT artifacts without agreed scope.
Prior one-off approvals do not authorize new rounds. Use exact project/service/
container identities; LuckyFive shared stack and peer processes are not targets.
Do not share raw logs/datasets/weights/keys/secrets in chat or public Git. A
successful UI deployment is not final project completion or model acceptance.
