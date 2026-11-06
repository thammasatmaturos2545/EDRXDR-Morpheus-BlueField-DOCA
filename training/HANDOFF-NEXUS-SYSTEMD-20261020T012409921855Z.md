# NEXUS All Events / systemd handoff — 20 October 2026

## Verified checkpoint
Both 3001 and 3006 migrated to user systemd with explicit Node 20.20.2.
Each port passed manual restart and API checks. These are not crash/reboot tests.
Manager: /wazuh-wazuh.manager-1, Compose project wazuh. Other group's manager
luckyfive_wazuh-wazuh.manager-1 must never be selected as fallback.
Homepage, Wazuh and Snapshot HTTP 200. History missing/wrong auth 401, valid auth 200.
Known exact UID: 5062c6e96485f0415cdbeeb57e2e899f18950aa85d79983b5c5c39591e9e62ef.
Raw AI score 0.0005193048855289817; displayed 0.1/100; low_severity.
This is a retained inference result, not proof of a currently running GPU worker,
attack probability, or model quality. Automated response/write/production flags false.

## Runtime and failure evidence
Runtime: /home/saiuser/nexus-history-preview-20261020/nexus-build-candidate-20261020
Build ID: B4ugzj7XFWOd_hGFLdjpl
Node: /home/saiuser/.nvm/versions/node/v20.20.2/bin/node
Units: nexus-all-events-prod-3001.service and nexus-all-events-prod-3006.service.
Overrides: ~/.config/systemd/user/<unit>.d/20-node-runtime.conf.
Systemd default Node18 reproduced Snapshot HTTP503 while Node20 passed on 3025.
This isolates a runtime-dependent symptom; the internal fetch failure mechanism
and original assertion line remain unproven. Do not change shared /usr/bin/node.
Restart=on-failure, delay5s. Linger=no; units last observed disabled.
No guarantee after final logout or reboot. Coordinate persistence with VM owner.

## History and authentication
Database: /home/saiuser/nexus-history-preview-20261020/history.sqlite3; backup contains 32241 events (count changes).
Use SQLite backup API, not plain copy of an active database.
History sync timer was active. Authentication only covers History API, not all APIs.
Secret remains at /home/saiuser/nexus-history-preview-20261020/preview-access.secret. Never commit or transmit it.
Access loopback listeners through SSH tunnels. No new GPU reservation is recorded.

## Preserve and resume
Git checkpoint before this documentation: 82521f898e8ab25d2c4891b81bc211a9015ccd89. Preserve all WIP.
Deployed candidate is outside Git and differs from repo: reconcile files individually,
including observed endpoints and All Events; never copy an entire stale tree over WIP.
Do not reset/clean. Do not rerun old migration scripts against changed PIDs.
Do not delete candidate dependencies or original runtime backups.
Retain all earlier demo evidence including the launcher124 run unchanged.
Safe next steps: verify current units/listeners, review this evidence, arrange
persistence, reconcile deployment sources into Git, then address Dashboard wording,
sampling/count/time-series limitations and model evaluation separately.

## Recovery and backups
Archive: /home/saiuser/EDRXDR-Archive/nexus-systemd-20261020T012409921855Z
Git bundle covers committed history at the checkpoint, not current WIP or SQLite.
Repository tar preserves tracked and nonignored untracked files except secret paths.
Deployed-source tar excludes build/dependencies/secrets; recovery needs matching
dependencies and rebuild in a separate directory, not over a running .next tree.
SQLite and security evidence are sensitive; keep archive private.
Original rollback runtime lacks History. Prefer repairing explicit Node20 unit
or running the tested new candidate manually if systemd is unavailable.
Stop only a verified NEXUS unit/PID after checking port ownership. Never stop
shared Wazuh/Kafka/OpenSearch/BlueField stacks. Preserve working port during recovery.
Private rollback environments stay outside Git in migration directories.

## Remaining work
Persistence approval/configuration; browser verification after migration; Git
reconciliation and reviewed commit; off-VM backup/hash verification.
Evidence directory: training/evidence/nexus-systemd-20261020T012409921855Z
