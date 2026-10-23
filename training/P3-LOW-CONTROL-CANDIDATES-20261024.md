# P3 low-control candidate review — 2026-10-24

Authorized read-only audit of existing P3 Agent003/004 metadata, deadline 04:00 ICT.
Rule550/2901 and all validation/quarantine/reserve rule IDs excluded from candidate extraction.
Matches use same manager-agent, UTC day and shared rule.groups on that day only.
These are coarse metadata candidates, not verified provenance or confirmed benign controls.
No text features/templates, dataset assignments, collection, GPU/training or offset changes.

| Positive rule | High rows | Coarse low-rule candidates |
| --- | ---: | --- |
| 202 | 3 | 205 |
| 203 | 2 | 205 |
| 204 | 2 | 205 |
| 2502 | 1 | 1010, 5402, 5503, 5710, 5715, 5760, 5762, 52002 |
| 19004 | 0 | None |
| 19005 | 5 | 19012, 19013, 19015 |
| 19014 | 2 | 19015 |
| 60110 | 24 | 60104, 60122, 60132, 60137, 60608, 60610, 60635, 60642, 60668, 60702, 60716, 60718, 60775, 60798, 60805, 60807, 60808, 60809, 61102, 61104, 61109, 61138, 67018, 67022, 67023, 67028 |
| 60602 | 3 | 60104, 60132, 60137, 60608, 60610, 60635, 60642, 60668, 60702, 60716, 60718, 60775, 61102, 61104, 61109, 61138, 67018, 67022, 67023, 67028 |
| 60776 | 10 | 60104, 60122, 60132, 60137, 60608, 60610, 60635, 60642, 60668, 60702, 60716, 60718, 60775, 60798, 60805, 60807, 60808, 60809, 61102, 61104, 61109, 61138, 67018, 67022, 67023, 67028 |
| 61110 | 2 | 60132, 60137, 60608, 60610, 60635, 60642, 60702, 60716, 60718, 60775, 61102, 61104, 61138, 67022, 67023, 67028 |

Private report: `/mnt/nexus-copilot-mQTssj/p3-low-control-review-uujc2u_x/result.json`
Report SHA256: `a9cca61fa1961304a4024dd1c3dfae4ea32252db40e703f7c393bbe453547365`

Broad categories/time coincidence are leads only. Scenario/source records and human review
are required before calling a row an appropriate control; all training eligibility stays pending.
No original protected data files opened. No staging, commit, service changes or live reads.
