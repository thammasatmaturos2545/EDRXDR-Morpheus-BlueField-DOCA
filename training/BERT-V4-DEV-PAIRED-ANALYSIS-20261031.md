# BERT v4 paired development analysis — 2026-10-31

Base HEAD `d297033499b23a36e234a249beb0f8cc58332a86`. Reuses frozen development predictions and the exact frozen
source-set train-count baseline. No new model execution, training or holdout access.
Reconstructed global counts/metrics match previously backed-up reports.

## B versus source-only across 123 positive label assignments

- Both correct positive: 12.
- B-only correct positive: 27.
- Source-only correct positive: 11.
- Both miss positive: 73.
- Both false positive: 43.
- B-only false positive: 100.
- Source-only false positive: 43.

These are paired label assignments, not counts of independent attacks/events.
B-only successes do not prove causal reliance on content. The source baseline
is deliberately simple and is not an exhaustive source-only learner comparison.

## Development family breakdown

| Family | N | B macro/micro | Reverse macro/micro | Source-only macro/micro |
|---|---:|---|---|---|
| 2 | 41 | 0.043723/0.077419 | 0.037655/0.077670 | 0.000000/0.000000 |
| 4 | 19 | 0.199519/0.477064 | 0.060315/0.186047 | 0.195896/0.453333 |
| 7 | 12 | 0.233766/0.341463 | 0.158730/0.277778 | 0.238095/0.300000 |

## Source cohorts

| Cohort | N | B macro/micro | Source-only macro/micro |
|---|---:|---|---|
| single_source | 14 | 0.134033/0.226415 | 0.060606/0.090909 |
| multi_source | 58 | 0.164632/0.261905 | 0.139899/0.209524 |
| seen_source_set | 64 | 0.151598/0.196850 | 0.194594/0.221154 |
| unseen_source_set | 8 | 0.225207/0.549020 | 0.000000/0.000000 |

## Per-tactic paired benefits and errors

| Tactic | Both TP | B-only TP | Source-only TP | B-only FP | Source-only FP |
|---|---:|---:|---:|---:|---:|
| collection | 0 | 0 | 0 | 0 | 0 |
| command-and-control | 0 | 0 | 0 | 3 | 0 |
| credential-access | 0 | 0 | 0 | 0 | 1 |
| defense-evasion | 1 | 10 | 4 | 13 | 1 |
| discovery | 0 | 4 | 0 | 19 | 0 |
| execution | 0 | 1 | 1 | 13 | 1 |
| initial-access | 0 | 0 | 6 | 0 | 33 |
| lateral-movement | 0 | 0 | 0 | 1 | 1 |
| persistence | 5 | 5 | 0 | 15 | 3 |
| privilege-escalation | 5 | 6 | 0 | 32 | 3 |
| reconnaissance | 1 | 1 | 0 | 4 | 0 |

## Interpretation limits and next step

Only three development families are available. Rows/labels can be correlated;
no population confidence interval or significance claim is issued. Subgroup
macro averages all 11 labels, even when some have zero subgroup support.
Development reuse is exploratory. Do not choose whichever subgroup/metric looks
best after seeing outcomes. No threshold/label/split/model changes are made.
Review this evidence before proposing a new protocol or one-time final test.

Private aggregate report: `/home/saiuser/EDRXDR-BERTv4-work/evidence/dev-paired-analysis-jeq0_4dn/paired-report.json`
SHA256: `5f2815ba307769f247fca1e110fb58d66fa997f407c0bbb511b11c05804277a6`
Source checkpoint/data/protocol reports remain untouched. Per-step private
predictions, tokens, raw logs and weights are not included in this document.
