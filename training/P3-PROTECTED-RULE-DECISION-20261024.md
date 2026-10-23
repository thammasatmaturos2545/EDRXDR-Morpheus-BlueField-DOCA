# P3 protected-rule decision — 2026-10-24

Checkpoint dataset manifest SHA256: `354e3c9dc9febe49173fa416cdd943cf3512540dded5f18e0ae3d800908b8669`.
Inventory SHA256: `8b4f56796c1d4d6d5bc71b4172ffb10bc3d78c09185ed1396f3adde1f6ae18c6`.
Checkpoint training report binds this manifest and records smoke=false.
This is not fresh proof of runtime model/weights binding.

## Decision superseding earlier pending training-eligibility notes

- Rule550: checkpoint quarantine_old_test=157; all 55 P3 rows are excluded
  from training under the existing whole-rule protection policy, including
  the one event linked to recorded lab evidence. Provenance linkage stays valid;
  it does not override split policy. No physical data was moved or reassigned.
- Rule2901: checkpoint validation=258; all 7 P3 rows are excluded from training
  under the existing validation rule policy even if their UIDs are new.
- Keep original baseline/design/integrity/link records as history, interpreted
  with this eligibility decision. No validation/quarantine/reserve examples opened.

## Aggregate policy classification

- existing_train_rule_requires_review: rules=23, high=1796, low=5229
- excluded_validation_rule: rules=4, high=548, low=1187
- excluded_quarantine_rule: rules=4, high=304, low=1604
- excluded_reserve_rule: rules=6, high=579, low=687
- unseen_rule_pending_policy_review: rules=53, high=55, low=8005

Existing train-rule rows still need provenance, UID/template overlap and time/endpoint
review before use. Unseen rules are pending policy review, not automatically eligible
or assigned to reserve/train. Positive counts are weak severity labels, not attacks.

Private report: `/mnt/nexus-copilot-mQTssj/p3-rule-policy-zhcbvmd6/result.json`
Report SHA256: `266f93ed52b941b14befb57d9be96ecf0e53bd187a4e3e3b73a74bcb83f8e66f`

No model scoring/training/GPU, threshold/offset changes, original dataset edits,
holdout text access, staging, commit or runtime changes.
Next: evaluate available non-protected positive-rule diversity from this report.
If insufficient, document a prospective authorized acquisition plan rather than
reusing protected rules or tuning on holdout results.
