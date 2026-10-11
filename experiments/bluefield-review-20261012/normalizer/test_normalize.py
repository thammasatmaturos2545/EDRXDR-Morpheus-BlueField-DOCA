from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from normalize import COUNTERS, Normalizer


def event(second=0, value=0, **changes):
    return dict(schema_version='bluefield-monitor-review-1', source='bluefield',
                measurement_scope='host_interface_counters', timestamp=f'2026-10-12T00:00:{second:02}Z',
                ibdev='mlx5_0', interface='test0', operstate='down', carrier=None,
                read_errors={'carrier': 'Invalid argument'}, **{k: value for k in COUNTERS}, **changes)


class Tests(unittest.TestCase):
    def setUp(self):
        self.n = Normalizer('synthetic-fixtures-only')

    def test_first_sample_has_no_invented_delta(self):
        out = self.n.normalize(event(value=100))
        self.assertIsNone(out['delta_rx_bytes'])
        self.assertEqual(out['delta_status']['rx_bytes'], 'first_sample')

    def test_zero_down_and_unknown_carrier_preserved(self):
        self.n.normalize(event())
        out = self.n.normalize(event(2))
        self.assertEqual(out['delta_rx_bytes'], 0)
        self.assertIsNone(out['carrier'])
        self.assertEqual(out['operstate'], 'down')

    def test_increment(self):
        self.n.normalize(event(value=10))
        self.assertEqual(self.n.normalize(event(2, 15))['delta_rx_bytes'], 5)

    def test_unavailable_does_not_bridge_gap(self):
        self.n.normalize(event(value=10))
        missing = event(2, 15)
        missing['rx_bytes'] = None
        missing['read_errors']['rx_bytes'] = 'Permission denied'
        out = self.n.normalize(missing)
        self.assertIsNone(out['rx_bytes'])
        self.assertIsNone(out['delta_rx_bytes'])
        self.assertEqual(out['delta_tx_bytes'], 5)
        self.assertEqual(self.n.normalize(event(4, 20))['delta_status']['rx_bytes'], 'baseline_unavailable')
        self.assertEqual(self.n.normalize(event(6, 23))['delta_rx_bytes'], 3)

    def test_counter_decrease_is_not_clamped_to_zero(self):
        self.n.normalize(event(value=100))
        out = self.n.normalize(event(2, 3))
        self.assertIsNone(out['delta_rx_bytes'])
        self.assertEqual(out['delta_status']['rx_bytes'], 'counter_decreased')
        self.assertEqual(self.n.normalize(event(4, 5))['delta_rx_bytes'], 2)

    def test_long_gap(self):
        self.n.normalize(event())
        self.assertEqual(self.n.normalize(event(20, 100))['delta_status']['rx_bytes'], 'sample_gap')

    def test_duplicate_or_older_preserves_state(self):
        self.n.normalize(event(2, 10))
        for second in (0, 2):
            with self.assertRaises(ValueError):
                self.n.normalize(event(second, 100))
        self.assertEqual(self.n.normalize(event(4, 12))['delta_rx_bytes'], 2)

    def test_interface_change_rebaselines_even_when_returning(self):
        self.n.normalize(event())
        other = event(2, 100)
        other['interface'] = 'test1'
        self.assertEqual(self.n.normalize(other)['delta_status']['rx_bytes'], 'interface_changed')
        self.assertIsNone(self.n.normalize(event(4, 30))['delta_rx_bytes'])

    def test_devices_and_capture_instances_are_separate(self):
        self.n.normalize(event(value=100))
        other = event(2, 1)
        other['ibdev'] = 'mlx5_1'
        self.assertIsNone(self.n.normalize(other)['delta_rx_bytes'])
        self.assertIsNone(Normalizer('other-capture').normalize(event(4, 200))['delta_rx_bytes'])

    def test_bad_numbers_and_inconsistent_errors_rejected(self):
        for value in (True, -1, '2', 1.5, 2**64, None):
            bad = event()
            bad['rx_bytes'] = value
            with self.assertRaises(ValueError):
                self.n.normalize(bad)
        bad = event()
        bad['read_errors']['rx_bytes'] = 'error with a non-null value'
        with self.assertRaises(ValueError):
            self.n.normalize(bad)

    def test_uint64_and_deepcopy(self):
        original = event(value=2**64 - 1)
        saved = deepcopy(original)
        out = self.n.normalize(original)
        self.assertEqual(out['rx_bytes'], 2**64 - 1)
        out['raw_event']['rx_bytes'] = 0
        self.assertEqual(original, saved)
        self.assertEqual(self.n.normalize(event(2, 2**64 - 1))['delta_rx_bytes'], 0)

    def test_invalid_schema_and_timezone(self):
        for field, value in (('schema_version', 'old'), ('source', 'wazuh'), ('timestamp', '2026-10-12T00:00:00')):
            bad = event()
            bad[field] = value
            with self.assertRaises(ValueError):
                self.n.normalize(bad)

    def test_unmapped_interface_stays_unknown(self):
        bad = event()
        for k in ('interface', 'operstate', 'carrier', *COUNTERS):
            bad[k] = None
            bad['read_errors'][k] = 'mapping unavailable'
        self.assertIsNone(self.n.normalize(bad)['delta_rx_bytes'])

    def test_cli_failure_creates_no_partial_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / 'input.jsonl', root / 'output.jsonl'
            command = [sys.executable, str(Path(__file__).with_name('normalize.py')), str(source), str(output), '--capture-scope', 'fixture']
            source.write_text(json.dumps(event()) + '\nINVALID\n')
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            source.write_text(json.dumps(event()) + '\n')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            before = output.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
