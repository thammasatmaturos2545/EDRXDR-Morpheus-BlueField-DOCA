# Temporal development experiment — v1

Status: COMPLETED DEVELOPMENT EXPERIMENT

Purpose:
Assess later Wazuh events using a temporal split of the original v2
training data. This experiment is development evidence only. It is not a
fresh final test, production-readiness evidence, or an independent attack
detector.

## Source

- Only the 5232 rows of the original v2 training split were used.
- Original validation was not used for temporal training.
- Old-test quarantine was not used.
- Reserve-new-rules set was not used.
- Original checkpoints were not overwritten.
- Base model started from bert-base-uncased.

## Verified temporal partition

Boundary:
2026-10-07T00:00:00Z

Time basis:
Wazuh UTC archive/event date.

Training:
- 3922 rows
- 2740 low_severity
- 1182 high_severity

Later development:
- 1310 rows
- 106 low_severity
- 1204 high_severity

Later seen-rule:
- 1291 rows

Later unseen-rule:
- 19 rows

Unseen rules:
- 19011
- 503
- 5901
- 5902
- 5904

Exact-text overlap:
- 4 later rows
- dev-clean excludes these four rows

Event identity overlap:
- 0

Rule/label conflicts:
- 0

## Timezone verification

25 boundary-crossing candidates were investigated.

For all 25:
- source-file date matched Wazuh UTC date
- full_log date matched Asia/Bangkok local date

No partition adjustment was required.

## Training variants

Two development variants were evaluated:

1. Rule-balanced loss
2. Unweighted loss

Both used:
- bert-base-uncased
- threshold 0.5
- fixed temporal training partition
- no later development rows for early stopping

## Development results

### Rule-balanced

dev-all:
- N = 1310
- TP = 1188
- FP = 1
- TN = 105
- FN = 16
- Recall = 0.9867109634551495
- FPR = 0.009433962264150943

dev-seen:
- TP = 1188
- FP = 1
- TN = 102
- FN = 0
- Recall = 1.0

dev-unseen:
- TP = 0
- FP = 0
- TN = 3
- FN = 16
- Recall = 0.0

### Unweighted

dev-all:
- TP = 1188
- FP = 0
- TN = 106
- FN = 16
- Recall = 0.9867109634551495
- FPR = 0.0

dev-seen:
- TP = 1188
- FP = 0
- TN = 103
- FN = 0
- Recall = 1.0

dev-unseen:
- TP = 0
- FP = 0
- TN = 3
- FN = 16
- Recall = 0.0

## Unseen-rule result

High-severity unseen rules were not detected:

- 19011: 13 FN
- 5901: 1 FN
- 5902: 1 FN
- 5904: 1 FN

Rule 503:
- 3 TN

The unseen-rule group contains only 19 rows and is exploratory evidence.

## Interpretation

The temporal experiment substantially improves behavior on later events from
rules represented in training, including the rule-2901 hard-negative issue.

However, it does not demonstrate reliable generalization to unseen
high-severity rules.

The temporal model must therefore not be treated as a production replacement
for the existing detector.

## Limitations

- Mostly one host.
- Strong time/class distribution shift.
- Very small unseen-rule support.
- No independent attack ground truth.
- Wazuh severity remains a teacher/proxy label.
- Seen-rule performance must not be interpreted as unseen-threat detection.
- This experiment does not establish production readiness.

## Safety / deployment status

- Production ready: NO
- Shadow deployment: NOT ENABLED
- Automated response: NOT ENABLED
- Reserve-new-rules set: PRESERVED
- Old-test quarantine: PRESERVED

## Next

1. Preserve this experiment and its reports as reproducible evidence.
2. Run broader multi-event replay across multiple behavioral cohorts.
3. Validate behavioral routing and not-scored states.
4. Perform repository and artifact hardening.
5. Design shadow-mode evaluation only after replay validation is complete.
