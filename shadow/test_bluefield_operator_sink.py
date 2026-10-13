"""Synthetic sink inspection tests; no Docker or OpenSearch calls."""
import copy
import json
import unittest
from unittest.mock import patch
import bluefield_operator_sink as s
import bluefield_operator_contract as c
import bluefield_operator_fixture as f

class SinkTests(unittest.TestCase):
    def setUp(self):
        self.run = 'opread-' + 'a'*32
        _, self.env, self.eid = f.bundle(self.run)
        self.index = s.names(self.run)
        self.uuid = 'fixture_uuid_1234'
        self.meta = {self.index: {'aliases': {}, 'settings': {'index': {'uuid': self.uuid}}}}
        self.doc = {'_index': self.index, '_id': self.eid, '_seq_no': 0, '_primary_term': 1,
                    '_version': 1, 'found': True, '_source': self.env}
        self.calls = []

    def inspect(self, changes=None):
        replies = [copy.deepcopy(x) for x in (self.meta, self.doc, self.meta, self.doc)]
        if changes:
            changes(replies)
        outer = self
        class Reader:
            def get(self, path, timeout):
                outer.calls.append(path)
                return replies.pop(0)
        return s.inspect_sink(Reader(), self.run, self.eid, self.uuid)

    def test_exact_get_and_metadata_only_contract(self):
        out = self.inspect()
        self.assertFalse(out['replay_authorized'])
        self.assertFalse(out['transport_enabled'])
        self.assertEqual(out['evidence_sha256'], c.evidence(self.env,self.eid))
        self.assertEqual(self.calls, ['/'+self.index, '/'+self.index+'/_doc/'+self.eid]*2)
        self.assertNotIn('raw_event', out['envelope'])

    def test_alias_rejected(self):
        with self.assertRaisesRegex(c.Rejected,'sink_alias_rejected'):
            self.inspect(lambda r: r[0][self.index].update(aliases={'other':{}}))

    def test_uuid_changed_during_read(self):
        with self.assertRaisesRegex(c.Rejected,'sink_index_uuid_changed'):
            self.inspect(lambda r: r[2][self.index]['settings']['index'].update(uuid='different'))

    def test_document_changed(self):
        with self.assertRaisesRegex(c.Rejected,'sink_document_changed'):
            self.inspect(lambda r: r[3].update(_version=2))

    def test_missing_doc(self):
        with self.assertRaisesRegex(c.Rejected,'sink_document_missing'):
            self.inspect(lambda r: r[1].update(found=False))

    def test_wrong_id(self):
        with self.assertRaisesRegex(c.Rejected,'sink_document_identity'):
            self.inspect(lambda r: r[1].update(_id='b'*64))

    def test_payload_field_rejected(self):
        with self.assertRaisesRegex(c.Rejected,'invalid_envelope_fields'):
            self.inspect(lambda r: r[1]['_source'].update(raw_event='secret'))

    def test_input_hash_id_mismatch(self):
        with self.assertRaisesRegex(c.Rejected,'evidence_id_mismatch'):
            self.inspect(lambda r: r[1]['_source'].update(input_sha256='b'*64))

    def test_bool_sequence_rejected(self):
        with self.assertRaisesRegex(c.Rejected,'sink_document_version'):
            self.inspect(lambda r: r[1].update(_seq_no=True))

    def test_strict_json(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'invalid', b' '*65537):
            with self.subTest(raw=raw[:20]), self.assertRaises(c.Rejected): s.strict_json(raw)

    def test_unsafe_path_no_io(self):
        reader=s.HostReader(); reader.container_id='fixture'
        with patch.object(reader,'execute') as io:
            for path in ('/bluefield-events','/shadow-bluefield-quarantine-dlq-*/_search','/index/../_delete_by_query'):
                with self.assertRaises(c.Rejected): reader.get(path,5)
            io.assert_not_called()

    def test_invalid_names_no_io(self):
        with self.assertRaises(c.Rejected): s.names('../live',self.eid)
        with self.assertRaises(c.Rejected): s.names(self.run,'*')

    def test_no_preflight_no_io(self):
        reader=s.HostReader()
        with patch.object(reader,'execute') as io:
            with self.assertRaisesRegex(c.Rejected,'sink_preflight_required'): reader.get('/'+self.index,5)
            io.assert_not_called()

    def test_deadline(self):
        with self.assertRaisesRegex(c.Rejected,'sink_deadline'):
            s.inspect_sink(None,self.run,self.eid,self.uuid,clock=iter([0,31]).__next__)

if __name__ == '__main__':
    unittest.main()
