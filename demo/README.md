> Latest handoff: [HANDOFF-NEXT-20261014.md](../training/HANDOFF-NEXT-20261014.md). Code checkpoint 8f737f9; supervisor cfecdcf offline tests and updated demo UI recorded. Sections below retain historical scope and reservation dates; follow the latest handoff before running commands.

# Bounded Severity flow demo

Add-only package preserving the dirty cb514aa snapshot. No existing files are
replaced. Source-lock and model parity checks remain unchanged. No drivers,
training, BlueField publisher, response automation or behavioral inference.

The launcher uses the approved H100 UUID only during 2026-10-13 17:00-19:00 +07,
with deadline before 18:55. Do not extend dates without another reservation.

## Operation

First terminal: `bash demo/start-ui.sh` builds a separate frontend copy using
existing dependencies and starts port 3001. Existing port 3000/build are preserved.

Second terminal: `bash demo/run.sh` starts a foreground bounded worker for at most
10 minutes. Open `/demo?run=RUN_ID` on port 3001 using the printed run ID.

After worker_ready, use an explicitly authorized normal Wazuh endpoint event.
This package does not generate endpoint events or change Wazuh configuration.

The first run records source high offsets. Only subsequent source arrivals are
captured. New groups, raw/output topics and an index are scoped to the run.
Capture ACK precedes source commit; score ACK precedes raw commit; index ACK
precedes output commit. Duplicate delivery remains possible; deterministic index
IDs preserve occurrence identity. At most 100 captures per session. Resume with
`bash demo/run.sh RUN_ID` while reservation remains valid. Retention gaps fail.

Each nonempty batch of up to eight invokes the frozen Morpheus severity engine.
Initialization repeats, so label this near-real-time microbatch, not hard real time.
The synthetic GPU smoke passed in 6.30 seconds; full pipeline remains to be tested.

Evidence lives in `~/edrxdr-demo-runs/RUN_ID/`: run.json, audit.jsonl and console
logs with exit codes. UID, source coordinates and raw hash link each stage. Raw
bytes are stored in the isolated raw topic, not printed or returned by the API.
Topics retain data for 24 hours with a 64 MiB cap. No automatic resource deletion.

UI shows latest 20 of exact total for this run. API failures clear displayed data.
Polling is serialized and abortable, three seconds after each request completes.
Heartbeat older than 30 seconds is stale; heartbeat is not inference evidence.
Session counters may include retries. Lag is unknown before first committed offset.
Wazuh severity and AI score stay separate. Behavioral is not run by this worker.

Index time is explicitly request-start time, not persistence ACK. Audit stores ACK
time. Browser first-seen is session-local and depends on clock synchronization.
Capture-to-browser is not full endpoint-event latency; source event time is unknown
in this view. No AE score does not mean safe. production_ready remains false.

Consumers close and audit flushes before explicit process exit, avoiding the prior
third-party shutdown hang. Inner/outer timeout bound the run. Timeout 124 is not
success. An interrupted input remains uncommitted and must be inspected/resumed.

Stop only the exact named demo container; never stop the shared Compose stack.
Accept only after new occurrences match hash/coordinates across capture, inference,
index and auto-updating UI, repeated with multiple events. Offline tests do not
prove VM integration, restart or failure recovery. GPU starts are never automatic
during installation.
