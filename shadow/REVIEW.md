# Shadow review — 11 October 2026

## Changes prepared locally

1. Persist the known-working HOME/XDG/CUPY/CUDA cache paths in the shared Compose environment.
   Defaults, resource limits, UID/GID, mounts, networks and execution gates remain closed/unchanged.
2. Fix incomplete OpenSearch acknowledgement acceptance in shadow/pilot.py. A matching document ID alone
   was previously sufficient when _shards was missing; an index acknowledgement must now contain the
   correct index and at least one successful shard, with zero failed shards, before input commit.
3. Harden Shadow display contracts: AE coverage and states/routing/novelty must agree; null Wazuh levels
   remain unknown; integer rule IDs are accepted; only validated fields for the correct model kind are
   projected. Nested metadata and opposite-model payload fields cannot leak via the old shared allowlist.
4. Show conflicting Behavioral rule/time in row details. Abort stale requests and bound client fetch time.
5. Update README/HANDOFF interpretation without editing historical evidence. Regenerate PACKAGE_SHA256
   for this source revision. source-lock.json and scoring/preprocessing/model pins remain unchanged.

## Evidence and coverage assessment

Source: training/evidence/dashboard-20261011/reported-result.json (a summary of user-provided VM/API/browser
observations) and training/evidence/shadow-20261011/join-evidence.txt (stored join report).
No fresh connection to the VM was made in this review.

| Observation | What it establishes | What it does not establish |
|---|---|---|
| 32 severity / 32 behavioral, matched32, conflicts0, unmatched0 | Paired stored outputs for the reported batch | Capture of all live events or future/current service health |
| raw hashes match32 | Stored provenance agrees across the two outputs | Independent rehash of original Kafka bytes in this review |
| candidates13, all reported as rule19008 level3 | 13/32 severity outputs flagged weak-label candidate (40.625%) | Confirmed attacks, independent false positives, or FPR for rule19008 |
| AE-scored0 / behavioral32 | 0% AE-scored coverage for this batch | AE accuracy, safety of unscored events, or an AE score of zero |
| semantic novelty1 | One stored novelty flag | One attack |

The export contains neither the actual 32 document payloads/raw input texts nor the source-locked replay
engine/validators/model weights. Therefore rule19008 text/host/template distribution cannot be audited here,
no existing AE-scored Replay case can be selected reliably, and identical-input score parity cannot be run.
Do not infer candidate-rule prevalence beyond the supplied candidate aggregate. Preserve old-test/reserve;
do not tune threshold or train a new model from these display counts.

## Validation scope

- Incoming shadow/PACKAGE_SHA256.json matched all its listed files. It was consistent in bytes; its README
  and local report described earlier execution and needed clearer historical labels.
- Frontend Shadow suite: 20 checks PASS, including isolated render tests, invalid contracts, projections,
  unknown Wazuh level and scored/unscored coverage. Fixtures do not enter production routes.
- Existing frontend regression: 7 groups PASS. Dependencies/config and the two original 2026-10-09 report
  files were reused from earlier supplied workspace artifacts solely for local validation; no fabricated
  report files or new metrics were used. They are not included in this patch or used to replace VM reports.
- TypeScript and ESLint: PASS in that validation workspace.
- Python syntax: PASS. New recovery suite: 7 PASS with fake clients and a stub document validator.
  Covers lost publish/index ACK, retry overwrite, commit failure, missing index and incomplete ACK.
- Existing worker suite: 23 attempted; 16 test methods completed successfully, 7 methods encountered missing
  replay validators (8 error records including subtests). Full suite is NOT PASS locally. The archive omitted
  all 12 source-locked replay/training files. Pins were not changed and assertions were not disabled.
- New build and Docker Compose validation status are recorded separately in REVIEW_TEST_REPORT.json.
- Not run: fresh VM HTTP/browser checks, actual model/GPU scoring, replay-vs-shadow same-input score parity,
  real broker/index outage/restart tests, new training, capture, daemon, commit or push.

## Receiving this patch / Git review

The guarded installer compares each destination to the uploaded snapshot, backs up changed files, and stops
on intervening edits. It applies only listed source/docs/tests; it does not run a service or touch credentials,
model volumes, offsets or source-lock.json. After applying, run bash verify_shadow_review.sh on the existing
checkout. That checks pinned source and uses only CPU tests plus compose config (no containers started).
Keep the generated logs. Inspect git diff and untracked files before staging explicit paths; no git add .
or automatic commit is part of this patch. Historical evidence contains internal infrastructure metadata;
review before sharing outside the team. Do not commit raw data, weights, credentials or transient cache files.

Remaining actual parity/recovery experiments need an isolated, resource-authorized setup with pinned models
and identical captured input, not a restart/fault in the shared production Kafka/OpenSearch deployment.
