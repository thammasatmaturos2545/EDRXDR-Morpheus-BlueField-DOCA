"""Compile real monitor.c with a synthetic DOCA adapter; no hardware or broker access."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent
COUNTERS = ('rx_packets', 'tx_packets', 'rx_bytes', 'tx_bytes', 'rx_errors', 'tx_errors')


class MonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='bluefield-unit-')
        cls.root = Path(cls.temp.name)
        cls.sysfs = cls.root / 'sys'
        (cls.root / 'doca_dev.h').write_text('''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef int doca_error_t;
#define DOCA_SUCCESS 0
struct doca_devinfo { int unused; };
static inline int doca_devinfo_create_list(struct doca_devinfo ***p, uint32_t *n) {
    static struct doca_devinfo device;
    static struct doca_devinfo *items[] = {&device}; *p = items; *n = 1; return 0;
}
static inline int doca_devinfo_get_ibdev_name(struct doca_devinfo *p, char *s, size_t n) {
    (void)p; if (n < 7) return 1; memcpy(s, "mlx5_0", 7); return 0;
}
static inline void doca_devinfo_destroy_list(struct doca_devinfo **p) { (void)p; }
''')
        (cls.root / 'doca_error.h').write_text('static inline const char *doca_error_get_descr(int n) { (void)n; return "stub"; }\n')
        cls.binary = cls.root / 'monitor-test'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-I', str(cls.root), f'-DSYSFS_ROOT="{cls.sysfs}"',
                        str(SOURCE / 'monitor.c'), '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        import shutil
        if self.sysfs.exists():
            shutil.rmtree(self.sysfs)
        self.mapping = self.sysfs / 'class/infiniband/mlx5_0/device/net'
        (self.mapping / 'test0').mkdir(parents=True)
        self.interface = self.sysfs / 'class/net/test0'
        (self.interface / 'statistics').mkdir(parents=True)
        (self.interface / 'operstate').write_text('down\n')
        (self.interface / 'carrier').write_text('0\n')
        for key in COUNTERS:
            (self.interface / 'statistics' / key).write_text('0\n')

    def read(self):
        p = subprocess.run([str(self.binary), '--samples', '1'], capture_output=True, text=True, timeout=5, check=True)
        lines = p.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        return json.loads(lines[0])

    def test_zero_is_real_zero_and_down_is_visible(self):
        data = self.read()
        self.assertEqual(data['operstate'], 'down')
        self.assertEqual(data['carrier'], 0)
        self.assertEqual(data['read_errors'], {})
        for key in COUNTERS:
            self.assertEqual(data[key], 0)

    def test_missing_counter_is_null_not_zero(self):
        (self.interface / 'statistics/rx_bytes').unlink()
        data = self.read()
        self.assertIsNone(data['rx_bytes'])
        self.assertIn('rx_bytes', data['read_errors'])
        self.assertEqual(data['tx_bytes'], 0)

    def test_invalid_negative_overflow_empty_and_embedded_nul(self):
        for value in ('garbage', '-1', '18446744073709551616', '', '12\x00bad', '1 2', '+2'):
            with self.subTest(value=value):
                (self.interface / 'statistics/rx_packets').write_text(value)
                data = self.read()
                self.assertIsNone(data['rx_packets'])
                self.assertIn('rx_packets', data['read_errors'])

    def test_uint64_max_is_preserved(self):
        (self.interface / 'statistics/rx_bytes').write_text('18446744073709551615\n')
        self.assertEqual(self.read()['rx_bytes'], 18446744073709551615)

    def test_missing_or_invalid_carrier_is_unknown(self):
        (self.interface / 'carrier').unlink()
        self.assertIsNone(self.read()['carrier'])
        (self.interface / 'carrier').write_text('2')
        self.assertIsNone(self.read()['carrier'])

    def test_ambiguous_mapping_is_not_arbitrary(self):
        (self.mapping / 'other0').mkdir()
        data = self.read()
        self.assertIsNone(data['interface'])
        self.assertEqual(data['read_errors']['interface'], 'ambiguous_interface_mapping')
        for key in COUNTERS:
            self.assertIsNone(data[key])

    def test_missing_mapping_and_operstate(self):
        (self.interface / 'operstate').unlink()
        self.assertIsNone(self.read()['operstate'])
        (self.mapping / 'test0').rmdir()
        self.assertIsNone(self.read()['interface'])

    def test_cli_rejects_unbounded_or_invalid_samples(self):
        for value in ('0', '101', '-1', 'abc'):
            p = subprocess.run([str(self.binary), '--samples', value], capture_output=True, timeout=5)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(p.stdout, b'')

    def test_two_samples_exit_without_timeout(self):
        p = subprocess.run([str(self.binary), '--samples', '2'], capture_output=True, text=True, timeout=5, check=True)
        self.assertEqual(len(p.stdout.splitlines()), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
