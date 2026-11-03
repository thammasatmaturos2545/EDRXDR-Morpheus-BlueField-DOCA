# Project delivery tracker and metadata snapshot

Owner requested complete project delivery before handoff. DELIVERY-PLAN.md and
acceptance.json define 23 required acceptance gates and dependencies. They record
partial historical successes honestly; no final acceptance is asserted.

Run python3 -B collect_status.py on VM after verifying the archive SHA256.
It verifies package files, runs ten synthetic tests, reads Git/service/container
metadata, saved pilot receipts and fixed unauthenticated loopback HTTP status.
It does not open raw logs, datasets, model weights, secrets or config contents.
It never starts/retries logging, creates response actions, changes services or
modifies Git/index. It writes a new private aggregate report directory only.

The existing pilot's consumed marker and saved state are used to avoid duplicate
activation. A saved RESTORED receipt is not a fresh verification of effective
logging configuration. Missing receipt is not proof no logger exists. Failed
checks are UNAVAILABLE, not converted into success or evidence of an outage.

Unauthenticated HTTP checks are not an authenticated API/count/browser acceptance
test. No quality/live readiness passes are inferred from HTTP 200 or running
containers. acceptance.py validates supplied receipt structure/dependencies only;
it does not authenticate receipts. Human/source-bound evidence review is required.

Keep all staged/untracked WIP. Package remains isolated; no repo installer or
commit command is included. Agent004/Network scope still requires a decision;
no device/telemetry/response/GPU authorization is added by this tracker.
