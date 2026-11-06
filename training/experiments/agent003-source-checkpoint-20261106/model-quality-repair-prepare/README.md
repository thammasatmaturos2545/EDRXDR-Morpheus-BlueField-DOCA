# Model Quality missing-path repair preparation

Operator verified both legacy report files using current committed TypeScript validators, threshold agreement, and exact SHA256 values bound in prepare.py. Runtime configured directory lacks both files; original repo contains them. This preparation copies only these verified legacy reports into a new user-private frozen directory under /mnt, proposes one appended EnvironmentFile, and records current NEXUS runtime metadata plus baseline503. It does not install a drop-in, reload/restart anything or change environment/Git. Existing report hashes must match or it stops.

An eventual approved apply must verify stale plan/runtime/drop-in hashes and ordering, preserve previous files, restart only NEXUS3006, confirm effective MODEL_QUALITY_REPORT_DIR, GET200 with exact report SHA identities and unchanged existing APIs, and roll back its own drop-in if any check fails. Existing EnvironmentFiles must not be reset. Do not remove cutover-plan-human-review or review-override.env.

The reports remain LEGACY DEVELOPMENT evidence, not the new DFP or endpoint detector's quality. Restoring availability is not a detector-quality acceptance or BERT replacement. No named users/catalog/DB are provisioned. No model/training/GPU/observer/logging/Kafka/OpenSearch operations.

Run preparation only: python3 -B prepare.py

V2: previous preparation stopped before copying reports or changing runtime because its proposed basename sorted before existing drop-ins. Select current greatest basename plus .model-quality-20261105.conf, retaining an explicit ordering check and no-overwrite guard. No changes to existing drop-ins.
