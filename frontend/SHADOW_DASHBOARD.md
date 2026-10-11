# Shadow Dashboard — review update 2026-10-11

/shadow reads stored results from /api/shadow/events. Refresh does not start inference or capture.
The supplied handoff reports VM/browser success with 32/32 documents, 13 severity candidates,
0 AE-scored, 1 novelty. This is historical evidence, not a new VM verification in this review.

The review strengthens validation: known AE states must agree with coverage/routing/novelty;
null Wazuh level remains unknown and comparisons remain null; integer rule IDs are supported;
model metadata must be scalar and the API projects only validated fields for each model kind.
The page shows both sides of rule/time conflicts, bounds fetch time, and discards aborted responses.
Wazuh severity remains separate from AI scores. A candidate is not an independently verified FP.

Limits retained: exact complete results only, at most 500 documents per index; partial shards,
timeouts, duplicate occurrences, inconsistent flags and invalid schemas are errors. No atomic
snapshot across indexes is claimed. No raw event/log fields are projected to the browser.

Local checks for this patch: 20 Shadow checks (synthetic fixtures, including rendered UI),
full regression 7 groups, TypeScript and ESLint. Original reports from the user's earlier
2026-10-09 source bundle were used to satisfy the regression report dependency; they are not
new evaluation results. No VM/GPU/broker check was performed by this review.
The new production build remains unverified if blocked by Windows sandbox access; see REVIEW_TEST_REPORT.json.

VM verification without starting services:

    node tests/shadow.cjs
    npm run typecheck
    npm run test:regression
    npm run lint

Only build the frontend if needed after review, stopping your own foreground frontend first;
building writes .next and uses CPU/RAM. Never stop shared backend services for frontend changes.
run_shadow_dashboard.sh remains unchanged: it discovers the replay container IP, checks both
Shadow counts, sets SHADOW_OPENSEARCH_URL and starts a foreground Next.js process only when invoked.
It does not set REPLAY_OPENSEARCH_URL or install a daemon. Do not run it merely to force data to appear.
No new worker execution is necessary to inspect a stored batch.

See ../shadow/REVIEW.md for evidence scope and ../verify_shadow_review.sh for saved CPU checks.
