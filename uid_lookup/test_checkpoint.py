import json
import tempfile
import unittest
from pathlib import Path

from uid_lookup.checkpoint import (
    load_checkpoint,
    make_plan,
    mark_complete,
)


class TestCheckpoint(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.path = Path(self.temp.name) / "checkpoint.json"
        self.plan = make_plan([
            "wazuh-alerts-4.x-2026.10.15"
        ])

    def test_new_checkpoint(self):
        state = load_checkpoint(self.path, self.plan)
        self.assertEqual(state["completed"], {})

    def test_completed_slice(self):
        state = mark_complete(
            self.path, self.plan, 0,
            scan_complete=True,
            scanned=10,
            created=10,
            verified_existing=0,
        )

        self.assertEqual(state["completed"]["0"]["scanned"], 10)
        self.assertTrue(self.path.exists())

    def test_incomplete_scan_rejected(self):
        with self.assertRaises(ValueError):
            mark_complete(
                self.path, self.plan, 0,
                scan_complete=False,
                scanned=10,
                created=10,
                verified_existing=0,
            )
        self.assertFalse(self.path.exists())

    def test_unconfirmed_count_rejected(self):
        with self.assertRaises(ValueError):
            mark_complete(
                self.path, self.plan, 0,
                scan_complete=True,
                scanned=10,
                created=9,
                verified_existing=0,
            )

    def test_plan_mismatch_rejected(self):
        mark_complete(
            self.path, self.plan, 0,
            scan_complete=True,
            scanned=10,
            created=10,
            verified_existing=0,
        )

        different = make_plan([
            "wazuh-alerts-4.x-2026.10.14"
        ])

        with self.assertRaises(ValueError):
            load_checkpoint(self.path, different)

    def test_resume_idempotent(self):
        kwargs = dict(
            scan_complete=True,
            scanned=10,
            created=8,
            verified_existing=2,
        )

        mark_complete(self.path, self.plan, 0, **kwargs)
        state = mark_complete(self.path, self.plan, 0, **kwargs)

        self.assertEqual(len(state["completed"]), 1)

        with self.assertRaises(ValueError):
            mark_complete(
                self.path, self.plan, 0,
                scan_complete=True,
                scanned=11,
                created=11,
                verified_existing=0,
            )


if __name__ == "__main__":
    unittest.main()
