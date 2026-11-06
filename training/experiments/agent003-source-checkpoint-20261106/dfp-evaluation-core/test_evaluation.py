from datetime import datetime,timezone,timedelta
import copy, hashlib, json, unittest
from evaluation import evaluate

def protocol():
    return {'schema_version':'dfp-evaluation-contract-draft-1','pipeline':'dfp','endpoint_id':'003',
        'feature_contract':'linux-journal-auth-observed-counts-engineering-0',
        'detector_artifact_sha256':'1'*64,'decision_policy_sha256':'2'*64,
        'window_seconds':300,'scope':'engineering_descriptive_only'}

def pin(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def case(n=0,**changes):
    start=datetime(2026,11,5,1,0,0,tzinfo=timezone.utc)+timedelta(minutes=5*n)
    end=start+timedelta(minutes=5)
    value={'case_ref':f'{n+1:064x}','entity_ref':'b'*64,'partition':'evaluation',
        'window_start':start.isoformat(),'window_end':end.isoformat(),
        'members':[f'{10000+n:064x}'],'label':'negative','label_evidence_sha256':'c'*64,
        'coverage':'accepted','scored':True,'alert':False,'detected_at':None}
    value.update(changes)
    if value['alert'] is True and 'detected_at' not in changes:
        value['detected_at']=(end+timedelta(seconds=5)).isoformat()
    return value

def run(cases):
    value=protocol()
    return evaluate(cases,value,pin(value))

class Tests(unittest.TestCase):
    def test_binary_counts_and_explicit_latency_origin(self):
        result=run([case(0,label='positive',alert=True),case(1,alert=True),
                    case(2),case(3,label='positive')])
        for scope in ('conditional_scored_case_metrics','end_to_end_eligible_case_metrics'):
            m=result[scope]
            self.assertEqual([m[k] for k in ('tp','fp','tn','fn')],[1,1,1,1])
            self.assertEqual(m['precision'],0.5);self.assertEqual(m['recall'],0.5)
        self.assertEqual(result['true_positive_window_end_to_alert_seconds']['maximum'],5)
        self.assertFalse(result['quality_acceptance'])
    def test_positive_unscored_not_hidden(self):
        result=run([case(0,label='positive',alert=True),case(1,label='positive',scored=False,alert=None)])
        self.assertEqual(result['conditional_scored_case_metrics']['recall'],1)
        self.assertEqual(result['end_to_end_eligible_case_metrics']['recall'],0.5)
        self.assertEqual(result['case_accounting']['positive_unscored_cases'],1)
    def test_unknown_reference_not_benign(self):
        result=run([case(label='unknown',label_evidence_sha256=None)])
        self.assertEqual(result['end_to_end_eligible_case_metrics']['n'],0)
        self.assertIsNone(result['end_to_end_eligible_case_metrics']['recall'])
        self.assertIsNone(result['labelled_negative_entity_hours'])
    def test_unknown_coverage_excluded_with_accounting(self):
        result=run([case(coverage='unknown'),case(1,coverage='incomplete')])
        self.assertEqual(result['case_accounting']['excluded_unknown_coverage'],1)
        self.assertEqual(result['case_accounting']['excluded_incomplete_coverage'],1)
        self.assertEqual(result['end_to_end_eligible_case_metrics']['n'],0)
    def test_only_labelled_negative_exposure_in_denominator(self):
        result=run([case(0,alert=True),case(1),case(2,label='unknown',label_evidence_sha256=None)])
        self.assertAlmostEqual(result['labelled_negative_entity_hours'],1/6)
        self.assertAlmostEqual(result['false_alerts_per_labelled_negative_entity_hour'],6)
    def test_fit_and_calibration_not_evaluation_metrics(self):
        result=run([case(0,partition='fit',alert=True),case(1,partition='calibration',alert=True),case(2)])
        self.assertEqual(result['end_to_end_eligible_case_metrics']['n'],1)
        self.assertEqual(result['end_to_end_eligible_case_metrics']['fp'],0)
    def test_shared_membership_across_splits_rejected(self):
        a=case(0,partition='fit');b=case(1,members=a['members'])
        with self.assertRaises(ValueError):run([a,b])
    def test_nonchronological_splits_rejected(self):
        with self.assertRaises(ValueError):run([case(0),case(1,partition='fit')])
    def test_overlapping_windows_rejected(self):
        a=case();b=case(1,window_start=a['window_start'],window_end=a['window_end'])
        with self.assertRaises(ValueError):run([a,b])
    def test_duplicate_case_rejected(self):
        with self.assertRaises(ValueError):run([case(),case()])
    def test_no_unscored_alert_fabrication(self):
        with self.assertRaises(ValueError):run([case(scored=False,alert=False)])
    def test_score_number_is_not_prediction(self):
        with self.assertRaises(ValueError):run([case(alert=0.8)])
    def test_unknown_raw_fields_rejected(self):
        for key in ('full_log','account','path','score'):
            with self.assertRaises(ValueError):run([case(**{key:'private'})])
    def test_external_protocol_binding(self):
        value=protocol()
        with self.assertRaises(ValueError):evaluate([],value,'f'*64)
    def test_reference_evidence_required(self):
        with self.assertRaises(ValueError):run([case(label_evidence_sha256=None)])
    def test_detection_time_cannot_precede_closed_window(self):
        with self.assertRaises(ValueError):run([case(alert=True,detected_at='2026-11-05T01:00:00Z')])
    def test_no_cross_account_model_pooling(self):
        with self.assertRaises(ValueError):run([case(),case(1,entity_ref='d'*64)])
    def test_no_mutation_or_private_reference_export(self):
        values=[case()];before=copy.deepcopy(values);result=run(values)
        self.assertEqual(values,before)
        self.assertNotIn('b'*64,json.dumps(result))
        self.assertFalse(result['coverage_claims_verified_by_this_function'])
    def test_no_empty_windows_or_metrics_invented(self):
        result=run([])
        self.assertEqual(result['case_count'],0)
        self.assertIsNone(result['conditional_scored_case_metrics']['precision'])
        self.assertIsNone(result['false_alerts_per_labelled_negative_entity_hour'])

if __name__=='__main__':
    unittest.main(verbosity=2)
