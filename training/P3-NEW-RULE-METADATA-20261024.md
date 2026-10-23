# P3 unseen-rule metadata profile — 2026-10-24

Aggregate metadata only; no split assignments, template generation, scoring or training.
Source P3 archives contain mixed rules. Only the 11 explicit unseen rule IDs are profiled;
no original protected dataset files opened; no non-allowlisted text used as features.
Provenance and row/template overlap remain unverified. High is weak severity, not attack.

| Rule | High | Low | High UTC days | High source pairs | Missing full_log (all rows) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 202 | 3 | 0 | 3 | 1 | 0 |
| 203 | 2 | 0 | 2 | 1 | 0 |
| 204 | 2 | 0 | 2 | 1 | 0 |
| 2502 | 1 | 0 | 1 | 1 | 0 |
| 19004 | 1 | 0 | 1 | 1 | 1 |
| 19005 | 5 | 0 | 3 | 1 | 5 |
| 19014 | 2 | 0 | 1 | 1 | 2 |
| 60110 | 24 | 0 | 6 | 1 | 24 |
| 60602 | 3 | 0 | 2 | 1 | 3 |
| 60776 | 10 | 0 | 6 | 1 | 10 |
| 61110 | 2 | 0 | 2 | 1 | 2 |

Private report: `/mnt/nexus-copilot-mQTssj/p3-new-rule-profile-e_lzng32/result.json`
Report SHA256: `c35dc7e32c739458e4c7bb0042f58d1bd2e6db6547f74917e4584ff6be289d49`

Next: propose policy and prospective, authorized provenance collection. Counts alone do not
authorize training or change reserve policy. Existing train/validation/quarantine/reserve stay fixed.
No raw logs/identities exported, GPU/offset/model/threshold changes, staging or commit.
