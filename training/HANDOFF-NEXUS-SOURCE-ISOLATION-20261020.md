# Wazuh source isolation — 20 October 2026

Scope: project/service discovery, container identity verification, Wazuh GET route
and compose-based status checks. No sampling changes, UID/History reconciliation,
Dashboard WIP or runtime/config migration in this commit.

resolveWazuhSource requires explicit WAZUH_COMPOSE_PROJECT, discovers exactly one
container within that project/service and validates its full ID, labels and state.
The Wazuh route reads only that validated full ID after confirming running state;
it never uses a name or selects the first service-only discovery result. Identity
failure/stopped manager/read failure returns 503 with total=null, not zero or healthy.
Successful source metadata includes identity and checked_at. Status compose checks
use the same scoped resolver and return unknown on identity/discovery failure.

The API retains HEAD's tail -n 100 and existing event selection. Balanced sampling
and tail -c 4194304 remain separate working-tree changes. Existing WIP bytes are
preserved while this commit is prepared in an isolated index/tree.

Validation: 13 resolver scenarios (two projects/order, missing config, ambiguous or
missing source, inspect mismatch, stopped manager, Docker failure, malformed data);
route tests with synthetic source/alerts; frontend no-emit typecheck. These tests
are offline and do not call Docker or read another team's payload.

Runtime acceptance remains separate: verify project ownership, configure only the
isolated/approved runtime, confirm process cwd/build and test identity failures.
This source commit does not deploy or restart 3001/3006, change systemd/shared state,
drivers/network or use GPU. Existing service configuration must not be assumed
to carry WAZUH_COMPOSE_PROJECT merely because the source reads it.

UID source reader was separately patched/tested in WIP to reuse this resolver;
its dependency chain and live evidence adapter remain outside this commit.
BlueField/rshim must remain inactive/dead/disabled; automated response OFF.
