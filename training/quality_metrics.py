"""Development metrics only; numerical gates are proposals, not deployment approval."""
import math
from collections import defaultdict


def metrics(pairs):
    tp = fp = tn = fn = 0
    for label, score in pairs:
        if label not in ('low_severity', 'high_severity') or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('Invalid label/score')
        high, predicted = label == 'high_severity', score >= .5
        tp += high and predicted
        fp += not high and predicted
        tn += not high and not predicted
        fn += high and not predicted
    def ratio(a, b):
        return a / b if b else None
    return dict(n=tp+fp+tn+fn, tp=tp, fp=fp, tn=tn, fn=fn,
                precision=ratio(tp, tp+fp), recall=ratio(tp, tp+fn),
                f1=ratio(2*tp, 2*tp+fp+fn), false_positive_rate=ratio(fp, fp+tn))


def evaluate(rows, comparisons):
    selected = [c for c in comparisons if c['source'] == 'validation']
    if sorted(c['audit_id'] for c in selected) != list(range(len(rows))):
        raise ValueError('Validation coverage/order contract failed')
    groups = defaultdict(list)
    pairs = []
    for item in selected:
        row = rows[item['audit_id']]
        pair = (row['weak_label'], item['morpheus_score'])
        pairs.append(pair)
        groups[row['rule_id']].append(pair)
    overall = metrics(pairs)
    per_rule = {rule: metrics(values) for rule, values in sorted(groups.items())}
    limits = dict(precision=.85, recall=.90, f1=.85, false_positive_rate=.10)
    gates = {key: overall[key] is not None and
             (overall[key] <= value if key == 'false_positive_rate' else overall[key] >= value)
             for key, value in limits.items()}
    gates['per_rule'] = all(
        (m['false_positive_rate'] is None or m['false_positive_rate'] <= .20) and
        (m['recall'] is None or m['recall'] >= .80) for m in per_rule.values() if m['n'] >= 30)
    return dict(scope='development_only', threshold=.5, overall=overall, per_rule=per_rule,
                proposed_limits=limits, proposed_gate_results=gates,
                development_numeric_gate_pass=all(gates.values()),
                shadow_authorized=False, production_ready=False,
                limitations=['Single-seed development set', 'Positive validation covers only one rule',
                             'Numerical pass cannot establish generalization or authorize deployment'])
