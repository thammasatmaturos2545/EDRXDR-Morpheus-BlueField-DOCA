"""Synthetic tests of local journal only. No Kafka/OpenSearch or device access."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_bluefield_operator_contract as fixtures
import bluefield_operator_contract as c
import bluefield_operator_store as s


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bluefield-audit-test-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'audit.sqlite3'
        self.f = fixtures.Contracts()
        self.f.setUp()
        s.initialize(self.path)
        self.store = s.Journal(self.path, clock=lambda: self.f.now)

    def args(self, attempt='attempt01'):
        f = self.f
        return (attempt, f.plan, f.envelope, f.id, f.approval, 'fixture-operator', f.source, f.raw, 0, 3)

    def reserve(self):
        return self.store.reserve(*self.args())

    def count(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]

    def test_intent_survives_reopen_without_raw_payload(self):
        self.reserve()
        result = s.Journal(self.path).inspect('attempt01')
        self.assertTrue(result['requires_reconciliation'])
        self.assertFalse(result['retry_allowed'])
        self.assertFalse(result['transport_enabled'])
        audit = result['audit']
        self.assertEqual(audit['approval']['operator'], 'fixture-operator')
        self.assertEqual(len(audit['events']), 3)
        self.assertEqual(audit['authorization_sha256'], self.f.auth())
        self.assertNotIn(self.f.raw, self.path.read_bytes())

    def test_same_approval_cannot_be_used_twice(self):
        self.reserve()
        with self.assertRaises(c.Rejected): self.store.reserve(*self.args('attempt02'))
        self.assertEqual(self.count(), 1)

    def test_new_approval_cannot_resend_same_record_destination(self):
        self.reserve()
        self.f.approval['approval_id'] = 'another-approval'
        with self.assertRaises(c.Rejected): self.store.reserve(*self.args('attempt02'))

    def test_duplicate_approval_id_also_blocks_new_destination(self):
        self.reserve()
        self.f.plan = c.review_plan(self.f.envelope, self.f.id, 'shadow-bluefield-controlled-replay-fixture99', self.f.now)
        self.f.approval['plan_sha256'] = self.f.plan['plan_sha256']
        with self.assertRaises(c.Rejected): self.store.reserve(*self.args('attempt02'))

    def test_two_concurrent_connections_only_one_reservation(self):
        def run(number):
            try:
                s.Journal(self.path, clock=lambda: self.f.now).reserve(*self.args('attempt' + str(number)))
                return 'reserved'
            except c.Rejected:
                return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, (1, 2)))
        self.assertCountEqual(results, ['reserved', 'blocked'])
        self.assertEqual(self.count(), 1)

    def test_two_processes_share_one_reservation(self):
        workers = [subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                                     '--reserve-worker', str(self.path), 'worker' + str(i)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(2)]
        results = []
        try:
            for worker in workers:
                stdout, stderr = worker.communicate(timeout=15)
                self.assertEqual(worker.returncode, 0, stderr)
                results.append(stdout.strip())
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                    worker.communicate()
        self.assertCountEqual(results, ['reserved', 'blocked'])
        self.assertEqual(self.count(), 1)

    def test_missing_approval_or_bad_source_leaves_no_intent(self):
        for position, value in ((4, None), (7, b'wrong bytes'), (8, 2)):
            args = list(self.args())
            args[position] = value
            with self.assertRaises(c.Rejected): self.store.reserve(*args)
            self.assertEqual(self.count(), 0)

    def test_expiry_rechecked_inside_transaction(self):
        self.store.clock = lambda: self.f.now + timedelta(hours=1)
        with self.assertRaises(c.Rejected): self.reserve()
        self.assertEqual(self.count(), 0)

    def test_write_failure_rolls_back_everything(self):
        with patch.object(self.store, '_commit', side_effect=sqlite3.OperationalError('injected disk failure')):
            with self.assertRaises(s.StoreUnavailable): self.reserve()
        self.assertEqual(self.count(), 0)

    def test_ambiguous_commit_returns_error_but_blocks_retry(self):
        def uncertain(db):
            db.commit()
            raise sqlite3.OperationalError('injected post-commit failure')
        with patch.object(self.store, '_commit', side_effect=uncertain):
            with self.assertRaises(s.StoreUnavailable): self.reserve()
        self.assertEqual(self.count(), 1)
        with self.assertRaises(c.Rejected): self.store.reserve(*self.args('attempt02'))
        self.assertTrue(self.store.inspect('attempt01')['requires_reconciliation'])

    def test_ack_requires_matching_destination_and_offset(self):
        self.reserve()
        for receipt in ({'topic': 'bluefield-events', 'partition': 0, 'offset': 0},
                        {'topic': self.f.plan['destination_topic'], 'partition': 0, 'offset': True},
                        {'topic': self.f.plan['destination_topic'], 'partition': 0, 'offset': -1}):
            with self.assertRaises(c.Rejected): self.store.record_outcome('attempt01', 'acknowledged', receipt)
        self.assertEqual(self.store.inspect('attempt01')['state'], 'intent_recorded')

    def test_ack_persisted_and_terminal(self):
        self.reserve()
        receipt = {'topic': self.f.plan['destination_topic'], 'partition': 0, 'offset': 0}
        self.store.record_outcome('attempt01', 'acknowledged', receipt)
        result = self.store.inspect('attempt01')
        self.assertEqual(result['audit']['receipt'], receipt)
        self.assertFalse(result['requires_reconciliation'])
        with self.assertRaises(c.Rejected): self.store.record_outcome('attempt01', 'outcome_unknown')

    def test_unknown_outcome_cannot_be_retried_or_marked_success(self):
        self.reserve()
        self.store.record_outcome('attempt01', 'outcome_unknown')
        self.assertTrue(self.store.inspect('attempt01')['requires_reconciliation'])
        with self.assertRaises(c.Rejected): self.store.record_outcome('attempt01', 'acknowledged', {})
        with self.assertRaises(c.Rejected): self.store.reserve(*self.args('attempt02'))

    def test_outcome_audit_failure_preserves_pending_intent(self):
        self.reserve()
        with patch.object(self.store, '_commit', side_effect=sqlite3.OperationalError('injected failure')):
            with self.assertRaises(s.StoreUnavailable): self.store.record_outcome('attempt01', 'outcome_unknown')
        self.assertEqual(self.store.inspect('attempt01')['state'], 'intent_recorded')

    def test_tampered_record_fails_closed(self):
        self.reserve()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE attempts SET seal='broken'")
        with self.assertRaises(s.StoreUnavailable): self.store.inspect('attempt01')

    def test_rehashed_but_invalid_audit_chain_fails_closed(self):
        self.reserve()
        with closing(sqlite3.connect(self.path)) as db, db:
            payload = json.loads(db.execute('SELECT payload FROM attempts').fetchone()[0])
            payload['events'][1]['operator'] = 'unchecked-field'
            db.execute('UPDATE attempts SET payload=?,seal=?', (c.canonical(payload).decode(), c.digest(payload)))
        with self.assertRaises(s.StoreUnavailable): self.store.inspect('attempt01')

    def test_missing_db_does_not_auto_recreate(self):
        self.path.rename(self.path.with_suffix('.saved'))
        with self.assertRaises(s.StoreUnavailable): self.reserve()
        self.assertFalse(self.path.exists())

    def test_initialize_refuses_existing_db_without_overwrite(self):
        self.reserve()
        before = self.path.read_bytes()
        with self.assertRaises(s.StoreUnavailable): s.initialize(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_caller_mutation_does_not_change_stored_approval(self):
        self.reserve()
        self.f.approval['operator'] = 'different'
        self.assertEqual(self.store.inspect('attempt01')['audit']['approval']['operator'], 'fixture-operator')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--reserve-worker':
        f = fixtures.Contracts()
        f.setUp()
        try:
            s.Journal(sys.argv[2], clock=lambda: f.now).reserve(
                sys.argv[3], f.plan, f.envelope, f.id, f.approval, 'fixture-operator', f.source, f.raw, 0, 3)
            print('reserved')
        except c.Rejected:
            print('blocked')
    else:
        unittest.main(verbosity=2)
