# EDR/XDR Development Handoff

Generated from live Git/Docker/test state at `2026-10-10T02:51:54+07:00`.

## Resume point
```bash
cd ~/EDRXDR-Morpheus
```

- Branch: `work/shadow-mode-v1`
- Commit: `4dae1f7223838c07ac3882bd1cf786e0f20dd9dc`
- Milestone: Replay Severity + Behavioral integration works in development.
- Multi-event join: **8/8 UID joins verified**
- Production ready: **NO**
- Shadow mode: **NOT ENABLED**
- Automated response: **OFF**

## First checks
```bash
cd ~/EDRXDR-Morpheus
git status --short
git diff --check
docker compose -f replay/compose.yml ps
```

## Pipeline
```text
RAW Wazuh archive
  +-- Severity: replay-wazuh-alerts -> normalizer -> replay-morpheus-input -> inference -> replay-morpheus-output -> replay-severity-v1
  +-- Behavioral: replay-behavioral-input -> behavioral_replay.py -> replay-behavioral-output -> replay-behavioral-v1
Both indexes join by event_uid in /api/replay/events.
```

## Actual multi-event results
| Rule | Lvl | Severity | Score | Behavioral state | Routing | Support | AE | Novel | UID join |
|---:|---:|---|---:|---|---|---:|---:|---|---|
| 503 | 3 | `low_severity` | 0.000607 | `novel_cohort` | `novel_cohort` | 0 | N/A | True | PASS |
| 2901 | 3 | `high_severity` | 0.999374 | `insufficient_feature_diversity` | `local_model` | 240 | N/A | False | PASS |
| 5402 | 3 | `low_severity` | 0.000431 | `behavioral_anomaly` | `local_model` | 127 | 1.399x | False | PASS |
| 5403 | 4 | `low_severity` | 0.000553 | `behavioral_anomaly+semantic_novelty` | `local_model` | 127 | 70.407x | True | PASS |
| 5901 | 8 | `low_severity` | 0.017986 | `novel_cohort` | `novel_cohort` | 0 | N/A | True | PASS |
| 5902 | 8 | `low_severity` | 0.001927 | `novel_cohort` | `novel_cohort` | 0 | N/A | True | PASS |
| 5904 | 8 | `high_severity` | 0.996517 | `novel_cohort` | `novel_cohort` | 0 | N/A | True | PASS |
| 19011 | 9 | `high_severity` | 0.999144 | `limited_history` | `limited_history` | 4 | N/A | False | PASS |

## Critical Behavioral contract
```text
INPUT  = replay-behavioral-input
OUTPUT = replay-behavioral-output
GROUP  = replay-behavioral-raw-v1
```
Do not switch Behavioral v1.4 back to `replay-morpheus-input`; it does not preserve all raw Behavioral fields.

## Latest checks
| Check | Result |
|---|---|
| Python `py_compile` | **PASS** |
| `docker compose config` | **PASS** |
| Next.js production build | **PASS** |
| `git diff --check` | **PASS** |
| Secret-pattern scan | **PASS (targeted scan: no matches; broader repo scan reviewed placeholders/comments/test strings only)** |
| OpenSearch multi-event join | **8/8 UID joins verified** |

## Git files not yet committed
```text
(none)
```

Untracked:
```text
(none)
```

## Dataset/model Docker volumes
### `edrxdr-dataset`
- Docker mountpoint: `/docker/volumes/edrxdr-dataset/_data`
- Top-level entries:
  - `wazuh-context-v2-20261008T185539Z-1179365`
  - `wazuh-history-20261008T184838Z-1179365`
### `edrxdr-model-output`
- Docker mountpoint: `/docker/volumes/edrxdr-model-output/_data`
- Top-level entries:
  - `morpheus-behavioral-v1-4-dev`
  - `morpheus-offline-check-20261008T191811Z-1451355`
  - `morpheus-offline-check-20261008T192047Z-1463522`
  - `morpheus-offline-check-20261008T192400Z-1478287`
  - `morpheus-offline-check-20261008T194638Z-1580961`
  - `morpheus-offline-check-20261008T194814Z-1588236`
  - `morpheus-raw-offline-check-20261008T203523Z-1803526`
  - `wazuh-severity-context-v2-balanced-20261008T190719Z-1398863`
  - `wazuh-severity-context-v2-smoke-20261008T190209Z-1373668`
  - `wazuh-severity-context-v2-train-20261008T190301Z-1377612`
  - `wazuh-severity-nlp-v1-smoke-20261007T135726Z-1881188`
  - `wazuh-severity-nlp-v1-train-20261008T182138Z-1189522`
  - `wazuh-severity-temporal-v1-balanced-20261009`
  - `wazuh-severity-temporal-v1-unweighted-20261009`

Expected Behavioral bundle: `edrxdr-model-output:/morpheus-behavioral-v1-4-dev/`.

## Containers still running
```text
edrxdr-replay-opensearch-1	opensearchproject/opensearch:2.11.0	Up 21 hours	9200/tcp, 9300/tcp, 9600/tcp, 9650/tcp
edrxdr-replay-normalizer-1	edrxdr-morpheus-normalizer:latest	Up 21 hours
edrxdr-replay-kafka-1	apache/kafka:3.8.1	Up 21 hours	9092/tcp
edrxdr-normalizer	edrxdr-morpheus-normalizer	Up 2 days
edrxdr-wazuh-forwarder	wazuh-wazuh.forwarder	Up 2 days
wazuh-wazuh.dashboard-1	wazuh/wazuh-dashboard:4.14.7	Up 2 days	443/tcp, 0.0.0.0:8443->5601/tcp, [::]:8443->5601/tcp
wazuh-wazuh.indexer-1	wazuh/wazuh-indexer:4.14.7	Up 2 days	0.0.0.0:9201->9200/tcp, [::]:9201->9200/tcp
wazuh-wazuh.manager-1	wazuh/wazuh-manager:4.14.7	Up 2 days	0.0.0.0:1514-1515->1514-1515/tcp, [::]:1514-1515->1514-1515/tcp, 0.0.0.0:514->514/udp, [::]:514->514/udp, 0.0.0.0:55000->55000/tcp, [::]:55000->55000/tcp, 1516/tcp
edrxdr-indexer	edrxdr-morpheus-indexer	Up 2 days
edrxdr-kafka	apache/kafka:3.8.1	Up 2 days	0.0.0.0:9092->9092/tcp, [::]:9092->9092/tcp
edrxdr-opensearch	opensearchproject/opensearch:2.11.0	Up 2 days	9300/tcp, 9600/tcp, 0.0.0.0:9200->9200/tcp, [::]:9200->9200/tcp, 9650/tcp
```

If `replay-opensearch-proxy` appears, it is a temporary host-access helper, not a production service.

## Relevant files outside Git
- `/tmp/multireplay-selected.tsv` — selected multi-event source pointers
- `/tmp/multireplay-selected.log` — multi-event candidate selection
- `/tmp/multireplay-publish-remaining3.log` — multi-event publish log
- `/tmp/multireplay-existing-behavioral.log` — Behavioral replay for 2901/503
- `/tmp/multireplay-existing-behavioral-index.log` — Behavioral indexing for 2901/503
- `/tmp/multireplay-behavioral.log` — Behavioral replay for remaining multi-event set
- `/tmp/multireplay-behavioral-index.log` — Behavioral indexing log
- `/tmp/multireplay-severity.log` — Severity GPU inference log
- `/tmp/multireplay-severity-index.log` — Severity indexing log
- `/tmp/replay-api-joined-3101.json` — temporary API join response
- `/tmp/edrxdr-temporal-v1` — generated temporal-v1 dataset
- `/tmp/edrxdr-temporal-v1-run` — temporal-v1 run artifacts
- `/tmp/edrxdr-temporal-v1-unweighted` — unweighted temporal-v1 run artifacts
- `/tmp/edrxdr-anomaly-v1` — Behavioral feature dataset v1
- `/tmp/edrxdr-anomaly-v1-run` — anomaly v1 run artifacts
- `/tmp/edrxdr-anomaly-v1-1-run` — anomaly v1.1 run artifacts
- `/tmp/edrxdr-anomaly-v1-2-run` — anomaly v1.2 run artifacts
- `/tmp/edrxdr-anomaly-v1-3-run` — anomaly v1.3 run artifacts

## Reports
- `training/experiments/temporal-v1/dataset-manifest.json`
- `training/experiments/temporal-v1/balanced-report.json`
- `training/experiments/temporal-v1/unweighted-report.json`
- `training/experiments/temporal-v1/PLAN.md`
- `training/experiments/temporal-v1/README.md`
- `/tmp/multireplay-behavioral.log` (if present)
- `/tmp/multireplay-behavioral-index.log` (if present)
- `/tmp/multireplay-severity.log` (if present)
- `/tmp/multireplay-severity-index.log` (if present)
- `/tmp/replay-api-joined-3101.json` (if present)

## Known problems
- Rule 2901 remains a Severity false-positive example.
- Temporal-v1 seen-rule success is not unseen-threat generalization.
- Behavioral novelty is not equivalent to maliciousness.
- `insufficient_feature_diversity` and `limited_history` are intentional not-scored states.
- Automated response remains prohibited.

## Next actions
1. Multi-event UID join = `8/8`; persist evidence before Shadow Mode.
2. Review `git diff --check` and `git status --short`.
3. Review the three updated docs.
4. Stage/commit the Replay E2E + Behavioral v1.4 checkpoint when ready.
5. Keep automated response OFF.
6. Design Shadow Mode only after checkpoint/evidence are finalized.

## Safety boundary
Do not enable automated containment/response from the current development models. Finalize replay evidence and the Git checkpoint before Shadow Mode design.
