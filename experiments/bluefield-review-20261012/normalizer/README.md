# Offline BlueField normalizer review

Run `bash run-check.sh` on the VM. Default input is the actual capture at ~/edrxdr-bluefield-nullcheck.Bn44DZ/monitor.jsonl; pass a different JSONL path as the first argument if needed. Output and a stdlib-only Python venv go into a new ~/edrxdr-bluefield-normalize.* directory. Input hashes before/after are compared. No package installation, driver changes, device access, Kafka, service changes, or edits to the production repo occur.

The implementation is separate from normalizer/normalizer.py. It accepts only the review monitor schema and emits a distinct offline_review schema, production_ready=false. It must not replace the live normalizer yet. Wazuh handling and production source-lock files are untouched. This is a contract experiment, not end-to-end integration or model parity validation.

## Delta contract

- Actual zero is retained. Missing/invalid reading must be null with a read_errors entry; contradictory records are rejected.
- First sample establishes a baseline; its delta is null, never the lifetime counter value.
- A failed counter reading clears that field's baseline; the next valid reading reestablishes it with null delta. Other valid fields can still produce deltas.
- A decreasing counter has null delta and counter_decreased status. The new value establishes the next baseline; no claim is made about reset versus wraparound.
- Interface change or gaps exceeding 10 seconds reestablish baselines. This is an explicit offline experiment policy, not a measured threshold.
- Duplicate/out-of-order timestamps reject the input without mutating the baseline. The CLI validates all records before creating any output and refuses to overwrite an existing output.
- State is isolated per Normalizer instance/capture scope and ibdev. One input file must belong to one host and continuous capture session; ibdev is not a stable physical device ID across reboot/hotplug. Restarting a capture requires a new scope/instance. Hardware replacement without a detectable mapping/counter/time change cannot be inferred.
- operstate down and unreadable carrier remain visible. Counter deltas represent observed host counters and do not establish healthy links or whole-DPU traffic. No rates or attack scores are invented.

## Validation

14 synthetic unit tests passed on Windows in a Python venv on 2026-10-12. Real VM file normalization is pending. Test cases include maximum uint64 preservation, no partial output on invalid input, no overwrite, mapping gaps and per-field recovery. Tests use synthetic data only; the run script subsequently reads the actual capture file. Limits: 8 MiB, 10000 records, 128 devices per instance.

Prior evidence supplied by the user: monitor C tests 9/9, real DOCA compile passed, six records from two down interfaces with carrier null and zero readable counters. These observations are not evidence of live traffic, Kafka delivery or GPU scoring.
