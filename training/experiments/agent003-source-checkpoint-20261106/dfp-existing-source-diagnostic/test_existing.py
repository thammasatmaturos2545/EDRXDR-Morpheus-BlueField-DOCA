from datetime import datetime, timezone, timedelta
import copy, json, unittest
import review_existing as review

KEY = bytes(range(32))  # Synthetic test key only.
START = datetime(2026,11,5,1,0,0,tzinfo=timezone.utc)
END = START + timedelta(minutes=5)

def row(n=1, message='Connection closed by 192.0.2.10 port 33333'):
    return {'_BOOT_ID':'a'*32,'__CURSOR':'synthetic-cursor-'+str(n),
            '__REALTIME_TIMESTAMP':str(int((START+timedelta(seconds=n)).timestamp()*1000000)),
            '_COMM':'sshd','SYSLOG_IDENTIFIER':'sshd','MESSAGE':message}

def expected(values):
    return {review.mac(KEY,'journal_record',v['_BOOT_ID'],v['__CURSOR']):
            review.mac(KEY,'payload',v) for v in values}

def encoded(values):
    return b'\n'.join(json.dumps(value).encode() for value in values)

class Tests(unittest.TestCase):
    def test_exact_matching_transport_notice_only(self):
        target=row(); other=row(2,'Accepted password for synthetic_user from 192.0.2.10 port 33333 ssh2')
        result=review.summarize(encoded([target,other]),KEY,expected([target]),START,END)
        self.assertEqual(result['exact_identity_and_payload_matched_targets'],1)
        self.assertEqual(result['format_indicator_counts']['ssh_transport_notice_format_only'],1)
        for private in ('192.0.2.10','synthetic_user','synthetic-cursor'):
            self.assertNotIn(private,json.dumps(result))
    def test_changed_payload_for_same_identity_rejected(self):
        original=row(); changed=copy.deepcopy(original);changed['MESSAGE']='Changed private message'
        before=copy.deepcopy(original)
        with self.assertRaises(ValueError):
            review.summarize(encoded([changed]),KEY,expected([original]),START,END)
        self.assertEqual(original,before)
    def test_missing_retained_source_not_called_benign(self):
        target=row();result=review.summarize(b'',KEY,expected([target]),START,END)
        self.assertEqual(result['targets_not_recovered_from_current_retention'],1)
        self.assertFalse(result['baseline_accepted'])
    def test_duplicate_source_identity_rejected(self):
        target=row()
        with self.assertRaises(ValueError):
            review.summarize(encoded([target,target]),KEY,expected([target]),START,END)
    def test_unknown_raw_field_rejected(self):
        target=row();target['unexpected_private_field']='not exported'
        with self.assertRaises(ValueError):
            review.summarize(encoded([target]),KEY,expected([target]),START,END)
    def test_outside_interval_rejected(self):
        target=row();target['__REALTIME_TIMESTAMP']='0'
        with self.assertRaises(ValueError):
            review.summarize(encoded([target]),KEY,expected([target]),START,END)
    def test_row_cap_is_fail_closed(self):
        values=[row(n+1) for n in range(1001)]
        with self.assertRaises(ValueError):
            review.summarize(encoded(values),KEY,{},START,END)
    def test_byte_cap_is_fail_closed(self):
        with self.assertRaises(ValueError):
            review.summarize(b'x'*(review.MAX_BYTES+1),KEY,{},START,END)
    def test_ambiguous_programs_are_metadata_not_account_guess(self):
        target=row();target['SYSLOG_IDENTIFIER']='sudo'
        result=review.summarize(encoded([target]),KEY,expected([target]),START,END)
        self.assertEqual(result['metadata_selection_counts']['ambiguous_selected_programs'],1)
        self.assertEqual(result['parser_stage_counts']['unsupported_source_program'],1)
    def test_original_nontext_and_multiline_failure_distinguished(self):
        for message,cause in ((None,'nontext_message'),('private\ntext','multiline_message_unverified')):
            target=row(message=message)
            result=review.summarize(encoded([target]),KEY,expected([target]),START,END)
            self.assertEqual(result['parser_stage_counts'][cause],1)
            self.assertNotIn('private',json.dumps(result))
    def test_successful_parser_conflicts_with_stored_unsupported(self):
        target=row(message='Accepted password for synthetic_user from 192.0.2.10 port 33333 ssh2')
        with self.assertRaises(ValueError):
            review.summarize(encoded([target]),KEY,expected([target]),START,END)
    def test_fixed_query_is_historical_bounded_no_shell(self):
        args=review.query_args(START,END)
        self.assertEqual(args[:3],['sudo','-n','journalctl'])
        self.assertIn('--lines=1001',args)
        self.assertIn('--output-fields=MESSAGE,__REALTIME_TIMESTAMP,_SYSTEMD_UNIT,_COMM,SYSLOG_IDENTIFIER',args)
        self.assertNotIn('-f',args)

if __name__=='__main__':
    unittest.main(verbosity=2)
