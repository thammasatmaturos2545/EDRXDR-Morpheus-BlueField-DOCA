"""Synthetic backend tests only. Never contact Kafka."""
import unittest
from unittest.mock import patch
import bluefield_operator_fixture as f
import bluefield_operator_contract as c


class Backend:
    def __init__(self):
        self.data={}; self.calls=[]; self.bad_ack=False; self.accept_bad=False
        self.inspect_count=0; self.extra=False
    def topics(self): self.calls.append('topics'); return set(self.data)
    def create(self, topic): self.calls.append('create'); self.data[topic]=[]
    def bounds(self, topic): return (0,len(self.data[topic]))
    def publish(self, topic, raw):
        self.calls.append('publish'); self.data[topic].append(raw)
        if self.extra: self.data[topic].append(raw)
        return {'topic':topic,'partition':0,'offset':1 if self.bad_ack else 0}
    def inspect(self, plan, envelope, evidence_id):
        self.inspect_count+=1
        c.validate_plan(plan,envelope,evidence_id)
        if self.accept_bad: return {'status':'verified_at_read','replay_authorized':False}
        source=plan['source']; values=self.data.get(source['topic'])
        c.require(values is not None,'source_topic_missing')
        c.require(source['offset'] < len(values),'source_unavailable')
        c.verify_source(plan,source,values[source['offset']],0,len(values))
        return {'status':'verified_at_read','replay_authorized':False}


class FixtureTests(unittest.TestCase):
    def setUp(self): self.b=Backend(); self.events=[]
    def run_fixture(self, allowed='1'):
        return f.exercise(self.b,allowed=allowed,emit=lambda kind,**data:self.events.append((kind,data)))
    def test_mutation_gate_no_calls(self):
        for val in [None,'0','true',True]:
            with self.assertRaises(c.Rejected): self.run_fixture(val)
        self.assertEqual(self.b.calls,[])
    def test_one_record_and_three_negatives(self):
        result=self.run_fixture()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(len(result['negative_cases']),3)
        self.assertEqual(self.b.calls.count('create'),1)
        self.assertEqual(self.b.calls.count('publish'),1)
        self.assertEqual(self.b.inspect_count,4)
        self.assertFalse(result['approval_issued'])
        self.assertFalse(result['controlled_replay_sent'])
        self.assertNotIn('carrier',str(self.events))
    def test_ack_mismatch_blocks_inspection(self):
        self.b.bad_ack=True
        with self.assertRaisesRegex(c.Rejected,'fixture_ack_mismatch'): self.run_fixture()
        self.assertEqual(self.b.inspect_count,0)
    def test_extra_record_blocks_inspection(self):
        self.b.extra=True
        with self.assertRaisesRegex(c.Rejected,'fixture_not_single_record'): self.run_fixture()
        self.assertEqual(self.b.inspect_count,0)
    def test_negative_acceptance_fails(self):
        self.b.accept_bad=True
        with self.assertRaisesRegex(c.Rejected,'negative_case_accepted'): self.run_fixture()
        self.assertNotIn('fixture_reader_result',[x[0] for x in self.events])
    def test_topic_collision_no_create(self):
        class Fixed: hex='a'*32
        with patch.object(f.uuid,'uuid4',return_value=Fixed()):
            self.b.data['shadow-bluefield-quarantine-input-opread-'+'a'*32]=[]
            with self.assertRaisesRegex(c.Rejected,'fixture_name_collision'): self.run_fixture()
        self.assertNotIn('create',self.b.calls)
    def test_new_run_each_invocation(self):
        one=self.run_fixture(); two=self.run_fixture()
        self.assertNotEqual(one['run_id'],two['run_id'])
    def test_bundle_preserves_original_fixture_hash(self):
        plan,env,eid=f.bundle('opread-'+'b'*32)
        c.validate_plan(plan,env,eid)
        self.assertEqual(c.verify_source(plan,plan['source'],f.RAW,0,1),f.RAW)
    def test_live_run_rejected(self):
        with self.assertRaises(c.Rejected): f.bundle('../bluefield-events')
    def test_create_failure_no_publish(self):
        def fail(topic): raise RuntimeError('creation uncertain')
        self.b.create=fail
        with self.assertRaises(RuntimeError): self.run_fixture()
        self.assertNotIn('publish',self.b.calls)
    def test_publish_failure_no_retry(self):
        def fail(topic,raw):
            self.b.calls.append('publish'); raise RuntimeError('ack uncertain')
        self.b.publish=fail
        with self.assertRaises(RuntimeError): self.run_fixture()
        self.assertEqual(self.b.calls.count('publish'),1)
        self.assertEqual(self.b.inspect_count,0)
    def test_nonempty_new_topic_no_publish(self):
        self.b.bounds=lambda topic:(0,1)
        with self.assertRaisesRegex(c.Rejected,'fixture_not_empty'): self.run_fixture()
        self.assertNotIn('publish',self.b.calls)


if __name__ == '__main__': unittest.main(verbosity=2)
