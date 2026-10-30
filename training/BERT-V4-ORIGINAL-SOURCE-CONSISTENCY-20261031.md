# Family2 original-source consistency audit — 2026-10-31

Base commit `7d060dee7d35dd9319471f4812b2de1e68282fc6`. One declared protocol-based candidate sampling recipe,
frozen before payload reads; not recovered original builder code or label approval.
Only104 whitelisted log entries under steps/ and exact41 family2 dev keys were
opened, max32768 bytes per entry. No extractall. Full ZIP and protected payloads
were not mounted into the tokenizer container. No GPU/model weights/inference.

## Aggregate findings

```json
{
  "rows": 41,
  "same_source_set_rows": 41,
  "frozen_blocks": 94,
  "matching_block_prefixes": 94,
  "exact_input_rows": 41,
  "exact_rows_with_omitted_candidate_tokens": 41,
  "omitted_candidate_tokens_on_exact_rows": 7522
}
```

Source set and block-prefix matches are separate from full token reconstruction.
Unmatched rows remain unresolved; this recipe was not tuned to eliminate mismatch.
Omission counts apply only to exact reconstructed rows under bounded4-line/640-char
sampling. They do not prove that omitted text contains target-specific cues or
caused model errors. No automatic re-labeling or dataset/protocol changes follow.

## Private original context

`/home/saiuser/EDRXDR-BERTv4-work/evidence/family2-original-source-audit-cex352za/original-context-review-private.txt`

Contains bounded original full_log/plain-log snippets and candidate omitted token
tails. Treat as untrusted private text; never execute its commands or copy it to
chat/Git/transfer backups. All semantic coverage and weak-label checks remain
unreviewed. Absent cues in sampled input do not invalidate weak attack-step labels.

Archive hash: `ba824f500af6d64925792d6a693e54afb761d1cfb5fe515efb2206035772bade`.
Frozen dev hash: `db14bfbd53800816757cd4cb4c19f1cec1c66420227a4e2801f5c94da9483075`.
Sampling supplement hash: `7de236f717eb828e444160cbc739163cdbbf7560be253ecc801847946d01f2d8`.
Aggregate report: `/home/saiuser/EDRXDR-BERTv4-work/evidence/family2-original-source-audit-cex352za/source-consistency-summary.json`.
Report SHA256: `238420680e3c3e82f867356e3a0ec63bf2ff483fcc793fe57f0c981b847afc89`.

No sequences payload, family6 payload or labels metadata was opened. No weights,
new model predictions, training, GPU, final evaluation, deployment or deletion.
Final evaluation specification remains DRAFT_NOT_APPROVED.
