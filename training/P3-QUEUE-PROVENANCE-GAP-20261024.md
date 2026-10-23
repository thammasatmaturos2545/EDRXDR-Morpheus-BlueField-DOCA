# P3 queue provenance gap — 2026-10-24

Agent004: three temporal candidates with later reported normal-load events.
UTC intervals:
- 2026-10-17 02:02:12.014–02:03:00.383
- 2026-10-19 14:49:32.269–14:50:29.848
- 2026-10-21 11:18:57.725–11:19:29.321

Reviewed excerpts from COMPANY-SCOPE-20261014, NEXUS-SHARED-HOST-20261017
and SEVERITY-FLOW-20261013 do not establish activity attribution.
The referenced October13/14 tests do not establish provenance for these events.

origin_kind=unknown
provenance_status=unestablished
training_eligibility=pending_review

Needed: authorized Agent004 change/run records linked to these event identities
and intervals, with operator review. Time coincidence alone is insufficient.
No conclusion that the events were attacks, benign activity or lab-generated.
No GPU/training, collection, offset changes, staging or commit.
