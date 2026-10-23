# Copilot live candidate handoff — 2026-10-24

Code baseline: 02347a8 on work/nexus-exact-ai-v1.
All results below are operator-reported VM outputs/browser observations.

## Verified
- Authenticated evidence API: missing auth 401, disabled 503,
  unauthorized exact UID 403.
- Authorized UID beginning 014b61edf23ba795: HTTP 200,
  complete=true, evidence=matched, AI=matched.
- All Events opens the server-verified evidence panel.
- Local gpt-oss-20b generated one new unreviewed draft through candidate 3013.
- Displayed Rule 533, Wazuh 7/15, existing AI score 99.9/100 and UID citation.
- Isolated synthetic tests and strict TypeScript passed.
- Banner state fix 02347a8 passed offline UI tests.

## Limits and pending work
- One live draft is not a model-quality evaluation or production approval.
- Analyst semantic review remains pending.
- Banner fix still needs an actual browser check.
- New drafts are not persisted; no review-decision persistence exists.
- Rate limits are per process; individual user RBAC is not implemented.
- No deployment to runtime 3006; candidate 3013 lifecycle must be checked.
- Check current Git/runtime state before continuing.

## GPU closure
- Inference authorized only until 2026-10-24 05:00 Asia/Bangkok.
- Operator stopped our LLM before the deadline.
- Subsequent GPU query showed only LuckyFive PID 189036, 808 MiB.
- Port 8011 had no listener. Do not stop LuckyFive.
- Fresh reservation and GPU guard required before any new inference.
- Verify temporary reservation file cleanup before another run.

## Shared VM constraints
Preserve WIP and unrelated untracked files. No reset/clean/overwrite,
shared driver/network changes, runtime .next build, shared stack restart,
offset reset/consumption, or training. Automated response remains OFF.
BlueField/rshim must remain inactive/dead/disabled.
Do not export secrets, raw logs, datasets or weights.
