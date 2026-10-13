# Step 8 — read-only OpenSearch quarantine sink inspection

Base source: cb514aa, work/bluefield-shadow-quarantine. Adds a reader and tests only.
No existing binding, approval, store, source contract or sender is changed.

## Implemented

Host CLI uses a fixed replay OpenSearch container name, resolves its container ID,
requires image opensearchproject/opensearch:2.11.0 and exactly the replay network,
and checks BlueField inactive/dead/disabled before and after inspection. Each HTTP
request uses loopback within that container, GET only, no redirect/proxy/curlrc,
timeouts and a 64 KiB response limit. Container identity is rechecked at completion.
Preflight lists only quarantine namespace index names and UUIDs. It creates nothing.
Inspect requires an explicit run ID, document ID and expected index UUID. It rejects
aliases, unexpected index/document identity, invalid/extra envelope fields,
inconsistent source/document hash, unsafe flags, duplicate JSON keys and changed
index or document state observed during repeated reads. No arbitrary URL, wildcard,
search query, credentials, stdin evidence file or write operation is accepted.

Output is a strictly validated quarantine envelope and metadata, not raw poison
bytes. No plan, approval, canonical journal entry, reservation, Kafka read/write,
OpenSearch write, source commit, GPU job or service action occurs.

## Trust boundary / limitations

This establishes observed retrieval from the locally selected Docker deployment.
It is NOT cryptographic provenance, a sink signature, authentication of the actor
who originally wrote the document, or production security validation. Docker/host
administrators and existing index writers are trusted. The image tag is checked;
an immutable image digest is not newly asserted. Index UUID must be independently
reviewed by the operator; supplying it is not approval or replay authorization.
Repeated reads detect observed change; they do not lock the document, guarantee
snapshot isolation, or prevent a later change. Evidence must be reread inside any
future guarded workflow. Current canonical fixture binding is unchanged and still
rejects real quarantine labels. There is no automatic integration into ReviewBook.

The local Windows test run passed 123 synthetic operator tests: existing 109 plus
14 sink tests. It is not a VM OpenSearch integration run. Installer reruns the suite
on the VM before adding files and saves the result separately.

## First VM action: metadata-only preflight

    timeout --kill-after=3s 45s python3 -B shadow/bluefield_operator_sink.py preflight

If quarantine_indices is empty, that is a valid observation, not a failure of the
reader and not an end-to-end PASS. Prior isolated resources may have been cleaned
up. Do not invent UUIDs/IDs or recreate checkpoint resources to force a result.
If an index exists, locate the original document ID in its recorded quarantine
evidence and review the UUID before an exact inspect call. No wildcard enumeration
of document bodies is implemented.

Inspect CLI flags: --run-id, --evidence-id, --index-uuid. Supply actual verified
values only. Missing/deleted indices or documents fail closed. The command outputs
replay_authorized=false, transport_enabled=false, production_ready=false.

## Pending

VM preflight and exact-document read verification; if resources are gone, design
a separate newly scoped integration fixture with explicit provenance. Then review
how verified sink/source observations and canonical host approval bind into one
durable guarded workflow. Controlled publication remains disabled. Do not run the
step-6 producer fixture merely to test this reader; it creates source data but no
quarantine sink document.
