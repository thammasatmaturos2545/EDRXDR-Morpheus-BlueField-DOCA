# BERT v4 final-evaluation specification — DRAFT, NOT APPROVED

Status: DRAFT_NOT_APPROVED. This document does not unlock final holdout,
change manifest approval flags, issue a GPU reservation, select a production
model, or authorize new training. Designed after development diagnostics.

## Proposed research candidate, not frozen selection

Experiment B saved best epoch2 is the candidate under review. A/B originals,
recovery and v3 must remain intact. Do not replace binary NEXUS Severity with
this eleven-tactic attack-step model. Current low F1, false positives, source
baseline similarity and order sensitivity prevent production approval.

## Fixed contract to approve before final access

- Original protocol hash: `c7c35882c15f60999970e26d119227129afd256362a8b7c26f079f68ff1b4492`.
- Fixed target order: collection, command-and-control, credential-access, defense-evasion, discovery, execution, initial-access, lateral-movement, persistence, privilege-escalation, reconnaissance.
- Task: weak attack-step multi-label tactics; not per-log attack ground truth.
- Proposed input: original canonical source order and original sampling/token
  policy. Reverse order is a sensitivity test, not a newly selected candidate.
- Maximum256 tokens, fixed threshold0.5, sigmoid on float32 logits. No per-label
  threshold tuning, removing difficult labels, changing exclusions or fallback.
- Proposed runtime reproduces historical GPU bf16 policy and pinned image;
  if a different runtime is selected, specify and validate it before final access.
- Primary selection criterion remains macro F1 across all11, with micro F1,
  exact match and per-tactic TP/FP/FN/TN/precision/recall/support/predicted-positive
  reported together. Undefined precision must be explicit, not silently perfect.
- Final family6 is protected. Protocol-reported eligible100 steps is metadata,
  not a fresh count/inspection. Final input provenance and protocol compliance
  must be approved without browsing final examples/labels for tuning.
- Training/development hashes stay fixed. Do not repair original data silently.
- Exact candidate artifacts to approve:
```json
{
  "model.safetensors": "89d2877e1be5b24bcc5b87ede62affc4d5f40c6ecc5f58485aad2b29c9a52034",
  "RUN_COMPLETE": "662f6df25509e72fdb418b0f88806a91acc202e883b8ced21837e52ce1b7ceec",
  "training_report.json": "e481ea72fca224b039cee08cff6885c8e389af8ca83a7c5f9672db20d4e608bd",
  "config.json": "355975cf0f485e174d0e56c5263f43b3250f6d9a40f4d3e9b6f8cdcce4ca874c",
  "tokenizer_config.json": "1e5724dbee358c6dec897072bc06af436cc15c88f46ff0457ca2b7ff7e89e123",
  "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
  "special_tokens_map.json": "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a",
  "tokenizer.json": "851ca67100d372ca3ae031a6abd168f53489eebfd7d89523f35c5c9b4d372c3c"
}
```

## Approval gates still pending

1. Human review of weak labels, possible train label hint and input provenance.
2. Accept/document the missing original builder and scope of the reconstructed
   serialized-block ablation; decide whether more development is required.
3. Explicitly approve candidate and a one-time research evaluation plan. There
   is no approved numeric production-acceptance threshold in this document.
4. Explicit data/evaluation authorization and a fresh GPU slot if required.
5. Immutable pre-run manifest of code/model/tokenizer/protocol, deadline,
   input allowlist, outputs, review ownership and failure/retry procedure.
6. Human freeze before opening final content. A failure must not trigger silent
   retries with changed settings or selection of a better final result.

If performance is poor, report it unchanged. Any later retraining/tuning needs
a new protocol/version and cannot reuse the final set as development. No
deployment approval follows automatically from a completed final run.

## Current reproducibility record

See `BERT-V4-DEV-DIAGNOSTICS-20261031.md`,
`BERT-V4-ORDER-ABLATION-20261031.md`, `BERT-V4-DEV-PAIRED-ANALYSIS-20261031.md`,
and `HANDOFF-BERT-V4-NEXT-20261031.md`. No final samples, labels, logs, datasets,
weights or private per-step predictions are copied into Git by this work.
