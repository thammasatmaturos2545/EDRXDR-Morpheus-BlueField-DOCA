# NEXUS DFP Diagnostic acceptance — 2026-11-04

Status: PREVIEW_BROWSER_VERIFIED_NOT_PRODUCTION_DEPLOYED.
This is an authenticated viewer of frozen CPU diagnostics, not live detection,
model-quality acceptance, automatic response or BERT replacement.

## Verified implementation

- Source baseline e19de85c88dcbc8d1dfd16dcc86c68e196210c3d.
- New page #dfpdiagnostic; GET /api/nexus/v1/dfp-diagnostic, History Basic auth first.
- Disabled by default. Requires NEXUS_DFP_DIAGNOSTIC_ENABLED=1 and server-pinned
  NEXUS_DFP_DIAGNOSTIC_SHA256. Fixed regular/single-link/private/same-owner file,
  no-follow open, byte/metadata/hash/model/capture/schema/identity/row checks.
- Backend reads no model, raw capture, feature values, HMAC keys or OpenSearch.
  Browser cannot supply paths/evidence/queries. One in-flight read per process.
- All twelve stored scores remain unscaled reconstruction losses. Exact zero and
  above-one behavior were tested with synthetic data; actual capture has no zero.
- Unknown coverage, no threshold/quality acceptance, response off and BERT intact
  remain explicit. No event_uid/severity/probability correlation is fabricated.
- Native sidebar/panels/table, textContent rendering, no inherited DEMO badge;
  failed reload clears old facts and stale navigation responses are ignored in
  synthetic tests. Failure/auth/stale browser behaviors were not forced on the
  real preview; distinguish these tests from the real success-path checks below.

## Operator-confirmed VM evidence

- Sealed file: /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/dfp-diagnostic-bundle-a_9ys044/diagnostic.json
  SHA256 0c308abf281a18a60e22d9382b6c1553c5f4e2b3b19132dbf145635dff66975e.
- Published private file: /mnt/nexus-copilot-mQTssj/dfp-diagnostic-published-v1/diagnostic.json.
- Built frontend: /mnt/nexus-copilot-mQTssj/incoming/dfp-diagnostic-candidate-xavq0_0z/frontend.
- Webpack build passed with existing dependencies copied locally; no installation.
- Preview unit: nexus-dfp-diagnostic-preview-m_kaeke4.service, loopback 3013,
  RuntimeMaxSec=3600. Current running/expiry state must be checked again.
- Private API result: /mnt/nexus-copilot-mQTssj/incoming/dfp-diagnostic-candidate-xavq0_0z/preview-attempt-m_kaeke4/result.json.
- Unauthenticated DFP API 401; authenticated exact sealed twelve windows / 845
  records; query rejection; existing preview APIs /api/wazuh, /api/events,
  /api/nexus/v1/snapshot returned 200; Model Lab all/DFP/Ransomware 773/666/107.
- Original production 3006 service metadata/page unchanged by preview helper.
- First preview attempt stopped at a faulty cmdline-based Node identity guard.
  Corrected helper compares /proc/MainPID/exe with samefile; seven mocked tests
  passed and real API preview then succeeded. No Node upgrade/install occurred.

## Direct real-browser checks by receiving agent

Via owner-opened SSH tunnel, http://127.0.0.1:13013/nexus/index.html#dfpdiagnostic:

- Twelve rendered rows, record sum 845, two boundary windows, all twelve coverage
  unknown. Maximum visible score 5.430511951446533; no alert/attack label inferred.
- Reload button completed and retained exact rows/counts. Evidence disclosure
  expanded; expected model/capture hashes visibly matched.
- DFP badge DIAG; Model Lab badge LAB and 773 results; Ransomware filter 107.
- Overview and All Events headings/badges returned correctly to API; diagnostic
  table absent on those pages. Only aggregate DOM metadata read on event pages;
  no raw-event content exported.
- Full-page screenshot inspected and retained privately on the Windows workspace,
  not included in Git. Browser returned to DFP Diagnostic as the user deliverable.

## Limits and next actions

Code commit does not change production runtime/env or extend the one-hour preview.
Production still serves the prior AppShield release unless separately switched.
No new Kafka/OpenSearch writes, model calls, training/GPU or logging occurred in
UI validation. Model Lab old code/schema/data is unchanged.

Before production: prepare a release bound to the committed frontend source,
verify build/receipts/file permissions/flag pin and rollback, then obtain approval
for the exact runtime switch. Preserve the old release and all other drop-ins.
Preview expiry is normal and must not be called an outage; any new/extended
preview needs a bounded scope rather than silently extending authorization.

Continue model validation/source coverage and DFP live shadow pipeline separately.
The central delivery acceptance remains incomplete. Ransomware live mapping and
compatible telemetry, BERT role, response gates, operations/restore and teammate
handoff remain outstanding; Agent004/Network restrictions remain in force.
