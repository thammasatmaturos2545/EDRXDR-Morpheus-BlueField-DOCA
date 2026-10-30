# BERT v4 preprocessing proposal — DRAFT_NOT_APPROVED

This proposal does not edit frozen v4 data, approve label changes, authorize
training/GPU/final holdout, or select a production model. Use alongside the
annotation/duplication, original-source, paired and order-sensitivity diagnostics.

## Proposed work before any dataset vNext implementation

1. Independently establish provenance of audit keys/technique-like annotations.
   Determine whether they are monitoring configuration, scenario instrumentation,
   or label-derived metadata. Do not label all matching values leakage by syntax.
2. Review repeated cross-source content. Alerts/auth may reflect the same event;
   timestamps/system boilerplate can also match. Distinct sources may supply
   essential corroboration. Define a provenance-preserving dedup policy before use.
3. Define sampling that preserves useful multi-record process/session context
   without conditioning on weak targets, step names, family/split or outcomes.
   Never use labels or model predictions to choose the supposedly relevant lines.
4. Do not simply increase token length: omitted snippets may expose annotation
   candidates. Masking/dedup/budget changes must be separate controlled variants.
5. If approved, create a separate immutable protocol/dataset version with builder
   source, exact source-member provenance, token spans, exclusions and manifests.
   Keep original v4, A/B/v3/recovery and current split assignments intact.
6. Unit-test feature invariance to labels/family/split identity, source isolation,
   annotation handling, duplicates, token budgets and deterministic reconstruction.
7. Specify matched-compute/seeds/model initialization and source-only controls
   before asking for new training authorization. Any GPU run needs a fresh slot.
8. Evaluate only development while designing; do not browse family6 or alter its
   frozen role. Final evaluation stays DRAFT_NOT_APPROVED until explicit freeze.

## Approval and reporting limits

No automatic sanitization or label correction is implemented here. A label-blind
parser may still be biased by engineering choices; disclose development reuse.
Any future masking must preserve original bytes separately, record removed-field
provenance privately, and avoid treating transformed text as original evidence.
No numerical production threshold or final-test permission is issued here.
The current NEXUS binary Severity model is separate from this eleven-tactic task.
