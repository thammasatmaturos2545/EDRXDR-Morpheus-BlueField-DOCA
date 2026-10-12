"""Synthetic transport only; no broker/service/network access."""
import copy
import unittest
import bluefield_operator_contract as c
import bluefield_operator_source as s
import test_bluefield_operator_contract as fixtures


class Reader:
    def __init__(self, fixture):
        self.parts = {0}
        self.ranges = [(0, 3), (0, 3)]
        self.record = {'source': fixture.source.copy(), 'value': fixture.raw}
        self.calls = []
        self.closed = False
        self.failure = False
    def partitions(self, topic, timeout):
        self.calls.append(('partitions', topic))
        if self.failure: raise RuntimeError('PRIVATE RAW CONTENT')
        return self.parts
    def watermarks(self, topic, partition, timeout):
        self.calls.append(('watermarks', topic, partition))
        return self.ranges.pop(0)
    def fetch_exact(self, topic, partition, offset, timeout):
        self.calls.append(('fetch', topic, partition, offset))
        return self.record
    def close(self): self.closed = True


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Contracts(); self.f.setUp()
        self.r = Reader(self.f)
    def run_read(self, **kwargs):
        return s.inspect_source(self.f.plan, self.f.envelope, self.f.id, self.r, **kwargs)
    def reject(self, reason):
        with self.assertRaisesRegex(c.Rejected, '^' + reason + '$'): self.run_read()
        self.assertTrue(self.r.closed)
    def test_success_metadata_only_exact_bytes(self):
        original = copy.deepcopy(self.f.plan)
        result = self.run_read()
        self.assertEqual(result['input_sha256'], self.f.envelope['input_sha256'])
        self.assertNotIn('value', result)
        self.assertNotIn('carrier', str(result))
        self.assertFalse(result['replay_authorized'])
        self.assertEqual(self.f.plan, original)
        self.assertEqual([x[0] for x in self.r.calls], ['partitions','watermarks','fetch','watermarks'])
        self.assertTrue(self.r.closed)
    def test_topic_missing_no_fetch(self):
        self.r.parts = None
        self.reject('source_topic_missing')
        self.assertEqual(len(self.r.calls), 1)
    def test_partition_missing(self):
        self.r.parts = {1}; self.reject('source_partition_missing')
    def test_retained_offset_missing(self):
        self.r.ranges = [(2,3)]; self.reject('source_unavailable')
    def test_offset_at_end_missing(self):
        self.r.ranges = [(0,1)]; self.reject('source_unavailable')
    def test_retention_race(self):
        self.r.ranges = [(0,3),(2,3)]; self.reject('source_unavailable')
    def test_compacted_or_absent_record(self):
        self.r.record = None; self.reject('source_record_missing')
    def test_wrong_exact_offset(self):
        self.r.record['source']['offset'] = 2; self.reject('source_position_mismatch')
    def test_hash_mismatch_no_json_repair(self):
        self.r.record['value'] = b'{"carrier": 2}'
        self.reject('source_hash_mismatch')
    def test_tombstone(self):
        self.r.record['value'] = None; self.reject('source_missing_or_oversize')
    def test_oversize(self):
        self.r.record['value'] = b'x' * (4*1024*1024+1)
        self.reject('source_missing_or_oversize')
    def test_invalid_watermark_boolean(self):
        self.r.ranges = [(False,3)]; self.reject('invalid_watermarks')
    def test_transport_error_no_payload_disclosure(self):
        self.r.failure = True; self.reject('source_transport_failed')
    def test_elapsed_deadline(self):
        ticks = iter([0,0,11])
        with self.assertRaisesRegex(c.Rejected,'source_read_timeout'):
            self.run_read(clock=lambda: next(ticks))
        self.assertTrue(self.r.closed)
    def test_invalid_timeout_no_io(self):
        for value in [0,-1,31,True,float('nan'),float('inf')]:
            with self.assertRaises(c.Rejected): self.run_read(timeout_seconds=value)
        self.assertEqual(self.r.calls, [])
    def test_plan_tamper_no_io(self):
        self.f.plan['source']['topic'] = 'bluefield-events'
        with self.assertRaises(c.Rejected): self.run_read()
        self.assertEqual(self.r.calls, [])
    def test_close_failure_no_success(self):
        def fail(): raise RuntimeError('private')
        self.r.close = fail
        with self.assertRaisesRegex(c.Rejected,'source_close_failed'): self.run_read()


if __name__ == '__main__': unittest.main(verbosity=2)
