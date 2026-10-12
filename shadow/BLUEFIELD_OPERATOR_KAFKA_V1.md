# Read-only Kafka adapter (step 5)

Pinned runtime: Python 3.12.11, confluent-kafka and librdkafka 2.6.1, existing
image sha256:66a654987f79ee7a929b8e24ea4e0f5eea8a02245131f0eeb97292beabcedc4e.
No dependency installs. The installer only executes fake-client offline tests.

The preflight shell wrapper checks BlueField inactive/dead/disabled and starts
one finite container on the existing replay network with no GPU, read-only source
mount, resource limits, no extra capabilities, and an inner plus outer deadline.
Invoke with bash shadow/run_bluefield_operator_preflight.sh only after installation.
Preflight reads metadata only, not records. It verifies cluster ID, exact advertised
endpoint and replay topic signature, rejecting live topic names.

The adapter also implements inspect --plan PATH --envelope PATH --evidence-id ID.
No host launcher for inspection or producer is included in this step. Inputs must
be supplied as read-only files for a later bounded integration. It emits metadata,
not raw bytes; success is a point-in-time observation, never replay approval.

## Client-specific correction to step 4 transport notes

Confluent Consumer requires group.id (the group_id=None note in step 4 does not
apply to this client). This adapter uses a fresh private random identity, manual
assign with exact offset, never subscribe, and disables auto commit, offset store
and topic creation. There are no commit, store_offsets or producer calls. close
cannot auto commit with enable.auto.commit=false. Old pipeline groups are not used.
Reference: https://docs.confluent.io/kafka-clients/python/current/overview.html

Topic metadata is requested without a named topic; missing source does not cause
creation. Fetch rejects a skipped/changed offset, null payload, hash mismatch and
retention loss via the verified step 4 core. Metadata checks are not cryptographic
broker authentication; isolation relies on the existing trusted Docker network.
The adapter does not retrieve or authenticate quarantine evidence from a sink yet.
An inspect result is not a durable review audit. Future replay must use the canonical
operator journal and revalidate both source and approval, then reserve intent.

No VM integration or broker-side absence-of-mutations verification is claimed by
unit tests. First run is metadata preflight only. The original historical source
topic was reported absent; no code reconstructs it or substitutes archived bytes.
