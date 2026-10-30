# BERT v4 development diagnostics — 2026-10-31

Operator-reported runs; aggregate reports verified against their local manifests.
Original checkpoint, datasets and protocol remain unchanged.

| Method | Macro F1 | Micro F1 | Exact match |
|---|---:|---:|---:|
| BERT B CPU float32 | 0.1727149303 | 0.2557377049 | 3/72 |
| Global train prevalence | 0.0000000000 | 0.0000000000 | 0/72 |
| Source-set train prevalence | 0.1693788504 | 0.1982758621 | 5/72 |

## Findings and limits

- CPU aggregate F1/exact match agree with the historical GPU bf16 report;
  per-row predictions/probabilities have not been proved identical.
- BERT B: TP 39, FP 143, FN 84 across all tactics.
- Collection, credential-access and initial-access have no positive predictions.
- Execution has TP 1 / FP 45 on support 3.
- Source-only macro F1 is close to BERT B; this warrants shortcut investigation,
  but does not prove that BERT ignores content.
- Source baseline is an exploratory train-count method, not an exhaustive
  source-only model comparison. No development-label fitting was performed.
- Source-order ablation is pending: no dataset builder or verified source spans
  found in the searched repo training/scripts and bounded workspace inventory.
- Do not guess token boundaries or shuffle token IDs to claim this ablation.
- metadata/labels-16695.json was not opened; holdout family 6 remains protected.
- No new BERT training, GPU use, threshold changes or deployment.
- Next: recover builder/spans, freeze a separate ablation method, then evaluate
  development only. Do not open final holdout until candidate/decisions freeze.

## Evidence

- Report: `/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-devcpu-1h5xog23/dev-cpu-report.json`
- SHA256: `3bf12fba50b26ab0e05c8551772473a3b2af0e0654989da7b72af061802f5040`

- Report: `/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-source-baseline-tbc7_g1q/source-only-report.json`
- SHA256: `e70e05931eb4245a27d8bd72b3a31270f2fa98598b389de7190920477fa601b6`
