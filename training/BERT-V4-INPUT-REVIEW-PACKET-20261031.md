# BERT v4 private input review preparation — 2026-10-31

Base commit `ebafa4b9904ac417f966ddd89ab9156fc9c43021`. Tokenizer-only CPU rendering; no weights/model/GPU loaded.
Uses pinned development input and saved B predictions, tokenizer/vocabulary.
Train, raw dataset archive, metadata/labels-16695.json and family6 are not mounted.

## Aggregate coverage indicators

| Cohort | N | Mean input tokens | At 256-token limit | UNK fraction |
|---|---:|---:|---:|---:|
| family2 | 41 | 256.000 | 41 | 0.000000 |
| other_development | 31 | 252.903 | 30 | 0.000000 |

## Family2 source-block sizes (including header)

| Source | Rows | Mean block tokens | Min | Max | UNK tokens |
|---|---:|---:|---:|---:|---:|
| alerts.json | 5 | 49.600 | 49 | 50 | 0 |
| audit.log | 41 | 135.585 | 48 | 254 | 0 |
| auth.log | 6 | 62.000 | 48 | 126 | 0 |
| syslog | 34 | 111.971 | 28 | 126 | 0 |
| daemon.log | 6 | 46.500 | 28 | 73 | 0 |
| kern.log | 2 | 48.000 | 48 | 48 | 0 |

Length256 indicates at-limit input, not independent proof of truncation. UNK
frequency and short blocks are descriptive, not proof of the model's error cause.
Decoded WordPiece text is normalized selected model input, not original raw logs
or complete attack-step evidence. Missing visible cues do not invalidate step labels.

## Private files, not committed or exported

- `/home/saiuser/EDRXDR-BERTv4-work/evidence/family2-input-review-679lrg_f/review-inputs-private.txt`: all41 cases, escaped terminal controls.
- `/home/saiuser/EDRXDR-BERTv4-work/evidence/family2-input-review-679lrg_f/analyst-review-template-private.json`: all cases unreviewed.
- `/home/saiuser/EDRXDR-BERTv4-work/evidence/family2-input-review-679lrg_f/input-review-summary.json`: aggregate metadata.

Read text only on VM. Never execute commands appearing inside untrusted log text.
Do not paste snippets/screenshots or review template into chat/Git. Independently
assess evidence coverage and weak-label scope; request original authorized train/dev
step evidence if needed. Do not rewrite labels based on model disagreement alone.
Do not approve all cases automatically. Reviewer identity/time/reasons must be
recorded separately. No semantic review or final-evaluation authorization completed.

Final specification remains DRAFT_NOT_APPROVED. No new model execution, training,
GPU, holdout, dataset edits, shared-state changes, deployment or deletion occurred.
