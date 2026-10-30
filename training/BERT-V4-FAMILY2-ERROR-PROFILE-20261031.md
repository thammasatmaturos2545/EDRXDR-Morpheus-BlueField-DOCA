# BERT v4 family2 development error profile — 2026-10-31

Base commit `c0c89c1e49a613018b442c307efe0427f07b59ee`. Reuses saved predictions; no model execution or label edits.
Family2 contains41 development steps. Only train1/3/5 and dev2/4/7 are read.
Original aggregate and family metrics reproduce the backed-up paired analysis.

## Row error categories

```json
{
  "fp_and_fn": 38,
  "fp_only": 3
}
```

## Per-tactic model errors and train/dev prevalence

| Tactic | Train positive/N | Family2 support/N | Predicted+ | TP/FP/FN | Precision | Recall |
|---|---|---|---:|---|---:|---:|
| collection | 13/458 | 4/41 | 0 | 0/0/4 | undefined | 0.0000 |
| command-and-control | 30/458 | 6/41 | 0 | 0/0/6 | undefined | 0.0000 |
| credential-access | 43/458 | 6/41 | 0 | 0/0/6 | undefined | 0.0000 |
| defense-evasion | 75/458 | 3/41 | 12 | 1/11/2 | 0.0833 | 0.3333 |
| discovery | 132/458 | 18/41 | 12 | 2/10/16 | 0.1667 | 0.1111 |
| execution | 113/458 | 1/41 | 34 | 1/33/0 | 0.0294 | 1.0000 |
| initial-access | 36/458 | 0/41 | 0 | 0/0/0 | undefined | undefined |
| lateral-movement | 14/458 | 2/41 | 0 | 0/0/2 | undefined | 0.0000 |
| persistence | 70/458 | 5/41 | 15 | 1/14/4 | 0.0667 | 0.2000 |
| privilege-escalation | 61/458 | 5/41 | 30 | 1/29/4 | 0.0333 | 0.2000 |
| reconnaissance | 72/458 | 0/41 | 2 | 0/2/0 | 0.0000 | undefined |

## Source composition

| Source | Train presence | Family2 presence |
|---|---:|---:|
| alerts.json | 152/458 | 5/41 |
| audit.log | 399/458 | 41/41 |
| auth.log | 151/458 | 6/41 |
| syslog | 169/458 | 34/41 |
| fast.log | 94/458 | 0/41 |
| access.log | 38/458 | 0/41 |
| daemon.log | 64/458 | 6/41 |
| kern.log | 43/458 | 2/41 |

Source-set total variation: 0.699702. Descriptive composition distance only, not statistical significance or causality.

## Source-set groups

| Sources | Family2 N | Train N | B micro F1 | Source-only micro F1 |
|---|---:|---:|---:|---:|
| alerts.json, audit.log, auth.log, syslog, daemon.log | 3 | 38 | 0.000000 | 0.000000 |
| audit.log, syslog | 28 | 25 | 0.000000 | 0.000000 |
| audit.log, auth.log | 1 | 8 | 0.000000 | 0.000000 |
| alerts.json, audit.log, auth.log, syslog, daemon.log, kern.log | 2 | 4 | 0.666667 | 0.000000 |
| audit.log | 6 | 183 | 0.137931 | 0.000000 |
| audit.log, syslog, daemon.log | 1 | 0 | 0.666667 | 0.000000 |

## False positives and co-occurring weak targets

- Predicted FP `defense-evasion` occurs with weak targets: command-and-control=3, discovery=2, execution=1, lateral-movement=2, persistence=4, privilege-escalation=4.
- Predicted FP `discovery` occurs with weak targets: command-and-control=3, defense-evasion=1, execution=1, lateral-movement=2, persistence=5, privilege-escalation=5.
- Predicted FP `execution` occurs with weak targets: collection=4, command-and-control=5, credential-access=6, defense-evasion=3, discovery=16, persistence=2, privilege-escalation=2.
- Predicted FP `persistence` occurs with weak targets: collection=3, credential-access=3, defense-evasion=1, discovery=7.
- Predicted FP `privilege-escalation` occurs with weak targets: collection=4, command-and-control=3, credential-access=6, defense-evasion=2, discovery=16.
- Predicted FP `reconnaissance` occurs with weak targets: command-and-control=1, discovery=1.

Each row can contain multiple weak targets, so these counts are nonexclusive.
This is not a single-class confusion matrix or proof of label corruption.

## Review queue and restrictions

All41 family2 steps have private review entries at `/home/saiuser/EDRXDR-BERTv4-work/evidence/dev-family2-profile-bi_a_rm2/review-queue-private.json`.
Entries contain identity/source/target/prediction metadata, no decoded logs or tokens.
Every entry remains unreviewed. An analyst must independently establish label/source
provenance; disagreement with the model alone must never rewrite labels.
Do not export the private queue or examples to chat/Git. Source availability does
not prove informative log content. No causal explanation is accepted from these
descriptive correlations alone. Only3 dev families exist; no population claim.

Aggregate report: `/home/saiuser/EDRXDR-BERTv4-work/evidence/dev-family2-profile-bi_a_rm2/family2-report.json`
SHA256: `2bab3cde965ef610d2b4d2563facb525e1b7ae86da1132303dd94383febaff10`
No training, threshold changes, GPU, final holdout, dataset edits or deployment.
