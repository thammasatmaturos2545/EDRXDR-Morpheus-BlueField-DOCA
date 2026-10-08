import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from raw_event_contract import event_text, reconstruct, sha
from quality_metrics import metrics, evaluate


class ContractTests(unittest.TestCase):
    def test_text(self):
        self.assertEqual(event_text({'rule': {'description': ' X '}, 'full_log': ' Y '}), 'Description: X\nLog: Y')
        self.assertEqual(event_text({'full_log': 'Y'}), 'Description: [missing]\nLog: Y')
        self.assertEqual(event_text({'rule': {'description': 'X'}}), 'Description: X\nLog: [missing]')
        self.assertEqual(event_text({'rule': None, 'full_log': 'Y'}), 'Description: [missing]\nLog: Y')

    def test_reject(self):
        for event in ({}, {'rule': {}}, {'full_log': '  '}, [], {'rule': []},
                      {'full_log': ['secret']}, {'rule': {'description': 7}}):
            with self.subTest(event=event), self.assertRaises(ValueError):
                event_text(event)

    def test_label_fields_not_input(self):
        a = {'rule': {'description': 'X', 'id': '1', 'level': 1}, 'full_log': 'Y'}
        b = {'rule': {'description': 'X', 'id': '99', 'level': 15}, 'full_log': 'Y'}
        self.assertEqual(event_text(a), event_text(b))

    def test_snapshot_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'a.json.gz'
            event = dict(manager={'name':'m'}, agent={'id':'a'}, id='i', rule={'id':'1','level':3,'description':'X'})
            # A held-out invalid row must never be parsed or transformed.
            with gzip.open(p, 'wt') as f:
                f.write(json.dumps(event)+'\nNOT_SELECTED\n')
            row = dict(source_file=p.name, source_line=1, event_id=hashlib.sha256(json.dumps(['m','a','i']).encode()).hexdigest(),
                       rule_id='1', text_input='Description: X\nLog: [missing]', weak_label='low_severity')
            manifest = {'source_sha256':{p.name:sha(p)}}
            data = {'train':[row], 'validation':[]}
            self.assertEqual(reconstruct(directory, manifest, data)['reconstructed_rows'], 1)
            row['text_input'] = 'wrong'
            with self.assertRaises(ValueError): reconstruct(directory, manifest, data)
            manifest['source_sha256'][p.name] = 'wrong'
            with self.assertRaises(ValueError): reconstruct(directory, manifest, data)

    def test_metrics(self):
        m = metrics([('high_severity', .9), ('high_severity', .1), ('low_severity', .9), ('low_severity', .1)])
        self.assertEqual((m['tp'],m['fp'],m['tn'],m['fn']), (1,1,1,1))
        self.assertEqual(m['f1'], .5)
        self.assertIsNone(metrics([('low_severity', .1)])['recall'])
        with self.assertRaises(ValueError): metrics([('low_severity', float('nan'))])
        with self.assertRaises(ValueError): evaluate([{}], [])

if __name__ == '__main__': unittest.main()
