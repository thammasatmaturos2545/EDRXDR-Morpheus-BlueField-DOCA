"""Evidence gate, not a source-of-truth authenticator or a deployment command."""
import re

HEX = re.compile(r'[0-9a-f]{64}\Z')


def evaluate(manifest):
    if type(manifest) is not dict or manifest.get('schema') != 'edrxdr-delivery-acceptance-1':
        raise ValueError('acceptance version required')
    items = manifest.get('items')
    if type(items) is not list or not items:
        raise ValueError('nonempty acceptance gates required')
    ids = [x.get('id') for x in items]
    if any(type(x) is not str for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('unique gate IDs required')
    by_id = {x['id']: x for x in items}
    pending = []
    for item in items:
        if type(item.get('required')) is not bool or item['required'] is not True:
            raise ValueError('baseline required gates cannot be silently waived')
        if item.get('status') not in ('pending', 'partial', 'blocked_scope', 'passed'):
            raise ValueError('unknown gate status')
        deps = item.get('depends_on')
        if type(deps) is not list or any(x not in by_id or x == item['id'] for x in deps):
            raise ValueError('invalid dependency')
        if item['status'] == 'passed':
            evidence = item.get('acceptance_receipt')
            if type(evidence) is not dict or evidence.get('reviewed') is not True:
                raise ValueError('reviewed receipt required')
            if not all(type(evidence.get(k)) is str and HEX.fullmatch(evidence[k]) for k in
                       ('receipt_sha256', 'source_manifest_sha256')):
                raise ValueError('version-bound receipt required')
            if item.get('independent_evaluation_required') is True and evidence.get('independent_evaluation') is not True:
                raise ValueError('in-sample evidence cannot pass model quality')
            if any(by_id[x]['status'] != 'passed' for x in deps):
                raise ValueError('dependency not accepted')
        else:
            pending.append(item['id'])
    visited, visiting = set(), set()
    def visit(key):
        if key in visiting: raise ValueError('dependency cycle')
        if key in visited: return
        visiting.add(key)
        for dep in by_id[key]['depends_on']: visit(dep)
        visiting.remove(key); visited.add(key)
    for key in by_id: visit(key)
    return {'delivery_accepted': not pending, 'gates': len(items), 'pending_gates': pending,
            'receipt_authenticity_verified': False}
