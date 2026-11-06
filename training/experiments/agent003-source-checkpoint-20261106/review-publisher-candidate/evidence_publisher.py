"""Pure evidence/policy checked experimental catalog builder. No live publish CLI."""
from datetime import datetime
import hashlib, math
import decision_review as review

MAX_BYTES = 512 * 1024
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024

def need(ok, message):
    if not ok:
        raise ValueError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def exact(value, fields):
    need(type(value) is dict and set(value) == set(fields), 'Unknown/missing fields')

def reference(value):
    need(type(value) is str and review.HASH.fullmatch(value), 'Invalid digest reference')

def identifier(value):
    need(type(value) is str and review.IDENT.fullmatch(value), 'Invalid contract identifier')

def number(value):
    need(type(value) in (int, float) and math.isfinite(value) and value >= 0,
         'Invalid native score/threshold')

def parsed(raw, expected):
    reference(expected)
    need(type(raw) is bytes and len(raw) <= MAX_BYTES and sha(raw) == expected,
         'Pinned bytes mismatch')
    return review.parse_json(raw)

def moment(value):
    review.timestamp(value)
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def build_catalog(bundle_raw, bundle_sha, policy_raw, policy_sha, artifact_bytes):
    """Policy hash is a caller-owned external trust anchor, NEVER taken from bundle."""
    policy = parsed(policy_raw, policy_sha)
    exact(policy, ('schema_version', 'enabled', 'profile_id', 'producer_id', 'pipeline',
        'endpoint_id', 'source_mode', 'producer_source_sha256', 'detector_artifact_sha256',
        'detector_id', 'detector_version', 'feature_contract', 'identity_contract',
        'endpoint_namespace', 'score_semantics', 'window_seconds', 'threshold', 'comparison'))
    need(policy['schema_version'] == 'experimental-publication-policy-1'
         and policy['enabled'] is True, 'Publication policy disabled/unsupported')
    for key in ('profile_id', 'producer_id', 'detector_id', 'detector_version',
                'feature_contract', 'identity_contract', 'endpoint_namespace'):
        identifier(policy[key])
    for key in ('producer_source_sha256', 'detector_artifact_sha256'):
        reference(policy[key])
    need(policy['endpoint_id'] == '003' and policy['source_mode'] in
         ('shadow', 'replay', 'controlled-test'), 'Unsupported publication scope')
    need(policy['pipeline'] in ('dfp', 'endpoint-file-behavior'), 'Unknown pipeline')
    need(policy['score_semantics'] == (
        'reconstruction-error' if policy['pipeline'] == 'dfp' else 'rule-count'),
        'Classifier mapping/other semantics not supported by this candidate')
    number(policy['threshold'])
    need(type(policy['window_seconds']) is int and policy['window_seconds'] in (60, 300),
         'Window contract not frozen')
    need(policy['comparison'] in ('gt', 'gte'), 'Threshold comparison not frozen')
    bundle = parsed(bundle_raw, bundle_sha)
    exact(bundle, ('schema_version', 'producer_id', 'producer_source_sha256',
                  'detector_artifact_sha256', 'observations'))
    need(bundle['schema_version'] == 'redacted-detector-batch-1', 'Unknown batch schema')
    for key in ('producer_id', 'producer_source_sha256', 'detector_artifact_sha256'):
        need(bundle[key] == policy[key], 'Producer/artifact binding mismatch')
    need(type(bundle['observations']) is list and len(bundle['observations']) <= 20,
         'Batch observation bound')
    need(type(artifact_bytes) is dict and len(artifact_bytes) <= 20,
         'Artifact bundle bound')
    need(all(type(raw) is bytes and len(raw) <= MAX_BYTES for raw in artifact_bytes.values())
         and sum(len(raw) for raw in artifact_bytes.values()) <= MAX_ARTIFACT_BYTES,
         'Evidence byte bound')
    artifacts = {}
    for digest, raw in artifact_bytes.items():
        artifact = parsed(raw, digest)
        exact(artifact, ('schema_version', 'producer_id', 'producer_source_sha256',
            'detector_artifact_sha256', 'feature_contract', 'identity_contract',
            'endpoint_namespace', 'endpoint_id', 'source_mode', 'observations'))
        need(artifact['schema_version'] == 'redacted-observation-evidence-1',
             'Unknown evidence schema')
        for key in ('producer_id', 'producer_source_sha256', 'detector_artifact_sha256',
                    'feature_contract', 'identity_contract', 'endpoint_namespace',
                    'endpoint_id', 'source_mode'):
            need(artifact[key] == policy[key], 'Evidence provenance mismatch')
        need(type(artifact['observations']) is list and len(artifact['observations']) <= 20,
             'Evidence observation bound')
        index = {}
        for item in artifact['observations']:
            exact(item, ('observation_ref', 'subject_ref', 'window_start', 'window_end',
                         'detected_at', 'score', 'record_refs'))
            for key in ('observation_ref', 'subject_ref'):
                reference(item[key])
            need(item['observation_ref'] not in index, 'Duplicate evidence observation')
            start, end, detected = (moment(item[key]) for key in
                                    ('window_start', 'window_end', 'detected_at'))
            need(start < end <= detected, 'Invalid closed-window/detection times')
            need((end-start).total_seconds() == policy['window_seconds']
                 and start.microsecond == 0
                 and int(start.timestamp()) % policy['window_seconds'] == 0,
                 'Window contract mismatch')
            number(item['score'])
            if policy['score_semantics'] == 'rule-count':
                need(item['score'] <= 2**53-1 and item['score'] % 1 == 0,
                     'Rule count is not a safe integer')
            need(type(item['record_refs']) is list and 1 <= len(item['record_refs']) <= 8,
                 'Evidence membership bound')
            for record in item['record_refs']:
                reference(record)
            need(len(set(item['record_refs'])) == len(item['record_refs']),
                 'Duplicate evidence membership')
            index[item['observation_ref']] = item
        artifacts[digest] = index
    items, seen, used, used_pairs = [], set(), set(), set()
    for row in bundle['observations']:
        exact(row, ('observation_ref', 'evidence_sha256'))
        reference(row['observation_ref']); reference(row['evidence_sha256'])
        need(row['observation_ref'] not in seen, 'Duplicate batch observation')
        seen.add(row['observation_ref'])
        need(row['evidence_sha256'] in artifacts
             and row['observation_ref'] in artifacts[row['evidence_sha256']],
             'Missing evidence observation')
        used.add(row['evidence_sha256'])
        used_pairs.add((row['evidence_sha256'], row['observation_ref']))
        evidence = artifacts[row['evidence_sha256']][row['observation_ref']]
        score = evidence['score']
        exceeds = score > policy['threshold'] if policy['comparison'] == 'gt' else score >= policy['threshold']
        if not exceeds:
            continue
        identity = review.digest({'pipeline': policy['pipeline'],
            'endpoint_namespace': policy['endpoint_namespace'], 'endpoint_id': '003',
            'subject_ref': evidence['subject_ref'], 'window_start': evidence['window_start'],
            'window_end': evidence['window_end'], 'source_mode': policy['source_mode']})
        items.append({
            'alert_id': identity, 'endpoint_id': '003', 'pipeline': policy['pipeline'],
            'source_mode': policy['source_mode'], 'event_time': evidence['window_end'],
            'detected_at': evidence['detected_at'], 'detector_id': policy['detector_id'],
            'detector_version': policy['detector_version'], 'feature_contract': policy['feature_contract'],
            'coverage_status': 'unknown', 'validation_status': 'experimental',
            'score': score, 'score_semantics': policy['score_semantics'],
            'findings': [
                'Candidate met the externally pinned experimental policy.',
                'Native score ' + str(score) + ' met ' + policy['comparison']
                + ' threshold ' + str(policy['threshold']) + ' under profile '
                + policy['profile_id'] + '.'],
            'limitations': [
                'Independent detection quality and source coverage are not accepted.',
                'Configured producer/artifact hashes do not independently prove model execution or physical endpoint identity.',
                'Publication policy binding: ' + policy_sha,
                'This candidate does not execute containment or replace live BERT.'],
            'evidence_refs': [{'record_ref': value, 'identity_contract': policy['identity_contract'],
                               'sha256': row['evidence_sha256']} for value in evidence['record_refs']],
            'recommendation': {'action': 'investigate', 'reason':
                'Review the bound evidence and experimental policy; no automated action is authorized.'}})
    need(used == set(artifacts), 'Unreferenced evidence artifact')
    need(used_pairs == {(digest, identity) for digest, index in artifacts.items()
                        for identity in index}, 'Unreferenced evidence observation')
    items.sort(key=lambda item: item['alert_id'])
    times = [item['detected_at'] for index in artifacts.values() for item in index.values()]
    need(times, 'Empty batch has no evidence generation time')
    generated = max(times, key=moment)
    catalog = {'schema_version': 'nexus-human-review-v2', 'generated_at': generated,
               'automated_response_allowed': False, 'items': items}
    review.validate_catalog(catalog)
    return {'catalog': catalog, 'binding_receipt': {
        'bundle_sha256': bundle_sha, 'external_policy_sha256': policy_sha,
        'evidence_sha256': sorted(used), 'profile_id': policy['profile_id'],
        'input_observations': len(seen), 'candidate_alerts': len(items),
        'production_ready': False, 'detector_quality_accepted': False}}
