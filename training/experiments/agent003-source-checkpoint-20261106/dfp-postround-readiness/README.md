# Original observer post-round readiness review

No new observer/training/model/threshold/runtime operation. Original round only: pysjui5a, source deadline6November2026 about03:59:58Asia/Bangkok. If receipt stillOBSERVING and original unit active/transitioning, printWAIT and return without reading eventDB/model/key/rawjournal. A staleOBSERVINGreceipt with no running unit stops for review; do not start another round.

After original worker stops, bind final receipt to its aggregate-SHA256, verify original collector code bytes, read normalizedSQLite via mode=ro/query_only, check quick_check/counts/record/time references, capture a stable finalDB SHA256 and create a NEW private aggregate report directory outside the observer. No original files are modified, copied/reclassified or purged; no WALcheckpoint. No keys/raw journal/reviewer credentials/models read. Audit caps10000normalized records/4000polls/200MiB DB/20sec; stops rather than truncate.

Technical capture checks are separate from semantic/quality acceptance. TechnicalPASS is NOT baseline, source completeness, independent evaluation, training approval or threshold selection. Those gates remain not_assessed. First/last poll engineering guards derive from the configured30sec cadence/25sec query timeout/5sec clock guard; cadence alone does not prove source retention or end-to-end coverage. Do not invent zero-event windows or benign labels.

Latest authorized historical review matched110stored unsupported records by exact identity AND payload from295historical selected rows; all hadSSHtransport-notice-like formats. No subcause labels were retroactively written. Formatting does not prove benignness, attacks or missed-auth rate, and that review did not accept source exposure.

Run after source deadline and worker completion: python3 -B run.py
Running early is safe but only returnsWAIT; do not continuously poll or use this as an automatic service.10synthetic readiness tests are separate from actual post-round review. Existing model/quality evidence and WIP are preserved.
