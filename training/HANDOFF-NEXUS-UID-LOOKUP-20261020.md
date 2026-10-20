# Exact UID Lookup isolated proposal — 2026-10-20

## Scope
- Existing exact UID parser and canonical source verification, server transport,
  snapshot augmentation and fail-closed correlation states.
- Reuses committed compose-project source resolver; never selects another project.
- Preserves genuine zero scores and missing timestamps; no inferred AI match.
- Endpoint inventory, sampling, dashboard/history and Copilot adapters remain WIP.

## Validation
- Preparation requires isolated UID, source guard, source resolver and NEXUS tests
  plus full TypeScript and whitespace checks to pass before PREPARED is written.
- Tests are offline synthetic/mocked checks, not fresh VM source verification.
- Operator previously reported exact source and evidence/AI matches for eight UIDs;
  this does not establish semantic accuracy or incident independence.

## Limits
- Lookup coverage is captured and bounded by the latest AI window.
- No production-readiness claim, automated response, model inference or GPU use.
- Existing Filebeat credential reuse remains technical debt; dedicated read-only
  OpenSearch credentials and endpoint authorization need deployment review.
- No build, service restart, deployment, staging in normal index or commit here.
- Existing working files stay unchanged apart from this new handoff document.
