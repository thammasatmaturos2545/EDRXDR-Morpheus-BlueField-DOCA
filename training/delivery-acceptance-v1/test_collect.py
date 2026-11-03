from pathlib import Path
from unittest.mock import patch
import json
import tempfile
import unittest
import collect_status as collector


class StatusTests(unittest.TestCase):
    def fixture(self):
        temporary=tempfile.TemporaryDirectory(prefix='status-mock-',dir=Path(__file__).resolve().parent)
        self.addCleanup(temporary.cleanup)
        prep=Path(temporary.name)
        patcher=patch.object(collector,'PREP',prep);patcher.start();self.addCleanup(patcher.stop)
        return prep

    def test_absent_consumption_never_requests_start(self):
        self.fixture();result=collector.pilot_status()
        self.assertFalse(result['start_confirmed'])
        self.assertEqual(result['status'],'NO_CONSUMED_APPROVAL_FILE')

    def test_running_and_restored_receipts_are_not_logging_verification(self):
        for status in ('OBSERVING','RESTORED'):
            with self.subTest(status=status):
                prep=self.fixture();attempt=prep/'approved-55m-synthetic';attempt.mkdir()
                (prep/'approval-consumed.json').write_text(json.dumps({'attempt':str(attempt)}))
                (attempt/'state.json').write_text(json.dumps({'status':status,'baseline_prefix_sha256':'private',
                    'private_config':'must-not-leak','capture':{'capture_lines':10,'raw':'must-not-leak'}}))
                result=collector.pilot_status()
                self.assertEqual(result['status'],status)
                self.assertNotIn('must-not-leak',json.dumps(result));self.assertNotIn('private_config',result)

    def test_redirected_attempt_rejected(self):
        prep=self.fixture()
        (prep/'approval-consumed.json').write_text(json.dumps({'attempt':str(prep.parent/'outside')}))
        with self.assertRaises(ValueError):collector.pilot_status()

    def test_oversized_metadata_rejected(self):
        prep=self.fixture();p=prep/'oversized.json';p.write_bytes(b' '*262145)
        with self.assertRaises(ValueError):collector.bounded_json(p)


if __name__=='__main__':unittest.main()
