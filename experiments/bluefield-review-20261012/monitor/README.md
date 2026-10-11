# Isolated BlueField monitor review

This is a separate test source tree, not an installer or production publisher.
It never writes into EDRXDR-Morpheus/build, controls a service, brings an interface up, changes drivers, or publishes to Kafka. Default sampling is three rounds at two-second intervals, with --samples restricted to 1..100. The helper adds a 15-second runtime guard. Use the existing C compiler, Meson, Ninja and DOCA packages. Python commands run in a fresh venv with no package installation.

Run `bash run-check.sh` on the VM after extracting to a NEW directory outside the live repository. It prints the evidence directory under ~/edrxdr-bluefield-nullcheck.*. Nine synthetic unit tests compile the actual C source with a fake DOCA adapter and a temporary sysfs tree, then the script compiles against the installed DOCA and reads real counters for three rounds. Synthetic tests do not establish hardware correctness. A successful bounded hardware run should exit zero; exit 124 is now an incomplete run, not a pass.

Changes: nullable failed readings with per-field error messages; interface operstate and carrier; no arbitrary interface selection when mapping is ambiguous; JSON escaping; strict unsigned counter parsing; bounded samples; DOCA list cleanup. Counter zero remains zero even if operstate is down. Unavailable carrier remains null, not false. If device name lookup fails the program logs the failure and exits nonzero after sampling. Zero discovered devices also fails.

Scope is Linux host-interface counters. DOCA discovers devices; this does not implement DOCA Flow, packet capture or DPU-wide traffic monitoring. It is not evidence that every discovered device is exclusively a BlueField port. Interface and counters are read sequentially, not as an atomic snapshot.

## Compatibility finding: do not feed into the current Normalizer

The bundled normalizer/normalizer.py uses safe_int(value, default=0) in normalize_bluefield. Missing and null counters become zero; it also computes deltas from those values and retains that baseline. Consequently this new nullable schema is NOT ready to be sent to bluefield-events. A separate change must preserve unknowns and define baseline resets, first samples, device identity and counter resets before any integration. Existing deployment/source-lock files are untouched by this package.

## Validation provenance

The prior ORIGINAL monitor compiled with DOCA 3.2.3005 on the VM and observed two interfaces, both DOWN with readable zero counters. Carrier reads failed with Invalid argument. That result is not validation of this changed source. This package must run its C tests and DOCA build on the VM: the Windows editing environment has no C compiler or DOCA SDK. Local checks cover Python syntax and package integrity only. No new GPU, driver, live broker, interface or service actions have been performed.

Original source SHA256 (from the VM):
- bluefield-agent/meson.build: 053f738ae5e4b1c3fbb4a93f962fd015c14e8d9848a203777da0a425d35f2510
- bluefield-agent/src/bluefield_monitor.c: f48d4ca2550a674dce408f44049a8447003cd57d937b38d6182df35e99bdb4dc
