# NEXUS Model Lab integration acceptance — 2026-11-03

Status: PREVIEW_VERIFIED_NOT_DEPLOYED. No production approval implied.
Repo last operator-confirmed: work/nexus-exact-ai-v1 / 90834b8.
Existing untracked/WIP must remain untouched; no reset/clean/git add .

## Verified observations

- Source archive SHA256: 4a78e23737ff5967b93906226f7bff8565b2f33b2ff36e50afcf697dc9d3f23b.
- Original candidate staged independently, offline server/UI tests, existing
  nexus-soc regression and strict TypeScript passed on VM (operator outputs).
- Turbopack build rejected an external node_modules symlink; Webpack build
  succeeded without changing dependencies or production .next (operator outputs).
- GET /api/nexus/v1/lab rejects unauthenticated access with 401; authenticated
  all/DFP/Ransomware totals were 667/666/1, complete flags and page sizes verified.
- Direct browser checks: all 667 results; Next/Previous pagination; DFP filter
  666; Ransomware CPU filter 1; class mapping remains explicitly unverified.
- Badge patch app SHA256:
  d4a076263c704bc8fcaf0f619838a150224bbe871360a6c050cf5c464c84ada6.
  Browser verified Lab replay / LAB and restore of non-Lab status on navigation.
- Candidate initially lacked WAZUH_COMPOSE_PROJECT. A metadata-validated value
  from the original runtime was applied only to preview (operator output).
  Direct browser recheck: Overview API CONNECTED, 110 events, 100 alerts,
  2 observed endpoints. Counts are not model quality or endpoint-health evidence.
- Browser confirmed Model Lab still returns 667 after that configuration change.

## Runtime and data scope

- Preview source: /mnt/nexus-copilot-mQTssj/incoming/model-lab-Dqp24IqX/candidate/frontend.
- Preview: loopback 3013; tunnel 13013. Current transient unit at last report:
  nexus-model-lab-preview-3013-v2.service. Original one-hour deadline retained.
- Production 3006 at nexus-uid-candidate-wgpajvXL was not switched.
- Fixed reader: http://127.0.0.1:9200/edrxdr-ai-lab-v1/_search only.
- Default disabled; NEXUS_MODEL_LAB_ENABLED=1 required in an approved runtime.
- Reuses History authentication; never copy secrets into Git or this document.
- Lab outputs are dataset replay from model result artifacts, not Wazuh alerts.
- DFP values are z-scores, not probability. Ransomware positions are not named
  classes. No new inference, training, GPU execution or data writes from preview.
- Legacy BERT/severity, Kafka offsets and automated response were not changed.
- Host CUDA error 999, ransomware class mapping and quality validation remain open.

## Evidence references on VM

- integration-package-73C9gztG/offline-import-VBMrTLYP/lab-observations.ndjson
- training/DFP-RANSOMWARE-LAB-TRANSPORT-20261103.md (operator-created, untracked)
- incoming/model-lab-Dqp24IqX/build-webpack-Zyn5T1hS/build-private.log
- incoming/model-lab-Dqp24IqX/badge-fix-0wutp5ow/ (private backup)

Paths above are relative to the recorded lab/staging roots; retain private logs
on VM. No private observations or model files are included in this source package.

## Remaining before any production switch

1. Review source diff and preserve current source/runtime/WIP fingerprints.
2. Apply only approved source files and record the reviewed state in Git.
3. Build a separate release with existing dependencies using Webpack; never build
   over the active runtime .next. Verify runtime config source and auth scope.
4. Prepare a reversible 3006 switch with old WorkingDirectory/config preserved;
   obtain explicit production-switch authorization before changing its service.
5. Recheck authentication, Lab filters, Overview and legacy History/Copilot after
   any approved switch; revert only the scoped runtime change if checks fail.

No source application, Git commit, production switch or push performed by
preparing this review package. VM preview may auto-expire; do not treat this
document as a command to extend the approved preview period.
