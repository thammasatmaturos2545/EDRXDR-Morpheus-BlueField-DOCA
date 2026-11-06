import sys,types,json,unittest
from pathlib import PurePosixPath
if sys.platform=='win32':
    sys.modules['fcntl']=types.SimpleNamespace()
import probe

FILES=PurePosixPath('/var/lib/edrxdr-endpoint-probes/probe-synthetic/files')
def events():
    rows=[];number=0
    for case_id,count,_ in probe.CASES:
        for index in range(count):
            number+=1
            rows.append({'id':str(number),'agent':{'id':'003'},
                'syscheck':{'path':str(FILES/f'normal-{index:02}.txt'),
                'sha256_after':probe.digest(probe.content(case_id,index)),
                'event':'modified','mode':'realtime'}})
    return rows
def raw(rows):
    return b'\n'.join(json.dumps(row).encode() for row in rows)

class Tests(unittest.TestCase):
    def test_all_cases_matched_by_content_reference(self):
        result=probe.summarize(raw(events()),FILES)
        self.assertTrue(result['all20_owned_modifications_matched_by_path_and_after_hash'])
        self.assertEqual(list(result['received_unique_modified_paths'].values()),[4,8,8])
        self.assertTrue(result['normal_bulk_and_controlled_fast_have_same_case_aggregate_signature'])
        self.assertFalse(result['ransomware_detection_verified'])
    def test_duplicates_do_not_inflate_counts(self):
        rows=events();result=probe.summarize(raw(rows+[rows[0]]),FILES)
        self.assertEqual(result['identical_delivery_retries'],1)
        self.assertEqual(result['received_modified_event_counts']['quiet-small-edits'],4)
    def test_missing_delivery_is_not_success(self):
        result=probe.summarize(raw(events()[:-1]),FILES)
        self.assertFalse(result['all20_owned_modifications_matched_by_path_and_after_hash'])
        self.assertIsNone(result['normal_bulk_and_controlled_fast_have_same_case_aggregate_signature'])
    def test_foreign_agent_rejected_from_counts(self):
        rows=events();rows[0]['agent']['id']='004'
        result=probe.summarize(raw(rows),FILES)
        self.assertEqual(result['foreign_agent_matches'],1)
        self.assertFalse(result['all20_owned_modifications_matched_by_path_and_after_hash'])
    def test_conflicting_delivery_id_fails_closed(self):
        rows=events();rows[1]['id']=rows[0]['id']
        with self.assertRaises(ValueError):probe.summarize(raw(rows),FILES)
    def test_content_guard_only_owned_bounded_files(self):
        for case_id,count,_ in probe.CASES:
            for index in range(count):self.assertLess(len(probe.content(case_id,index)),1024)
        with self.assertRaises(ValueError):probe.content('unknown-scenario',0)
        with self.assertRaises(ValueError):probe.content(probe.CASES[0][0],100)

if __name__=='__main__':
    unittest.main(verbosity=2)
