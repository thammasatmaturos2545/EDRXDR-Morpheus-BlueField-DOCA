> Latest handoff: [HANDOFF-NEXT-20261014.md](HANDOFF-NEXT-20261014.md). Code checkpoint 8f737f9; supervisor cfecdcf offline tests and updated demo UI recorded. Sections below retain historical scope and reservation dates; follow the latest handoff before running commands.

# Demo handoff checkpoint — 14 October 2026

## Confirmed result

Code checkpoint: 5701979 on work/bluefield-shadow-quarantine.
Run: d20261013t181858-e1bbae7e (14 October 01:18–01:28 Asia/Bangkok).
New Wazuh Kafka offsets 17230 and 17231 traversed the bounded Morpheus
Severity demo: captured/scored/indexed 2/2/2. UID, raw SHA256, source and
OpenSearch document ID agree between retained audit and retrieved API.
The API returned two documents, worker stopped and last reported lag 0/0/0.
All three consumer-close markers and process_exit_requested=0 were recorded.
Container exit=0, launcher exit=0, OOMKilled=false, runtime Error empty.
Original evidence: training/evidence/demo-detached-d20261013t181858-e1bbae7e/.
Original run directory: /home/saiuser/edrxdr-demo-runs/d20261013t181858-e1bbae7e/.
Current API verification: training/evidence/demo-close-20261014/.

## UI observation and timing limits

Operator-supplied screenshot, API time 14 October 01:59:21 Thai, shows the
same run, 2/2/2 counters, two rows, offsets 17230/17231, stopped/stale and
last reported lag 0/0/0. This is visual confirmation of retained results,
not proof of an active worker or a new live run. Screenshot remains in the
conversation; this updater does not claim to archive the image in Git.
Capture-to-score was 9458 ms and 2477 ms in the API. Capture-to-browser
2283103 ms and 2057878 ms includes opening the page long after processing;
do not present those values as pipeline latency. Index request start is
not OpenSearch acknowledgement. No claim of model accuracy follows from
two low_severity predictions. Behavioral processing is absent from this worker.

## Historical evidence remains valid

The earlier Windows-origin run d20261013t164314-c1b4d787 achieved 3/3/3,
with verified agent 004 file-event origin, but launcher exit was 124.
Keep that result unchanged. The new run verifies the detached supervisor
success path; it does not retroactively change the earlier exit result.
Old documents below their checkpoint notices describe historical states.

## Resume and remaining work

1. Check current Git branch, HEAD and status before changes; never reset/clean.
2. Review supervisor failure paths before broader use: launch timeout or
   malformed output may leave container identity unknown; signal interruption,
   Docker unavailability and failure to stop need explicit reconciliation.
   This successful run does not validate all shutdown failures or supervision
   for continuous production operation. Do not stop containers by broad prefix.
3. Rehearse a fresh event during a newly confirmed GPU reservation and capture
   UI updates while it runs, correlating the same UID/hash through each stage.
   Keep run-scoped topics/groups/index and automated response OFF.
4. Improve demo presentation and explain score/threshold, historical versus
   live state, latency origins and Severity-only scope. Preserve honest unknowns.
5. Operator authoritative replay integration, Behavioral/AE, live BlueField,
   model-quality evaluation and production hardening remain separate work.
6. Commit this documentation/evidence and create/verify a Git bundle. A bundle
   covers committed Git history, not Docker volumes, model volumes, ignored
   files or the external run directories. Copy the bundle off the VM as well.

## Operating constraints and access

The latest reported GPU authorization was 13 October 23:00 through 14 October
03:00 Thai; launcher cutoff was 02:55. This is historical authorization, not
permission for future runs. Check date/time and reservation before any GPU use.
BlueField remains inactive/dead/disabled. Do not change drivers/interfaces,
stop shared stacks, enable automated response or claim production readiness.
Use bash demo/start-ui.sh for frontend only; demo/run.sh starts GPU work.
Windows tunnel: ssh -N -L 127.0.0.1:3001:127.0.0.1:3001 saiuser@172.16.30.147
Open http://127.0.0.1:3001/demo?run=d20261013t181858-e1bbae7e with both the
frontend and tunnel sessions kept open. No new worker is needed to view history.

Earlier file organization remains under
/home/saiuser/EDRXDR-Archive/20261012T135349958660Z/ with manifest and restore
script. Seven backup/package/review/handoff items were moved, not deleted;
no disk space was reclaimed. Main repo, personal worktree and service paths
were retained. Do not restore the archive merely to resume development.
