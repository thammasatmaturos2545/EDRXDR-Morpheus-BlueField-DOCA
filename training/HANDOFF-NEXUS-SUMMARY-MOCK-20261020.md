# SOC Copilot synthetic mock — 2026-10-20
Operator-reported VM checks:
- Mock tests: 12 groups PASS; frontend TypeScript and whitespace PASS.
- Resolver 13 scenarios, sampling, UID lookup 21 groups, endpoints, NEXUS PASS.
- Isolated HTTP candidate port 3011: missing auth 401; valid auth 200.
- Synthetic UID citation matched; score 0 preserved.
- provider=mock; production_ready=false; automated_response_allowed=false.
No real logs, external provider, GPU, production build or service restart.
No deployment to 3001/3006. Existing WIP retained.
Pending: live evidence authorization/source checks, partial-response safeguards,
real-provider evaluation, distributed rate limiting and deployment review.
