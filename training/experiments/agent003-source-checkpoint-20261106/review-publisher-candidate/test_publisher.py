import copy, json, sqlite3, unittest
import decision_review as review
import evidence_publisher as publisher
import catalog_lifecycle as lifecycle
import revision_reader as reader
from test_lifecycle import fixture

def raw(value):
    return json.dumps(value, sort_keys=True).encode()

def inputs():
    policy = {'schema_version': 'experimental-publication-policy-1', 'enabled': True,
        'profile_id': 'synthetic-test-only', 'producer_id': 'synthetic-fixture',
        'pipeline': 'dfp', 'endpoint_id': '003', 'source_mode': 'controlled-test',
        'producer_source_sha256': '1'*64, 'detector_artifact_sha256': '2'*64,
        'detector_id': 'synthetic-not-a-detector', 'detector_version': 'test-only',
        'feature_contract': 'synthetic-six-counts', 'identity_contract': 'synthetic-journal-reference-1',
        'endpoint_namespace': 'synthetic-not-physical-device', 'score_semantics': 'reconstruction-error',
        'window_seconds': 300, 'threshold': 10, 'comparison': 'gte'}
    observation = {'observation_ref': '3'*64, 'subject_ref': '4'*64,
        'window_start': '2026-11-05T01:00:00Z', 'window_end': '2026-11-05T01:05:00Z',
        'detected_at': '2026-11-05T01:05:01Z', 'score': 125.5, 'record_refs': ['5'*64]}
    evidence = {key: policy[key] for key in (
        'producer_id', 'producer_source_sha256', 'detector_artifact_sha256',
        'feature_contract', 'identity_contract', 'endpoint_namespace', 'endpoint_id', 'source_mode')}
    evidence.update(schema_version='redacted-observation-evidence-1', observations=[observation])
    bundle = {'schema_version': 'redacted-detector-batch-1',
        'producer_id': policy['producer_id'], 'producer_source_sha256': policy['producer_source_sha256'],
        'detector_artifact_sha256': policy['detector_artifact_sha256'], 'observations': []}
    return policy, evidence, bundle

class Tests(unittest.TestCase):
    def setUp(self):
        self.policy, self.evidence, self.bundle = inputs()
    def build(self, evidence=None):
        evidence = self.evidence if evidence is None else evidence
        artifact = raw(evidence); digest = publisher.sha(artifact)
        bundle = copy.deepcopy(self.bundle)
        bundle['observations'] = [{'observation_ref': item['observation_ref'],
                                  'evidence_sha256': digest}
                                 for item in evidence['observations']]
        return publisher.build_catalog(raw(bundle), publisher.sha(raw(bundle)),
            raw(self.policy), publisher.sha(raw(self.policy)), {digest: artifact})
    def test_native_loss_preserved_and_typed_reference(self):
        before = copy.deepcopy(self.evidence)
        result = self.build(); row = result['catalog']['items'][0]
        self.assertEqual(row['score'], 125.5)
        self.assertNotIn('event_uid', row['evidence_refs'][0])
        self.assertEqual(row['evidence_refs'][0]['identity_contract'], self.policy['identity_contract'])
        self.assertFalse(result['binding_receipt']['production_ready'])
        self.assertEqual(self.evidence, before)
    def test_disabled_policy_rejected(self):
        self.policy['enabled'] = False
        with self.assertRaises(ValueError): self.build()
    def test_wrong_external_policy_pin_rejected(self):
        with self.assertRaises(ValueError):
            publisher.build_catalog(b'{}', publisher.sha(b'{}'),
                raw(self.policy), 'f'*64, {})
    def test_wrong_artifact_bytes_rejected(self):
        with self.assertRaises(ValueError):
            publisher.build_catalog(raw(self.bundle), publisher.sha(raw(self.bundle)),
                raw(self.policy), publisher.sha(raw(self.policy)), {'f'*64: raw(self.evidence)})
    def test_foreign_endpoint_and_namespace_rejected(self):
        for key, value in [('endpoint_id','004'),('endpoint_namespace','foreign-namespace')]:
            evidence = copy.deepcopy(self.evidence); evidence[key] = value
            with self.assertRaises(ValueError):self.build(evidence)
    def test_model_producer_and_feature_bindings(self):
        for key in ('producer_source_sha256','detector_artifact_sha256','producer_id','feature_contract','identity_contract'):
            evidence = copy.deepcopy(self.evidence); evidence[key] = 'different'
            with self.assertRaises(ValueError):self.build(evidence)
    def test_raw_and_privilege_fields_rejected(self):
        for key in ('full_log','path','account','production_ready','automated_response_allowed'):
            self.evidence[key] = 'untrusted'
            with self.assertRaises(ValueError):self.build()
            del self.evidence[key]
    def test_nonfinite_boolean_negative_scores_rejected(self):
        for value in (True, -1, float('inf')):
            self.evidence['observations'][0]['score'] = value
            with self.assertRaises((ValueError,review.Rejected)):self.build()
    def test_fractional_rule_count_rejected(self):
        self.policy.update(pipeline='endpoint-file-behavior',score_semantics='rule-count')
        with self.assertRaises(ValueError):self.build()
    def test_classifier_semantics_not_implicitly_mapped(self):
        self.policy.update(pipeline='endpoint-file-behavior',score_semantics='classifier-score')
        with self.assertRaises(ValueError):self.build()
    def test_zero_and_threshold_boundary(self):
        self.policy['threshold'] = 0; self.evidence['observations'][0]['score'] = 0
        self.assertEqual(self.build()['catalog']['items'][0]['score'],0)
        self.policy['comparison'] = 'gt'
        self.assertEqual(self.build()['catalog']['items'],[])
    def test_invalid_window_and_detection_time(self):
        for key,value in [('window_end','2026-11-05T01:04:00Z'),('detected_at','2026-11-05T01:00:00Z')]:
            evidence=copy.deepcopy(self.evidence);evidence['observations'][0][key]=value
            with self.assertRaises(ValueError):self.build(evidence)
    def test_duplicate_observation_and_membership(self):
        self.evidence['observations'].append(copy.deepcopy(self.evidence['observations'][0]))
        with self.assertRaises(ValueError):self.build()
        self.evidence['observations'].pop()
        self.evidence['observations'][0]['record_refs']*=2
        with self.assertRaises(ValueError):self.build()
    def test_policy_change_changes_revision_without_alert_identity(self):
        first=self.build()['catalog']; self.policy['threshold']=20; second=self.build()['catalog']
        self.assertEqual(first['items'][0]['alert_id'],second['items'][0]['alert_id'])
        self.assertNotEqual(review.validate_catalog(first)['items'][0]['alert_revision'],
                            review.validate_catalog(second)['items'][0]['alert_revision'])
    def test_empty_unbound_batch_rejected(self):
        with self.assertRaises(ValueError):
            publisher.build_catalog(raw(self.bundle),publisher.sha(raw(self.bundle)),
                raw(self.policy),publisher.sha(raw(self.policy)),{})
    def test_missing_artifact_rejected(self):
        self.bundle['observations']=[{'observation_ref':'3'*64,'evidence_sha256':'f'*64}]
        with self.assertRaises(ValueError):
            publisher.build_catalog(raw(self.bundle),publisher.sha(raw(self.bundle)),
                raw(self.policy),publisher.sha(raw(self.policy)),{})
    def test_typed_v2_cannot_claim_legacy_event_uid(self):
        catalog=self.build()['catalog']
        catalog['items'][0]['evidence_refs']=[{'event_uid':'5'*64,'sha256':'6'*64}]
        with self.assertRaises(review.Rejected):review.validate_catalog(catalog)
    def test_legacy_v1_still_valid(self):
        review.validate_catalog(fixture())
    def test_built_catalog_lifecycle_and_reader_keep_decision_evidence(self):
        old=fixture();oldraw=raw(old);anchor=publisher.sha(oldraw)
        first=raw(self.build()['catalog'])
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        try:
            db.executescript(review.SCHEMA)
            db.executemany('INSERT INTO metadata VALUES (?,?)',
                [('schema_version','nexus-decision-store-v1'),('catalog_sha256',anchor)])
            db.commit()
            lifecycle.advance(db,oldraw,first,anchor,'2026-11-05T02:00:00Z')
            active,catalogs,pin=reader.view(db,oldraw,anchor)
            body={'request_id':'11111111-1111-4111-8111-111111111111',
                'alert_id':active['items'][0]['alert_id'],'alert_revision':active['items'][0]['alert_revision'],
                'expected_seq':0,'action':'investigating','reason':'Synthetic human intent'}
            db.execute('BEGIN IMMEDIATE')
            reader.decide(db,body,{'actor_ref':'synthetic-reviewer'},active,'2026-11-05T02:01:00Z')
            db.commit()
            self.policy['threshold']=20;second=raw(self.build()['catalog'])
            lifecycle.advance(db,first,second,pin,'2026-11-05T02:02:00Z')
            active,catalogs,pin=reader.view(db,oldraw,anchor)
            items=reader.display_items(db,active,catalogs)
            row=next(item for item in items if item['alert_id']==body['alert_id'])
            self.assertIn(body['alert_revision'],row['revision_evidence'])
            self.assertEqual(len(row['history']),1)
        finally:db.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
