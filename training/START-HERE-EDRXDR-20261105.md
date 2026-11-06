# START HERE — EDRXDR–Morpheus–NEXUS
## Development Handoff — 2026-11-05

- Status: ACTIVE DEVELOPMENT ENTRY POINT
- Branch: work/nexus-exact-ai-v1
- Architecture commit: 8f25e448cb4fdffd1c2c6f3e3f3d7fcb49c2f5a0

---

## 1. Authoritative Architecture

The single authoritative target specification is:

[EDRXDR–DFP–RANSOMWARE–NEXUS v1](../docs/architecture/EDRXDR-DFP-RANSOMWARE-NEXUS-v1.md)

Do not create competing architecture definitions in other documents.

This START-HERE document is a navigation and execution handoff only.
If any historical document conflicts with Architecture v1, Architecture v1
takes precedence.

## 2. Active Detection Pipelines

1. DFP — behavioral anomaly detection using identity, authentication,
   VPN and relevant endpoint telemetry.
2. Ransomware Detection — process-level ransomware classification using
   compatible process and memory snapshot evidence aligned with
   NVIDIA DOCA AppShield.

Both pipeline outputs converge into the shared SIEM/XDR processing path
and are presented through NEXUS.

BERT v4 is superseded as an active target. Preserve its source code,
datasets, weights, checkpoints, evaluation evidence and historical reports.

## 3. Last Verified Development Status

Treat these as historical evidence, not claims of current production readiness.

### DFP

- CPU prototype implementation and diagnostic scoring were verified.
- The prototype used 12 historical windows for in-sample diagnostics.
- Independent evaluation windows: 0.
- The post-capture feature review found 12 rows, but no complete windows.
- Coverage and scoring authorization remain unresolved.
- Two bounded baseline collection attempts found no eligible fresh events.
- Identity reconciliation found zero training-eligible cohorts.
- Physical endpoint identity has not been independently verified.

### Ransomware Detection

- CPU sample/replay work exists.
- Live-compatible telemetry, verified process class mapping and
  independent evaluation remain implementation and acceptance gates.
- Do not treat sample/replay results as live detection performance.

### NEXUS

- Re-verify the deployed runtime, service state, APIs and UI before
  claiming current integration status.
- Existing diagnostic viewers must not be confused with live model inference.

## 4. Development Sequence

### Phase 0 — Architecture and contracts

- Read Architecture v1.
- Inventory current Morpheus and NEXUS integration points.
- Freeze versioned input/output contracts.
- Record dependencies and acceptance criteria.

### Phase 1 — DFP

- Resolve source exposure and physical identity.
- Establish representative baseline data.
- Define chronological independent evaluation.
- Verify feature extraction, window completeness and model semantics.
- Do not claim anomaly detection quality without independent evaluation.

### Phase 2 — Ransomware Detection

- Verify AppShield-compatible input and memory snapshot contracts.
- Establish process identity and class-label provenance.
- Validate ransomware and benign examples independently.
- Define false-positive, false-negative and resource acceptance criteria.

### Phase 3 — Morpheus Integration

- Implement separate DFP and Ransomware inference paths.
- Preserve independent feature contracts and model versions.
- Add deterministic offline tests.
- Normalize outputs into the shared SIEM/XDR event contract.

### Phase 4 — NEXUS Integration

- Integrate both pipeline outputs.
- Display source, timestamp, model version and detection evidence.
- Distinguish diagnostic, replay, shadow and live results.
- Do not infer production severity from uncalibrated scores.

### Phase 5 — Acceptance and Release

- Independent evaluation for both pipelines.
- Integration and regression tests.
- Shadow-mode validation.
- Resource and latency measurements.
- Explicit release approval before production cutover.

## 5. Safety and Preservation Rules

- Do not modify or delete BERT v4 historical artifacts.
- Do not overwrite frozen datasets or checkpoints.
- Do not fabricate missing events, benign labels or memory snapshots.
- Preserve incomplete windows and unknown coverage explicitly.
- Do not silently change legacy NEXUS event identity.
- Preserve all existing staged and untracked Git work.
- Do not use broad git add, reset or clean.
- Keep production services and runtime unchanged during development.
- Separate diagnostic evidence from model acceptance evidence.

## 6. Required Reading

1. This document.
2. [Architecture v1](../docs/architecture/EDRXDR-DFP-RANSOMWARE-NEXUS-v1.md).
3. [AI deployment handoff — historical runtime snapshot](START-HERE-AI-HANDOFF-20261104.md).
4. [DFP development handoff](START-HERE-DFP-HANDOFF-20261103.md).
5. [DFP/Ransomware lab transport notes](DFP-RANSOMWARE-LAB-TRANSPORT-20261103.md).

Historical documents remain evidence and must not silently override
the active architecture.

---

End of development handoff.
