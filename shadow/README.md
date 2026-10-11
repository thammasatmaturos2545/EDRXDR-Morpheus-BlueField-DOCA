# Shadow Mode v1 — stored bounded pilot

Review update: 2026-10-11. This source patch has not been applied to the VM by the reviewer.
The original base is branch work/shadow-mode-v1, commit 12d6049741235ba4bb45d65c1e3f59d4e01ce5b3,
as recorded in the supplied evidence. No new Git commit/push is claimed.

## Recorded VM evidence

The supplied training/evidence/shadow-20261011/join-evidence.txt and
training/evidence/dashboard-20261011/reported-result.json record a completed, stopped batch:
32 severity + 32 behavioral documents, 32 matched occurrences/raw hashes, zero missing/conflicting pairs,
13 weak-label candidates (all reported as rule19008), AE-scored 0, semantic novelty 1.
The Dashboard observation is user-reported evidence, not a fresh API query by this review.
Earlier validator-import failure and pending-GPU statements are historical; that batch subsequently completed.

32/32 measures output/identity completeness, not model accuracy. 13/32 is a candidate proportion,
not a false-positive rate against independent attack truth. AE coverage is 0/32, so the batch
cannot establish AE detection quality. Novelty does not establish maliciousness; not-scored is not safe.
Do not tune the threshold or move old-test/reserve records into training based on this batch.

## Review changes

- compose.yml stores the four cache environment settings previously used successfully on the VM:
  HOME=/tmp, XDG_CACHE_HOME=/tmp/cache, CUPY_CACHE_DIR=/tmp/cupy-cache, CUDA_CACHE_PATH=/tmp/cuda-cache.
  This persists SETTINGS in source control. Cache contents remain ephemeral in the existing 1 GiB tmpfs.
- The indexer requires the expected index/document ID plus failed=0 and successful>=1 shard acknowledgement
  before committing input. Missing or malformed acknowledgement fails closed.
- test_recovery.py adds isolated fake-client crash/retry tests; no broker, model or GPU is used.
- PACKAGE_SHA256.json describes this package's bytes. source-lock.json is unchanged: frozen replay/training
  dependencies remain pinned; their absence from the supplied archive is not worked around.
- See REVIEW.md and REVIEW_TEST_REPORT.json for local test scope and remaining gaps.

## Runtime constraints retained

Manual bounded workers only; do not use compose up or enable a daemon to populate a dashboard.
SHADOW_RUN_ALLOWED=0 and SHADOW_GPU_ALLOWED=0 remain the defaults. GPU work needs a current reservation.
UID/GID 1001:1002, all capabilities dropped, no-new-privileges, read-only root/models/source mounts,
/tmp tmpfs, CPU/RAM/PID budgets, manual profiles and restart=no are unchanged.
Do not rerun ownership initialization, provision/reset topics, change offsets or restart shared services
as part of this review. Source pins and deployment identity checks remain mandatory.

Capture reads live wazuh-alerts under a dedicated group; publishes only to experimental shadow topics.
Severity and behavioral outputs use separate shadow indexes in replay OpenSearch. Replay and live brokers
share a cluster ID, so pinned advertised listeners and disjoint topic signatures are checked too.
These checks are routing guards, not ACLs. This is logical isolation on shared infrastructure.

Delivery is at-least-once: producer acknowledgement before input commit, then index acknowledgement before
index-consumer commit. Lost acknowledgements can produce duplicate deliveries. Stable occurrence/model/raw-hash
index IDs permit overwrite retries; the newly added recovery tests exercise the control flow with a stub validator.
They do not prove production validator equivalence or recovery from real Kafka/OpenSearch outages.

Original occurrence identity is UID + source cluster/topic/partition/offset and raw_sha256.
Captured/scored timestamps are not input event time; capture_to_score_ms includes human wait time.
Raw JSON remains in the private raw Shadow Kafka topic, not score indexes or audits. Topic retention is 24h/64 MiB
per partition from provisioning; deletion is asynchronous. Index retention and pagination remain future work.
Do not reset offsets to recover a retention gap; the worker deliberately fails and requires investigation.

## Safe checks on the existing checkout (CPU only)

    python3 -B shadow/test_shadow.py
    python3 -B shadow/test_recovery.py
    docker compose -f shadow/compose.yml config --quiet
    cd frontend
    node tests/shadow.cjs
    npm run typecheck
    npm run test:regression
    npm run lint

These commands do not start workers, train, score, or open daemons. They assume the existing checkout includes
the source-locked replay/training files and original reports. A source-lock mismatch must be reviewed, not repinned.
The helper verify_shadow_review.sh runs these checks and saves fresh logs in training/evidence/ using a unique directory.

## Remaining work

1. Obtain current VM Git status and run the CPU verification script after applying the reviewed patch.
2. Confirm the changed API/page against the existing stored batch; no capture or GPU run is needed for display.
3. Analyze rule19008 with authorized input/context and independent labels; aggregate evidence alone is insufficient.
4. Select an existing replay AE-scored case only after checking actual payload/provenance; no such payload is in this archive.
5. Replay-vs-Shadow same-input scoring parity remains NOT RUN. It requires pinned source/models, identical raw input,
   reviewed preprocessing/threshold and resource authorization. Offline parity of another run does not replace it.
6. Real isolated broker/index outage tests remain NOT RUN. Never inject failures into the shared/live services.
7. Do not call sustained operation complete: rebalance/shutdown, poison messages, retention, pagination,
   resource budgets and ownership still need design and evidence.
