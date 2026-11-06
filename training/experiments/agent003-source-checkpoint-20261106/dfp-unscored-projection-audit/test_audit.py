import json, unittest
from audit import summarize
from diagnostic_candidate import labels
from journal_adapter import project

def fixture(n=1, unscored=False):
    ref = f'{n:064x}'
    return ref, {
        'schema_version':'bounded-journal-auth-observation-0','journal_record_ref':ref,
        'event_time_utc':'2026-11-05T01:00:00+00:00',
        'poll_observed_at_utc':'2026-11-05T01:00:20+00:00',
        'query_snapshot_sha256':'a'*64,'query_row':1,
        'status':'unscored' if unscored else 'candidate_mapping_only_not_scored',
        'reason':'unsupported_message_format' if unscored else 'unverified_journal_format_identity_and_coverage',
        'event_kind':None if unscored else 'ssh_auth_success',
        'subject_role':None if unscored else 'candidate_account',
        'subject_ref':None if unscored else 'b'*64,
        'actor_ref':None,'target_ref':None,'attempt_ref':None,'source_ip_ref':None,
        'model_scored':False,'window_complete':False,'source_coverage_accepted':False,
        'training_eligible':False,
        'identity_scope':'bounded_journal_observation_candidate_not_legacy_event_uid'}

def encoded(n=1, unscored=False):
    identity, row = fixture(n,unscored)
    return identity, json.dumps(row)

class Tests(unittest.TestCase):
    def test_synthetic_counts_not_reclassification(self):
        rows=[encoded(n+1,n<106) for n in range(285)]
        result=summarize(rows)
        self.assertEqual(result['unscored_records'],106)
        self.assertEqual(result['candidate_records'],179)
        self.assertEqual(result['unscored_without_recoverable_event_kind'],106)
        self.assertEqual(result['buckets_containing_both_candidate_and_unscored'],1)
        self.assertFalse(result['parser_subreason_retained'])
        self.assertNotIn('b'*64,json.dumps(result))
    def test_unknown_reason_never_echoed(self):
        identity,row=fixture(unscored=True);row['reason']='private_untrusted_value'
        result=summarize([(identity,json.dumps(row))])
        self.assertNotIn('private_untrusted_value',json.dumps(result))
        self.assertEqual(result['masked_unknown_reason_rows'],1)
    def test_extra_raw_field_rejected(self):
        identity,row=fixture();row['full_log']='private'
        with self.assertRaises(ValueError):summarize([(identity,json.dumps(row))])
    def test_safety_promotion_rejected(self):
        identity,row=fixture();row['training_eligible']=True
        with self.assertRaises(ValueError):summarize([(identity,json.dumps(row))])
    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):summarize([encoded(),encoded()])
    def test_naive_time_rejected(self):
        identity,row=fixture();row['event_time_utc']='2026-11-05T01:00:00'
        with self.assertRaises(ValueError):summarize([(identity,json.dumps(row))])
    def test_unknown_event_kind_rejected(self):
        identity,row=fixture();row['event_kind']='private_untrusted_kind'
        with self.assertRaises(ValueError):summarize([(identity,json.dumps(row))])
    def test_query_reference_and_row_guard(self):
        identity,row=fixture();row['query_row']=True
        with self.assertRaises(ValueError):summarize([(identity,json.dumps(row))])
    def test_empty_snapshot_not_fabricated(self):
        result=summarize([])
        self.assertIsNone(result['unscored_record_fraction'])
        self.assertEqual(result['observed_event_time_buckets'],0)
    def test_future_diagnostics_preserve_finite_detail(self):
        for message,program,expected in [
            ('unsupported text','sudo','unsupported_message_format'),
            (None,'sshd','nontext_message'),
            ('private\nmultiline','sshd','multiline_message_unverified'),
            ('x'*32769,'sshd','message_too_large'),
            ('private account data','unknown-private-program','unsupported_source_program')]:
            result=labels(project(message,program),program)
            self.assertEqual(result['parse_status'],expected)
            self.assertNotIn('private',json.dumps(result))
    def test_future_diagnostics_do_not_echo_account(self):
        message='Accepted password for synthetic_private_account from 192.0.2.10 port 33333 ssh2'
        result=labels(project(message,'sshd'),'sshd')
        self.assertEqual(result['source_family'],'ssh')
        self.assertEqual(result['parse_status'],'format_candidate')
        self.assertNotIn('synthetic_private_account',json.dumps(result))
        self.assertNotIn('192.0.2.10',json.dumps(result))
    def test_diagnostics_do_not_mutate_input(self):
        projection=project('unsupported text','sudo');before=json.dumps(projection)
        labels(projection,'sudo')
        self.assertEqual(json.dumps(projection),before)

if __name__ == '__main__':
    unittest.main(verbosity=2)
