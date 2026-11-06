# DFP / Ransomware Lab transport — 2026-11-03

Evidence: operator-reported command outputs; not independently SSH-verified.

## Results

- Offline import PASS: 667 observations (DFP 666, Ransomware CPU summary 1).
- Batch SHA256:
  c72e369a699e48344c1f884bd618ac1e5f898bf23e8d318b6f837117a69fe0f4
- First pass: OpenSearch 667 documents; exact IDs matched the batch.
- First pass: Kafka end/committed 667; lag 0.
- One duplicate publication increased Kafka end to 1334.
- Retry processing was interrupted at committed offset 1074, leaving lag 260.
- Bounded resume processed the remaining 260 without republishing or resetting offsets.
- Final: Kafka end/committed 1334, lag 0; OpenSearch count 667; failed shards 0.
- Post-retry read-only validation PASS: exact IDs 667/667.
- Stored document contents matched candidate projections 667/667.
- Candidate payload hashes and original batch SHA256 were rechecked.
- Retry did not increase the document count; Kafka end/committed 1334, lag 0.
- Count stability supports idempotent document IDs; this is not exactly-once delivery.

## Scope

- Project: edrxdr-morpheus; network: edrxdr-net.
- Topic: edrxdr-lab-ai-observations-v1 (1 partition, 1 replica, retention 7 days).
- Index: edrxdr-ai-lab-v1 (1 shard, 0 replicas).
- Consumer group: edrxdr-lab-ai-lab-transport-YCoTV3ug.
- Lab profile: multi-pipeline-lab-v1.
- Explicit writes were authorized only for the isolated Lab integration.
- No BERT replacement, NEXUS deployment, training or GPU execution in this task.
- Sample results do not establish detection quality or production readiness.
- Ransomware output class mapping and Host CUDA error 999 remain unresolved.

## Private evidence locations

Under /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/integration-package-73C9gztG/:
- offline-import-VBMrTLYP/lab-observations.ndjson
- lab-transport-YCoTV3ug/transport-private.log
- lab-retry-sAIUyYUU/retry-private.log
- lab-resume-CBqH7H9d/resume-private.log

Keep private logs/data out of Git and chat.
Next: read-only post-retry ID/content validation, then review NEXUS integration
separately before changing any runtime or datasource.
