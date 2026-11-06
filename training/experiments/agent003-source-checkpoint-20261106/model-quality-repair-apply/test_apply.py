import sys, types, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
if sys.platform == 'win32':
    sys.modules['fcntl'] = types.SimpleNamespace()
import apply as repair

class Tests(unittest.TestCase):
    def setUp(self):
        if sys.platform == 'win32':
            context = patch.object(repair.os, 'O_NOFOLLOW', 0, create=True)
            context.start(); self.addCleanup(context.stop)
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.drop = self.root / 'owned.conf'
        self.content = b'[Service]\nEnvironmentFile=/synthetic/path\n'
        self.before = {'WorkingDirectory': '/synthetic/release/frontend'}
        self.plan = {'runtime_before': self.before,
                     'frozen_report_directory': str(self.root / 'reports'),
                     'proposed_dropin_sha256': repair.sha(self.content)}
        self.started = []
        def show(key):
            return {'NeedDaemonReload': 'no', 'DropInPaths': '',
                    'WorkingDirectory': self.before['WorkingDirectory'],
                    'MainPID': '123'}[key]
        for name, value in (
            ('ROOT', self.root), ('runtime', lambda: dict(self.before)),
            ('show', show), ('command', lambda args: self.started.append(args) or ''),
            ('read', lambda path: Path(path).read_bytes()),
            ('restart', lambda: None),
            ('report_environment', lambda: self.plan['frozen_report_directory']
             if self.drop.exists() else '/old/reports')):
            context = patch.object(repair, name, value)
            context.start(); self.addCleanup(context.stop)

    def http(self, path, body=False):
        if path == '/api/model-quality':
            if not self.drop.exists(): return 503, None
            return 200, {'source': {
                'quality_sha256': repair.EXPECTED['quality_report.json'],
                'parity_sha256': repair.EXPECTED['parity_report.json']},
                'quality': {'scope': 'development_only', 'threshold': 0.5},
                'parity': {'threshold': 0.5}}
        return 200, None

    def test_success_arms_watchdog_before_install(self):
        with patch.object(repair, 'http', self.http):
            repair.apply(self.plan, self.drop, self.content)
        self.assertEqual(self.drop.read_bytes(), self.content)
        result = json.loads((self.root/'apply-result-private.json').read_text())
        self.assertEqual(result['status'], 'QUALITY_PATH_REPAIR_PASS')
        self.assertTrue(any(x[0] == 'systemd-run' for x in self.started))

    def test_bad_report_hash_rolls_back(self):
        def http(path, body=False):
            status, data = self.http(path, body)
            if data: data['source']['quality_sha256'] = '0' * 64
            return status, data
        with patch.object(repair, 'http', http):
            with self.assertRaises(RuntimeError):
                repair.apply(self.plan, self.drop, self.content)
        self.assertFalse(self.drop.exists())
        self.assertEqual(json.loads((self.root/'rollback-result-private.json').read_text())['status'], 'ROLLBACK_PASS')

    def test_stale_plan_no_configuration_write(self):
        with patch.object(repair, 'runtime', lambda: {'WorkingDirectory': '/changed'}):
            with self.assertRaises(RuntimeError):
                repair.apply(self.plan, self.drop, self.content)
        self.assertFalse(self.drop.exists())
        self.assertFalse((self.root/'attempt-private.json').exists())

    def test_existing_dropin_not_overwritten(self):
        self.drop.write_bytes(b'other administrator')
        with self.assertRaises(RuntimeError):
            repair.apply(self.plan, self.drop, self.content)
        self.assertEqual(self.drop.read_bytes(), b'other administrator')

    def test_rollback_refuses_changed_owned_file(self):
        repair.save(self.root/'attempt-private.json', {})
        self.drop.write_bytes(b'concurrent administrator edit')
        with self.assertRaises(RuntimeError):
            repair.rollback(self.plan, self.drop)
        self.assertTrue(self.drop.exists())

    def test_successful_watchdog_does_not_rollback(self):
        repair.save(self.root/'apply-result-private.json',
                    {'status': 'QUALITY_PATH_REPAIR_PASS'})
        repair.rollback(self.plan, self.drop, automatic=True)
        self.assertFalse((self.root/'rollback-result-private.json').exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)
