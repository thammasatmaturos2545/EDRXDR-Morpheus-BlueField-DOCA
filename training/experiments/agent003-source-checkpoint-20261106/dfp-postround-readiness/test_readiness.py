import copy, json, unittest
from readiness import evaluate

def fixture():
    receipt={'status':'OBSERVATION_FINISHED_NOT_QUALITY_ACCEPTANCE','failure_type':None,
        'observation_started_utc':'2026-11-05T01:00:00+00:00','maximum_seconds':60,
        'seconds_observed':60,'records_preserved':3,'polls_committed':3,
        'candidate_event_kind_counts':{'ssh_auth_success':2},
        'unscored_reason_counts':{'unsupported_message_format':1},
        'observed_account_time_buckets':1,'candidate_account_count':1,
        'source_coverage_accepted':False,'baseline_accepted':False,'training_performed':False,
        'gpu_used':False,'automated_response_allowed':False,'model_invocations':0}
    projection={'snapshot_records':3,'candidate_records':2,'unscored_records':1,
        'candidate_event_kind_counts':{'ssh_auth_success':2},
        'unscored_reason_counts':{'unsupported_message_format':1},
        'record_times_inside_approved_interval':True}
    polls=[{'observed_at_utc':f'2026-11-05T01:00:{n:02}+00:00',
            'elapsed_monotonic_seconds':n,'returned_rows':3,
            'free_disk_bytes':20*1024**3} for n in (0,30,59)]
    unit={'LoadState':'loaded','ActiveState':'inactive','Result':'success','ExecMainStatus':'0'}
    return receipt,projection,polls,unit

class Tests(unittest.TestCase):
    def report(self,values=None,db_ok=True,bound=True):
        receipt,projection,polls,unit=fixture() if values is None else values
        return evaluate(receipt,projection,polls,unit,db_ok,bound,1,1)
    def test_technical_pass_never_accepts_quality(self):
        result=self.report()
        self.assertIn('TECHNICAL_CHECK_PASS',result['status'])
        self.assertTrue(all(value=='not_assessed' for value in result['acceptance'].values()))
        self.assertFalse(result['training_allowed_by_this_audit'])
        self.assertFalse(result['threshold_selected'])
    def test_input_not_modified(self):
        values=fixture();before=copy.deepcopy(values);self.report(values)
        self.assertEqual(values,before)
    def test_receipt_count_mismatch_requires_review(self):
        values=fixture();values[0]['records_preserved']=4
        self.assertEqual(self.report(values)['technical_checks']['receipt_projection_ledger_counts_match'],'fail')
    def test_hash_and_database_failures_require_review(self):
        self.assertIn('NEEDS_REVIEW',self.report(db_ok=False)['status'])
        self.assertIn('NEEDS_REVIEW',self.report(bound=False)['status'])
    def test_incomplete_not_promoted(self):
        values=fixture();values[0]['status']='OBSERVATION_STOPPED_INCOMPLETE';values[0]['failure_type']='InterruptedError'
        self.assertEqual(self.report(values)['technical_checks']['observer_finished_normally'],'fail')
    def test_clock_divergence_is_explicit(self):
        values=fixture();values[2][1]['observed_at_utc']='2026-11-05T01:00:40+00:00'
        self.assertEqual(self.report(values)['technical_checks']['ledger_clock_alignment_within_original_5s_guard'],'fail')
    def test_running_unit_not_certified(self):
        values=fixture();values[3]['ActiveState']='active'
        self.assertEqual(self.report(values)['technical_checks']['original_unit_not_running'],'fail')
    def test_early_end_not_full_duration(self):
        values=fixture();values[0]['seconds_observed']=30
        self.assertEqual(self.report(values)['technical_checks']['record_elapsed_duration_reached_original_maximum'],'fail')
    def test_source_interval_violation(self):
        values=fixture();values[1]['record_times_inside_approved_interval']=False
        self.assertEqual(self.report(values)['technical_checks']['stored_record_times_within_approved_interval'],'fail')
    def test_no_private_references_in_report(self):
        self.assertNotIn('subject_ref',json.dumps(self.report()))

if __name__=='__main__':
    unittest.main(verbosity=2)
