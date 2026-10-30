# BERT v4 error-review handoff — 2026-10-31

Read `BERT-V4-FAMILY2-ERROR-PROFILE-20261031.md` alongside paired/order diagnostics.
This round profiles existing outputs only. A private queue covers all41 family2
steps; it has not been semantically reviewed and contains no automatic approvals.

## Next bounded work

1. Review the family2 aggregate profile and private queue on VM. Establish whether
   required evidence is present and whether weak step labels apply to selected logs.
2. Recover original builder/provenance before changing sampling or feature design.
3. If a revised dataset/model is proposed, write a new version/protocol first,
   preserve current splits/checkpoints, and obtain training authorization separately.
4. Do not tune thresholds, remove difficult labels or select favorable subgroups to
   make the current final report look better. Current fixed threshold remains0.5.
5. `BERT-V4-FINAL-EVALUATION-DRAFT-20261031.md` remains DRAFT_NOT_APPROVED.
   Family6 and metadata/labels-16695.json remain unopened. No final authorization.

No inference, training, GPU, shared-state changes, service restart, deploy or delete
was performed here. Shared GPU rights must be rechecked for any later GPU work.
Do not touch LuckyFive, BlueField/rshim, automated response, offsets or review69
organization entries. Preserve unrelated untracked history/uid_lookup/evidence.

Private aggregate report: `/home/saiuser/EDRXDR-BERTv4-work/evidence/dev-family2-profile-bi_a_rm2/family2-report.json`.
Final reports/summaries stay distinguishable from live binary NEXUS Severity.
