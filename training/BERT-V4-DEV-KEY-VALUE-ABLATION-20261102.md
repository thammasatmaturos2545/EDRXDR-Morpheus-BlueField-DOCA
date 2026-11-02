# BERT v4 B: development key-value ablation results

Date: 2026-11-02 (Asia/Bangkok).
Status: COMPLETED_WITH_CONTROLS_PASSED.
Evidence basis: operator-provided VM console output, including verified closure.
This document was prepared locally; the remote private result files have not been
independently downloaded or inspected in this session.

## Result and interpretation

Replacing the fixed audit-key value intervals with pad ID 0 and attention 0 changed
no thresholded label decisions in any of the 13 eligible development rows.
Maximum absolute probability delta over their 143 row/class pairs was
0.002581775188446045. It is a probability-scale change, not a calibrated risk score
or relative percentage. Predictions and all reported F1/exact-match metrics stayed
unchanged. The identical no-op and the 59 unchanged-row controls passed exact
probability identity checks.

This intervention provides no observed decision-level evidence that these 13
selected values drive the saved B checkpoint's predictions at threshold 0.5.
It does not prove their complete irrelevance, absence of leakage, sound labels,
causal raw-log provenance, or acceptable unseen-family generalization.

## Fixed scope and runtime

- Saved B checkpoint: `runs/bert-v4-planB-expB-16719`, best epoch 2.
- Development only: 72 frozen rows, with 13 unique eligible rows and 59 controls.
- Intervention: 133 declared value-token positions. Preserve sequence positions,
  lengths, delimiters, other content, labels and source order; no token refill.
- Original, no-op and ablated arms used the same ordered batches of 8, right
  padding to 256, CPU float32 and eager BERT attention.
- Torch 2.4.0+cu124; Transformers 4.44.2; sigmoid(logits.float()) >= 0.5.
- Two CPU compute threads, one interop thread, deterministic algorithms, seed 42.
- Docker CPU limit 2, RAM limit 4 GiB, network disabled, read-only inputs/root,
  new private result directory, 1200-second limit with 20-second kill grace.
- No GPU, training, final holdout, NEXUS deployment or automated response action.

## Aggregate results

Original and ablated results are identical in every cell below. Exact match counts
whole 11-label vectors; TP/FP/FN are pooled over row/tactic decisions.
Macro F1 includes all eleven classes, with zero division mapped to zero.

| Cohort | Rows | Macro F1, both arms | Micro F1, both arms | Exact match, both arms | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full development | 72 | 0.17271493028480606 | 0.25573770491803277 | 3/72 | 39 | 143 | 84 |
| Eligible intervention | 13 | 0.06493506493506493 | 0.18867924528301888 | 0/13 | 5 | 28 | 15 |
| Unchanged controls | 59 | 0.18078749313247042 | 0.2698412698412698 | 3/59 | 34 | 115 | 69 |

- Eligible changed prediction vectors: 0/13.
- Eligible changed label decisions: 0/143 (13 rows x 11 tactics).
- Maximum absolute probability delta: 0.002581775188446045.
- No-op probability identity: true.
- Original/ablated probability identity on all 59 control rows: true.
- Historical original baseline: passed pooled counts, exact match, macro F1 and
  all eleven per-tactic confusion-count checks before interpreting ablation.
- The runner reverified checkpoint and original input hashes after inference.
- Original input bytes, in-memory variants and labels remained unchanged.

These pooled counts are multilabel tactic decisions. They are not a binary
malicious/benign confusion matrix and do not establish an attack false-positive rate.
The eligible/control cohort metric difference is not a randomized treatment effect.

## Execution and closure

Work root: `/home/saiuser/EDRXDR-BERTv4-work`.

Evidence directory:
`/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-key-value-cpu-cvf8bc5u`.

Container: `edrxdr-bert-keycpu-cvf8bc5u`.
Closure UTC: 2026-11-02T07:16:36.448567+00:00.
Closure path:
`/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-key-value-cpu-cvf8bc5u/closure-20261102T071636446725Z.json`.

- Local release tests: 54 synthetic tests passed, including 5 launcher tests.
- Packaged VM tests: 49 passed before model loading.
- Reported evaluation elapsed time: 37.5717994190054 seconds, excluding host
  preflight, tests and closure overhead.
- Container status: exited, exit code 0, OOMKilled false.
- Closure: passed true, reason VERIFIED. Result file hashes were checked by launcher.
- Container and failed-attempt evidence retention policy unchanged; this container
  was retained rather than removed.

Private outputs under the evidence directory include the frozen protocol/code,
interval mapping, labels, per-arm probabilities and paired deltas. Keep these on
authorized machines; do not copy them into Git or external GPT prompts. The
aggregate summary and this document contain no token values or raw log excerpts.

## Artifact identities

| Artifact | SHA256 |
|---|---|
| Release ZIP | 2d19d1bc48bae176d8ce7765ff671e2d0ea44eda340c0e3d10772ecb9e9fc840 |
| Result SHA256 manifest | 026da9391252af596eec23525ab7667214da9459ab270899125909f45bbf2324 |
| Existing eight-file checkpoint manifest | 3f062d2ddd3f4cd406af1ba8e24350eb6bd438d7321ed3605bf2d92548bbf083 |
| Model weights | 89d2877e1be5b24bcc5b87ede62affc4d5f40c6ecc5f58485aad2b29c9a52034 |
| Frozen private review | 4efc006abea582ecb7f4e6f37cc2e622aa191895d7430a2f807548e3f5f9ab6b |
| Frozen development | db14bfbd53800816757cd4cb4c19f1cec1c66420227a4e2801f5c94da9483075 |
| Saved tokenizer JSON | 851ca67100d372ca3ae031a6abd168f53489eebfd7d89523f35c5c9b4d372c3c |
| Original/no-op model inputs | 952e36974c2244e5fc0e7e26d236618913303f5c3ef112d44e8e3b98ac6a8483 |
| Ablated model inputs | 4780f4abfb2a6becd6cad51dba3f711a4210a20b26523e164bacf0b00ab217fc |

## Limits and relationship to previous diagnostics

The 13 cases came from exploratory development review, not a random or blinded
sample. Original private semantic decisions remain UNREVIEWED and raw-log
builder/member/occurrence provenance remains unresolved. Structural token alignment
and quoted-value boundaries were verified separately; they do not supply that
missing provenance. The intervention is artificial pad-plus-zero-attention and may
be out of distribution. Labels are weak attack-step tactic labels.

Earlier source-block reversal changed prediction vectors on 51/72 development
rows. That manipulation and this 13-row intervention have different scopes and
cannot be compared as causal effect sizes or treated as proof of a single shortcut.
Together they justify continuing the source/content/label investigation without
claiming that removing these values repairs the model.

B remains weak on development: micro F1 about 0.256 and exact match 3/72. This
diagnostic does not approve final family6 evaluation, model promotion, replacing
NEXUS binary Severity, or production automated response.

## Next work and handoff instructions

1. Preserve this completed run; do not rerun or change intervals to seek a preferred
   result. Keep original v4 data, A/B/v3/recovery, backups and all prior diagnostics.
2. Add this aggregate report to repository training documentation using a new file,
   then inspect actual Git status. Preserve untracked history/, uid_lookup/ and
   handoff/evidence work; no reset, clean or broad staging.
3. Review the existing original-source and weak-label diagnostics privately. Before
   further source/content ablations or preprocessing changes, specify a separate
   narrow hypothesis and preserve source-member/occurrence provenance. Do not
   select rows, snippets or masks using targets or predictions.
4. Recover the raw-data builder/selection provenance before claiming reproducible
   raw-log preprocessing. Do not silently sanitize or overwrite frozen v4 files.
5. Any dataset vNext or new training remains a separate proposed experiment. Freeze
   changes, baselines and evaluation criteria first; future GPU work needs a fresh
   booking. Do not automatically increase epochs, weights or token budgets.
6. Final holdout family6 and metadata/labels-16695.json remain protected. Freeze the
   candidate and final-evaluation procedure before considering that one-time gate.
7. Keep the eleven-tactic BERT v4 task separate from NEXUS binary Severity and LLM
   summaries. Live inference coverage, operational recovery, model quality and
   response authorization remain independent requirements.

No new training, final evaluation, deployment, cleanup or shared-service changes
are implied by receipt of this report.
