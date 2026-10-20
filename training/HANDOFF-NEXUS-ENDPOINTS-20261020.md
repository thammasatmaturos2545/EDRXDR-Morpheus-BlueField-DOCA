# Observed endpoint inventory — 2026-10-20

## Scope
- Existing observed endpoint builder and snapshot integration with dedicated tests.
- Observations come from loaded Wazuh rows, not authoritative asset/health inventory.
- No fabricated health/risk; missing or invalid time must not become current time.
- UI translation assertion stays at committed HEAD wording; translation remains WIP.
- Sampling, Dashboard/history UI and other WIP are outside this proposal.

## Validation and limits
- Isolated endpoint, NEXUS, UID, Copilot evidence and AI reader regression plus
  TypeScript and staged whitespace must pass before preparation succeeds.
- Offline synthetic checks only; no fresh inventory completeness or runtime proof.
- Endpoint identifiers depend on existing source identity; deployment review must
  consider source scope, authorization, history retention and data freshness.
- No network reads, LLM, GPU, build, restart, deployment or commit by preparer.
- Existing working files and normal index are preserved; only this handoff is added.
