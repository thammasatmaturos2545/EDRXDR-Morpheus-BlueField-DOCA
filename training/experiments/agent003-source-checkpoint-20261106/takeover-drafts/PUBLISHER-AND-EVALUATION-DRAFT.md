# Publisher/evaluation preparation — draft, 5 November 2026

Operator snapshot 14:49:26 Asia/Bangkok: branch work/nexus-exact-ai-v1 HEAD2fd3a6c; staged193-line handoff and pre-existing untracked preserved. Dashboard active on127.0.0.1:3006 at release-human-review-no-llm-r2n1_jrx/frontend, HTTP200. This is operator evidence, not a fresh direct SSH inspection. Architecture v2 and handoff read. No source/runtime modifications performed by this draft.

Observer pysjui5a: OBSERVING, 1235 polls,217 preserved records,32 observed account buckets,2 candidate accounts. Kind counts46 PAM opens/46 closes/38 SSHsuccess/8 sudo;79 unsupported. Last poll2026-11-05T07:49:16.339022Z; complete/trainingeligible0; no coverage/normalbaseline acceptance. Leave original deadline unchanged. Read-only final review must distinguish successful polling from source exposure, account membership, time coverage, parser limitations and experimental activity. Do not use elapsed24h as an acceptance gate by itself.

Owner does not yet know exam classifier requirements. Do not silently choose rules as a substitute for required AI or call a count feature builder a ransomware classifier. Preserve both design options until requirements clarified; shared publisher and evaluation infrastructure can proceed independently.

## Candidate publisher constraints (must inspect committed implementation before coding integration)

1. Trusted boundary: publisher runs server-side, separately authorized from browser reviewer. Browser cannot supply actor, score, coverage acceptance, model approval or arbitrary paths. An accepted JSON shape or approved flag does not authenticate evidence.
2. Evidence binding: bind pipeline, feature contract/order, detector artifact/version, evaluation/policy version, source scope, Agent003 identity namespace and observed event-time interval to immutable privately stored evidence. Separate ingestion time from occurrence time; retain missingness and coverage limits. Expose redacted references only.
3. Current permitted modes: replay/controlled-test/shadow. No production-ready flag, automated response or replacement claim unless independently accepted. Diagnostic loss remains native reconstruction error; do not transform to probability, severity or verdict without a justified policy.
4. Stable alert identity: source/pipeline-specific deterministic identity with documented namespace. Revision must cover displayed evidence, facts, recommendation and limitations. Retry of identical content is idempotent; conflicting identity/revision is rejected. Changed content creates a new revision rather than rewriting old evidence.
5. Catalog lifecycle: v1 is a pinned batch (20alerts,100decisions/alert). Do not simply overwrite the pinned catalog, repin arbitrary data, or create a replacement DB. Design/test migration with old revisions readable and decisions bound to the exact reviewed revision. Separate active catalog pointer from immutable revision storage only if current reader/auth/hash contract supports a reviewed migration.
6. Transactions/concurrency: prevalidate all records and provenance before publication; all-or-nothing DB transaction; expected catalog generation/sequence; crash recovery cannot expose half a catalog. Publish failure must leave prior catalog/audit readable. Auth failures precede private reads/writes.
7. Review isolation: named reviewer registry is not shared preview login. Owner chooses reviewer identities/roles; provisioning happens through private local credential entry. Never put passwords/digests/private decisions in chat/Git. Agree-recommendation records human intent only; no execution endpoint.
8. Tests before any apply: schema/raw-field rejection; foreign endpoint/contract; unknown coverage; duplicate/conflicting publish; updated recommendation generates revision; old decisions remain readable; stale writes; concurrent publisher/reviewer; crash/rollback; bounds; auth; no external calls; source retirement regressions. Use synthetic fixtures first and no real catalog writes by default.

## Evaluation preparation, not permission to collect/train

Freeze separate DFP6-count and endpoint-file/process contracts; event-time windows/lateness/duplicates/identity/missingness/source exposure are prerequisites. Fit/calibration/independent evaluation chronological and disjoint by source membership; keep experimental activity marked; no holdoutfamily6. Don't relabel all owner-recognized account data benign.

Endpoint evaluation needs owner-selected protected path and normal workload; not selected yet. File bursts can be benign bulk copy/build/update; modifying files alone does not establish encryption/process attribution. Freeze threshold selection metric and false-alert budget before independent test. Measure counts of eligible cases, missed cases/false alerts, latency and resource/retry/rotation effects; report unknown denominators as unknown, not zero or accuracy100%.

DFP needs representative baseline, source retention/exposure review and per-account support, loss scaling/version binding and an independent evaluation protocol. Do not retrain, reload models for new scoring, calibrate threshold or consume final holdout under this draft.

Next concrete engineering task: inspect committed decision worker/catalog/auth/tests and ModelQuality reader. Prepare an isolated candidate implementing compatible publisher lifecycle with synthetic tests. No real users/catalog/DB, runtime changes, collector or model execution until concrete scope is authorized.

## Operator VM acceptance of offline lifecycle v2

Package SHA71029d5ca66a06004fc37b36d6fe2136147639bd0936af4329b2cd8a1951f942 verified. Committed worker exact SHA33b1519eebed3827b6a43849a7cc3a58bb636e8a608797121e48e0b78b852a4b bound; original chat export omitted final LF, repaired without weakening exact check. Operator reports12 lifecycle+17original tests all passed onVM, including real POSIX private/no-follow checks. No live catalog/users/DB/model/GPU/runtime/repo changed. NOT_DEPLOYED. Legacy reader pin migration and trusted evidence provenance remain required; never run offline advance against real DB. ModelQuality report file-presence results still not received.
