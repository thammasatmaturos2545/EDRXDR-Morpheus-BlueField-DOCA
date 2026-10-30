# Family2 annotation and source-duplication audit — 2026-10-31

Base HEAD `edf2159b091793e4338dfa99c5d3c5220e766e10`. Exploratory tokenizer-only audit, no model/GPU execution.
Original archive, all104 exact family2 steps/ source prefixes and frozen rows
were revalidated. All41 candidate inputs still reconstruct exactly.

## Row-level possible annotation indicators

```json
{
  "bounded_candidate": {
    "technique_id_like_text": 41,
    "audit_key_technique_indicator": 41,
    "audit_key_tactic_name_indicator": 5
  },
  "selected_input": {
    "technique_id_like_text": 6,
    "audit_key_technique_indicator": 6,
    "audit_key_tactic_name_indicator": 0
  },
  "omitted_tail": {
    "technique_id_like_text": 35,
    "audit_key_technique_indicator": 35,
    "audit_key_tactic_name_indicator": 5
  }
}
```

## Lexical source-body comparisons

```json
{
  "pairs": 92,
  "exact_selected_body_pairs": 6,
  "selected_prefix_containment_pairs": 9,
  "selected_common_prefix_ge16_pairs": 11,
  "exact_candidate_body_pairs": 7,
  "rows": 41,
  "rows_with_selected_prefix_ge16": 6,
  "rows_with_exact_selected_body_pair": 6,
  "rows_with_exact_candidate_body_pair": 6
}
```

## Candidate indicators absent from current selected input

```json
{
  "candidate_not_selected__technique_id_like_text": 35,
  "tail_not_selected__technique_id_like_text": 35,
  "candidate_not_selected__audit_key_technique_indicator": 35,
  "tail_not_selected__audit_key_technique_indicator": 35,
  "candidate_not_selected__audit_key_tactic_name_indicator": 5,
  "tail_not_selected__audit_key_tactic_name_indicator": 5
}
```

Technique-ID-like text and quoted monitoring keys are flags, not established
dataset-label leakage. No ID-to-tactic mapping is used. No heuristic matches
does not imply leakage-free data. Source headers were excluded from duplicate
comparisons. Shared timestamp/boilerplate prefixes need semantic review.
Pairwise overlap counts are not additive token savings or permission to drop logs.

Audit performed after examining development outcomes and one case; not a blind
test or causal study. There are no error-free family2 controls in these41 rows.
The original preprocessing/protocol/model/labels remain unchanged.

Private per-step flags (no snippets/annotation values): `/home/saiuser/EDRXDR-BERTv4-work/evidence/family2-annotation-audit-aaocr5u2/flag-review-queue-private.json`.
Aggregate report: `/home/saiuser/EDRXDR-BERTv4-work/evidence/family2-annotation-audit-aaocr5u2/annotation-duplication-summary.json`.
Report SHA256: `ebe3e60ea8d446bef4f17b9c8c958c62eb20b52e5ccc28d83c693a8edfadd05d`.
All flags remain unreviewed. Family6/sequences payload and labels metadata were
not opened. No new training, weights, inference, GPU, final evaluation or deploy.
