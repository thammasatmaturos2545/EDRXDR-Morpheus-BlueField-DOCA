# NEXUS Copilot saved review — 20 October 2026

This commit adds an authenticated saved-result review page inside the existing
NEXUS shell at index.html#copilot. It is not a live Analyze endpoint or a production
deployment. Existing All Events/History/source-selection WIP is outside this commit.

GET /api/nexus/v1/copilot/review reuses requireHistoryAuth and is disabled unless
the isolated process sets NEXUS_COPILOT_REVIEW=saved-eight. It reads one fixed local
report, permits exactly eight verified UIDs and one pinned gpt-oss model revision,
checks citations/flags/original score fields, bounds reads and returns no-store.
No credentials or private report contents are committed. Missing report gives 503.

Report fixture path, deliberately local to this PoC:
/mnt/nexus-copilot-mQTssj/results/summary-eight-vone0xsh/result.json
The file is not tracked or bundled with source. Portability/configuration and
retention/RBAC must be designed before production; shared Basic auth is not tenant RBAC.

UI stays in the NEXUS sidebar/header/breadcrumb and uses native panel styles. Model
text uses textContent, exact citations and source disclosures. Repeated UID text is
shortened only for display; original text remains available. All generated summaries
are labeled unreviewed; saved data is explicitly not realtime. Standalone fallback
/nexus/copilot-review.html is retained. No inference/response/score mutation in UI/API.

Operator-reported evidence: real UID/source/AI matches 8/8; local gpt-oss summaries
generated 8/8; evidence/score/citation integrity 8/8. This is pipeline verification,
not semantic acceptance or model accuracy. Partial feedback for events 1–2 identifies
missing structured unknowns/checks; no claim of eight independent incidents.

Isolated checkpoint:
/mnt/nexus-copilot-mQTssj/checkpoint-copilot-vjs20j40
It retains overlapping source WIP and private evaluation, excludes secrets, weights,
dependencies, build, History DB and complete systemd/runtime restoration.

Tests: saved-review parser/API/browser DOM and integrated UI synthetic groups;
frontend typecheck with no emit/incremental cache and JS syntax check. Real browser
integration confirmed by operator on isolated port 3012; no deployment to 3001/3006.
LLM reservation was limited to 20 October 2026 at 12:00 Asia/Bangkok; do not reuse
that window for future inference. No driver/network/shared-stack changes authorized.
