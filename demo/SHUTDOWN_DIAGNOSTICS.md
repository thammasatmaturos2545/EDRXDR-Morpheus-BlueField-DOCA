> Latest handoff: [HANDOFF-NEXT-20261014.md](../training/HANDOFF-NEXT-20261014.md). Code checkpoint 8f737f9; supervisor cfecdcf offline tests and updated demo UI recorded. Sections below retain historical scope and reservation dates; follow the latest handoff before running commands.

> Latest checkpoint: see training/HANDOFF-DEMO-CLOSE-20261014.md. Run d20261013t181858-e1bbae7e: 2/2/2, container and launcher exit 0; API and operator UI observation verified. Earlier exit 124 remains historical.

# Shutdown diagnostics

Updates only demo/worker.py after matching the uploaded source SHA256.
Creates a byte-for-byte backup in the operator home. Runs four cleanup tests
and the existing demo/test_worker.py offline before writing the file.
No service, broker, GPU, reservation, Compose or launcher changes.

Historical worker_stopped means the processing loop and status write completed;
it does not prove process exit. Consumer cleanup follows that marker.
Both launcher and container timeouts can produce 124; existing logs cannot
uniquely identify which timeout or cleanup component caused the result.

New markers: shutdown_begin, consumer_close_begin/done/failed,
consumer_cleanup_complete, worker_main_returned, process_exit_requested.
After 20 seconds in cleanup, faulthandler prints Python thread stacks to stderr
and repeats every 20 seconds until process exit. It does not print raw events
or local variable values. Native-library stalls may still require other evidence.
Existing outer timeouts are unchanged. Failures stay nonzero.
Other consumers are closed if one close raises; a failure is never called success.

Local validation: 4 new cleanup tests and 11 existing worker tests passed.
Existing worker tests used the locally available shadow dependencies; the
installer reruns them against the actual VM repository before applying.
No actual GPU shutdown or new end-to-end run was tested.
Do not run demo/run.sh until a new GPU reservation is confirmed.
