# BERT v4 source-block order diagnostics — 2026-10-31

Observed VM results; closure timestamp UTC: 2026-10-30T18:35:03.738166+00:00.
Base commit before these documentation changes: `a736f4da520fe80ee242e3012a0748bca4c3b7a7`.
Original checkpoints, datasets, protocol and all earlier/failed evidence retained.

| Method | Macro F1 | Micro F1 | Exact match |
|---|---:|---:|---:|
| B CPU original | 0.1727149303 | 0.2557377049 | 3/72 |
| B CPU reversed | 0.1206381206 | 0.1511111111 | 5/72 |
| B GPU bf16 original | 0.1727149303 | 0.2557377049 | 3/72 |
| B GPU bf16 reversed | 0.1206381206 | 0.1511111111 | 5/72 |
| Source-set prevalence | 0.1693788504 | 0.1982758621 | 5/72 |

## Controlled observations

- All 458 train and 72 dev rows passed source header/boundary reconstruction audit.
- Reversed blocks preserve source contents, per-source token budgets and labels.
- GPU control matches historical GPU aggregate and prior CPU counts.
- GPU reversed prediction vectors changed on 51/72 rows;
  96 label decisions changed.
- Maximum GPU probability change: 0.3613156378.
- Single-source inputs (14 rows) had zero probability change; multi-source cohort 58.
- CPU/GPU row-vector agreement: original 72/72;
  reverse 72/72. This does not prove probability identity.
- B original: TP39 / FP143 / FN84. Execution alone TP1 / FP45 on support3.
- Source-only prevalence is close in macro F1, but is a simple exploratory baseline.

## Interpretation and limits

The fixed checkpoint is sensitive to serialized source-block order on development.
This does not establish that source shortcuts are the sole cause, that content is
ignored, or that unseen-family generalization is acceptable. Higher reverse exact
match does not override lower macro/micro F1 or retrospectively change selection.
Original builder was not recovered; this tests audited serialized blocks, not
independent reproduction of original raw-log sampling/allocation. Weak step labels,
small supports, one seed and one dev split remain important limitations.

No new model training, threshold tuning, final holdout access or NEXUS deployment.
No final-evaluation/production approval is issued by this diagnostic.

## Failed GPU attempt retained

`expB-order-gpu-wmk7kogo` exited1 before model loading because environment-only
UUID validation disagreed with the observed Python runtime. Docker selectors
were correct. V2 verified actual NVML/CUDA device scope while accepting observed
NVIDIA_VISIBLE_DEVICES=void; host peer/UUID/time/memory guards remained in place.

## Per-tactic GPU effects

| Tactic | Original TP/FP/FN | Reverse TP/FP/FN | Original F1 | Reverse F1 |
|---|---|---|---:|---:|
| collection | 0/0/4 | 0/0/4 | 0.000000 | 0.000000 |
| command-and-control | 0/3/10 | 0/0/10 | 0.000000 | 0.000000 |
| credential-access | 0/0/8 | 0/0/8 | 0.000000 | 0.000000 |
| defense-evasion | 11/16/8 | 8/10/11 | 0.478261 | 0.432432 |
| discovery | 4/26/20 | 4/24/20 | 0.148148 | 0.153846 |
| execution | 1/45/2 | 2/49/1 | 0.040816 | 0.074074 |
| initial-access | 0/0/9 | 0/0/9 | 0.000000 | 0.000000 |
| lateral-movement | 0/1/3 | 0/0/3 | 0.000000 | 0.000000 |
| persistence | 10/15/10 | 0/0/20 | 0.444444 | 0.000000 |
| privilege-escalation | 11/33/9 | 1/0/19 | 0.343750 | 0.095238 |
| reconnaissance | 2/4/1 | 2/2/1 | 0.444444 | 0.571429 |

## Evidence references

- `/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-devcpu-1h5xog23/dev-cpu-report.json`
- SHA256 `3bf12fba50b26ab0e05c8551772473a3b2af0e0654989da7b72af061802f5040`

- `/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-source-baseline-tbc7_g1q/source-only-report.json`
- SHA256 `e70e05931eb4245a27d8bd72b3a31270f2fa98598b389de7190920477fa601b6`

- `/home/saiuser/EDRXDR-BERTv4-work/evidence/source-span-audit-4lyctebb/report.json`
- SHA256 `a332ab8b133239da45399643d5c608882a27a4819194d48cfe2d66709346edc1`

- `/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-order-ablation-a7449rse/source-order-report.json`
- SHA256 `2db98d4b5fe2d244306e90e11d0214c48f8bfceef2add0d3ccc8a4081a80d0c1`

- `/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-order-gpu-v2-b6cqbxn1/source-order-report.json`
- SHA256 `0c4f0f3b1c02d1685c56e01d87ea1df2e8e3a0192a0b4c06c3c87095f69a186e`
