# Historical source diagnostics — prepared; separate raw-source/key scope

Purpose: recover finite parser subcauses for exactly stored unsupported_message_format records. Saved normalized data omits source program and parser detail; no truthful reconstruction from projections alone is possible.

Explicit scope for owner review: ordinary saiuser helper; read original observation snapshot/receipt/plan; access only existing32byte experiment source-refs-private.key locally to reproduce original record/payload HMACs. No SSH/enrollment/API keys are read. Query existing journal using sudo -n only for journalctl, fixed original SSH/sudo/su/login filters, original observation start through last committed poll, maximum24h,1000source rows/8MiB/20sec. All selected source rows within that bounded interval are read in memory to match opaque IDs; only stored unsupported targets are classified after exact identity AND payload match. Stops on source binding/hash mismatch, changed payload, schema change, duplicate identity, cap or timeout. No follow/new collector/logging/retention change.

Output only aggregate parser/source-family/format-indicator counts, matched/missing totals and operational interval bounds. No raw text/accounts/IPs/cursors/HMACs/key values saved or printed. No files/records reclassified or overwritten, no model/training/GPU/new observation/threshold/runtime changes. Missing retention and notice-like formatting do not prove benignness, no attacks or baseline acceptance. Cannot establish source coverage or complete independent evaluation.

12 synthetic tests passed locally. Query is a single bounded historic read, not a passive collection loop. sudo is needed only to read journal if ordinary user lacks group access; helper itself must not run as root. Do not execute until owner accepts this specific source/key scope. No automatic retry or active observer patch.

Synthetic tests only: python3 -B -m unittest -v test_existing.py
Approved operation: python3 -B review_existing.py --approved-existing-source-review
