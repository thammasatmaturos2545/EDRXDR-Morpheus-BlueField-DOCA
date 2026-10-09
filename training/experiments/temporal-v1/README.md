# Temporal v1 Development Experiment

## Status

Development experiment only.

Not production-ready.
Not a fresh final test.
No shadow deployment or automated response was enabled.

## Objective

Evaluate whether the Wazuh severity proxy model generalizes forward in time
when trained only on earlier events from the original v2 training split.

The model predicts the experimental weak label:

- `high_severity`: Wazuh `rule.level >= 7`
- `low_severity`: Wazuh `rule.level < 7`

This is a Wazuh severity proxy, not an independent threat detector.

## Dataset

Only the original v2 training split was used.

Temporal boundary:

`2026-10-07T00:00:00Z`

Canonical time basis:

Wazuh UTC archive/event date.

### Train

- 3922 rows
- 2740 low severity
- 1182 high severity

### Development

- Dev-All: 1310 rows
- Dev-Clean: 1306 rows
- Dev-Seen: 1291 rows
- Dev-Unseen: 19 rows
- Exact-text overlap removed from Dev-Clean: 4 rows

Unseen rules:

- 19011
- 503
- 5901
- 5902
- 5904

Original validation, old-test quarantine, and reserve-new-rules were not used.

## Timezone verification

25 events appeared to cross the temporal boundary when using timestamps
embedded inside `full_log`.

Raw Wazuh verification showed:

- source-file date == Wazuh UTC date: 25/25
- full_log date == Asia/Bangkok date: 25/25

Therefore the original UTC partition was retained.

## Balanced Result

### Dev-All

- TP: 1188
- FP: 1
- TN: 105
- FN: 16
- Precision: 99.916%
- Recall: 98.671%
- F1: 99.290%
- FPR: 0.943%

### Seen Rules

- TP: 1188
- FP: 1
- TN: 102
- FN: 0
- Recall: 100%
- FPR: 0.971%

### Unseen Rules

- TP: 0
- FP: 0
- TN: 3
- FN: 16
- High-severity recall: 0%

All 16 unseen high-severity events were missed.

## Unweighted Ablation

### Seen Rules

- TP: 1188
- FP: 0
- TN: 103
- FN: 0
- Recall: 100%
- FPR: 0%

### Unseen Rules

- TP: 0
- FP: 0
- TN: 3
- FN: 16
- High-severity recall: 0%

Removing rule-balanced weighting did not fix unseen-rule generalization.

## Unseen-rule analysis

Rule 19011:

- 13 high-severity events
- 13/13 false negatives
- related training examples were primarily low-severity SCA/CIS events

Rules 5901, 5902 and 5904:

- high-severity user/group modification events
- corresponding lexical/event patterns were absent from early training data
- all were predicted low severity

Rule 503:

- 3 low-severity events
- 3/3 correctly classified

## Conclusion

The temporal experiment shows strong performance on rules represented in
training, but poor generalization to unseen high-severity rules.

Balanced and unweighted training both fail on the same 16 unseen high events.

This suggests the current text-only task primarily learns associations between
known Wazuh rule/event templates and Wazuh severity.

It should not be treated as an independent threat detector.

## Next Direction

Keep Wazuh `rule.level` as the authoritative Wazuh severity signal.

Use NVIDIA Morpheus for an independent signal such as:

- anomaly score
- behavioral risk score
- suspicious activity classification
- endpoint/network multi-signal correlation

Do not use `rule.level` as an input feature when training a model whose target
is derived from `rule.level`, because that would be direct label leakage.

## Holdouts

The following remain untouched by this experiment:

- original validation
- old-test quarantine
- reserve-new-rules (479 events)

Do not use these sets for model tuning.
