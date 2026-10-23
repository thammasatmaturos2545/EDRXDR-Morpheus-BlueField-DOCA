# P3 rule550 provenance linkage — 2026-10-24

Operator-run CPU metadata audit linked exactly one recorded FIM lab event to P3.
- Exact canonical UID matches: 1; agent/event ID, rule, timestamp, path and both file hashes agree.
- Lab evidence result hash: 6f94b1e28a65101c0d0c8452171ed259fe4b8c1ad9317a3c26e6a35e601b0566
- Private reproducible report: /mnt/nexus-copilot-mQTssj/p3-provenance-26ufeeo7/result.json
- Report SHA256: a9724e3ccadb137bf5a0b827e9cd3a2a113188346affd091d141de11b410bca0
- Verifier SHA256: 4a2d9df0c81ea5b2bff00bb94a4408fa1f6a24da2b8c88323065226a4d0322d9
- Cohort: 55 rule550 high rows; 1 linked to recorded lab evidence, 54 still unestablished.
- This does not independently authenticate original lab execution or prove linkage
  to the profile's marker-only bucket; do not extend verification to the cohort.
- Eligibility remains pending; protected membership and data-use authorization unchecked.
- Lab activity/high weak severity does not establish a malicious incident.

No scoring/training/GPU, threshold/model/split/dataset changes or offset consumption.
No holdout/reserve file access; only named P3 archive and recorded FIM evidence inspected.
No raw event content exported. No existing repository file changed; no staging/commit/deployment.

Next: identify protected manifest metadata and permitted provenance records before
constructing memberships or assigning any development split. Rule2901 stays out of train.
