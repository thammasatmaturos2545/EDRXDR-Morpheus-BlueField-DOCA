# BlueField isolated review — 2026-10-12 (Asia/Bangkok)

## Scope and evidence provenance

This directory archives separate experimental source trees. It does not replace bluefield-agent/, normalizer/, service units or any build directory used by a service. No driver, interface, broker or production configuration was changed by these experiments.

The following VM results were supplied by the operator in this conversation, not independently rerun on Windows. Original VM logs and JSONL must be copied into evidence/ using the accompanying collection script; they are not fabricated or reconstructed here.

## Observed results

- Original publisher service referenced a missing ~/EDRXDR-Morpheus/build/bluefield-agent/bluefield_monitor and repeatedly restarted. No claim is made that this service has been repaired or stopped.
- Review monitor: 9 synthetic C tests passed, DOCA 3.2.3005 build passed, and bounded sampling produced 6 real records (two interfaces, three rounds). Both interfaces were down; carrier was null with Invalid argument; all six counters were readable zero values.
- Monitor evidence directory: /home/saiuser/edrxdr-bluefield-nullcheck.Bn44DZ.
- Offline normalizer: 14 tests passed on the VM and 6 real file records normalized. All carrier values stayed null; two initial rx_bytes deltas were null (first_sample), and four subsequent deltas were computed zero. No broker access occurred.
- Normalizer evidence directory: /home/saiuser/edrxdr-bluefield-normalize.udX6v2.
- The monitor run-check.sh packaged here adds TMPDIR under its output directory. The successful VM run used the previous script with TMPDIR explicitly set by the operator. C source and tests are unchanged; the updated wrapper itself has not been independently rerun on the VM.

Existing component README validation sections describe their original packaging-time status. This document records the later operator-supplied VM results without rewriting historical claims.

## Remaining work

No live Kafka, Morpheus, OpenSearch integration, traffic test, GPU parity or real outage recovery was performed in this experiment. The current live Normalizer still coerces null to zero; do not send this new schema to its topic. Before integration, define a separate topic/index and consumer group, preserve the nullable contract through downstream processing, and coordinate interface ownership with the shared VM/network team. Do not enable ports or deploy the test binary to the service path merely to populate the Dashboard.
