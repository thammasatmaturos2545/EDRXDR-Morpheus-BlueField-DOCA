"""Synthetic offline operator workflow tests. No real approvals or service actions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stdout, redirect_stderr
from datetime import timedelta
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import bluefield_operator_contract as c
import bluefield_operator_store as s
import bluefield_operator_review as r
import test_bluefield_operator_contract as fixtures


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='operator-review-tests-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'operator.sqlite3'
        self.f = fixtures.Contracts(); self.f.setUp()
        self.actor = {'uid': 1001, 'name': 'fixture-operator'}
        self.clock = lambda: self.f.now
        r.initialize(self.db, self.actor, clock=self.clock)
        self.book = r.ReviewBook(self.db, clock=self.clock)
        self.plan = self.book.review(self.f.envelope, self.f.id, self.f.plan['destination_topic'], self.actor)
        self.hash = self.plan['plan_sha256']

    def events(self):
        with self.book._transaction() as db:
            return self.book._events(db)

    def approve(self):
        return self.book.decide(self.hash, self.actor, True, confirmed=True)

    def cli(self, *args, tty=False, confirmation=None):
        # Authentication/service guard are explicitly mocked; CLI parsing/flow are real.
        with patch.object(r, 'local_actor', return_value=self.actor), patch.object(r, 'service_guard'), \
             patch.object(r, 'ReviewBook', return_value=self.book), \
             redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()), \
             patch('sys.stdin.isatty', return_value=tty), patch.object(stdout, 'isatty', return_value=tty), \
             patch('builtins.input', return_value=confirmation):
            return r.main(['--db', str(self.db), *args])

    def test_review_is_pending_not_an_approval(self):
        data = self.book.inspect_review(self.hash)
        self.assertEqual(data['state'], 'pending'); self.assertIsNone(data['approval'])
        self.assertEqual(self.events()[-1]['action'], 'reviewed')

    def test_metadata_does_not_store_raw(self):
        self.assertNotIn(self.f.raw, self.db.read_bytes())
        self.assertNotIn('raw_event', json.dumps(self.book.inspect_review(self.hash)))

    def test_approval_and_audit_committed_together(self):
        data = self.approve()
        self.assertEqual(data['approval']['operator'], self.actor['name'])
        self.assertEqual(self.events()[-1]['artifact_sha256'], c.digest(data))
        self.assertEqual(r.ReviewBook(self.db).inspect_review(self.hash)['state'], 'approved')

    def test_explicit_confirmation_required(self):
        with self.assertRaises(c.Rejected): self.book.decide(self.hash, self.actor, True)
        self.assertEqual(self.book.inspect_review(self.hash)['state'], 'pending')

    def test_noninteractive_approval_denied_and_audited(self):
        self.assertEqual(self.cli('approve', '--plan', self.hash), 1)
        self.assertEqual(self.events()[-1]['reason'], 'interactive_required')
        self.assertIsNone(self.book.inspect_review(self.hash)['approval'])

    def test_wrong_confirmation_denied_and_audited(self):
        self.assertEqual(self.cli('approve', '--plan', self.hash, tty=True, confirmation='yes'), 1)
        self.assertEqual(self.events()[-1]['reason'], 'confirmation_failed')

    def test_exact_interactive_confirmation_issues_approval(self):
        self.assertEqual(self.cli('approve', '--plan', self.hash, tty=True, confirmation='APPROVE ' + self.hash), 0)
        self.assertEqual(self.book.inspect_review(self.hash)['state'], 'approved')

    def test_explicit_rejection_terminal_and_audited(self):
        self.assertEqual(self.cli('reject', '--plan', self.hash, '--reason', 'invalid_measurement'), 0)
        self.assertEqual(self.events()[-1]['action'], 'rejected')
        with self.assertRaises(c.Rejected): self.approve()

    def test_storage_failure_does_not_issue_approval(self):
        with patch.object(self.book, '_commit', side_effect=sqlite3.OperationalError('fault')):
            with self.assertRaises(s.StoreUnavailable): self.approve()
        self.assertEqual(self.book.inspect_review(self.hash)['state'], 'pending')
        self.assertFalse(any(e['action'] == 'approved' for e in self.events()))

    def test_ambiguous_commit_leaves_decision_no_reissue(self):
        def failure(db):
            db.commit(); raise sqlite3.OperationalError('after commit')
        with patch.object(self.book, '_commit', side_effect=failure):
            with self.assertRaises(s.StoreUnavailable): self.approve()
        self.assertEqual(self.book.inspect_review(self.hash)['state'], 'approved')
        with self.assertRaises(c.Rejected): self.approve()

    def test_concurrent_decisions_one_wins(self):
        def decide(approve):
            try:
                r.ReviewBook(self.db, clock=self.clock).decide(self.hash, self.actor, approve, confirmed=True)
                return 'decided'
            except c.Rejected: return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(decide, [True, False])), ['decided', 'blocked'])

    def test_export_requires_approval_and_owner(self):
        out = self.root / 'approval.json'
        with self.assertRaises(c.Rejected): self.book.export_approval(self.hash, self.actor, out)
        self.assertFalse(out.exists())
        self.approve()
        with self.assertRaises(c.Rejected): self.book.export_approval(self.hash, {'uid': 1002, 'name': 'other'}, out)
        self.assertFalse(out.exists())

    def test_export_hash_and_no_overwrite(self):
        self.approve(); out = self.root / 'approval.json'
        digest = self.book.export_approval(self.hash, self.actor, out)
        import hashlib
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), digest)
        before = out.read_bytes()
        with self.assertRaises(FileExistsError): self.book.export_approval(self.hash, self.actor, out)
        self.assertEqual(out.read_bytes(), before)
        self.assertTrue(any(e['action'] == 'exported' for e in self.events()))

    def test_expired_approval_cannot_export(self):
        self.approve(); self.book.clock = lambda: self.f.now + timedelta(hours=1)
        with self.assertRaises(c.Rejected): self.book.export_approval(self.hash, self.actor, self.root / 'approval.json')

    def test_failed_export_intent_does_not_create_file(self):
        self.approve(); out = self.root / 'approval.json'
        with patch.object(self.book, '_commit', side_effect=sqlite3.OperationalError('fault')):
            with self.assertRaises(s.StoreUnavailable): self.book.export_approval(self.hash, self.actor, out)
        self.assertFalse(out.exists())

    def test_invalid_input_cli_denial_is_audited(self):
        p = self.root / 'bad.json'; p.write_text('{"raw_event":"PRIVATE"}')
        self.assertEqual(self.cli('review', '--envelope', str(p), '--evidence-id', self.f.id, '--destination', self.f.plan['destination_topic']), 1)
        self.assertEqual(self.events()[-1]['action'], 'denied')
        self.assertNotIn('PRIVATE', self.db.read_bytes().decode('latin1'))

    def test_duplicate_json_keys_rejected(self):
        p = self.root / 'bad.json'; p.write_text('{"a":1,"a":2}')
        with self.assertRaises(c.Rejected): r.read_envelope(p)

    def test_duplicate_review_cannot_extend_approval(self):
        with self.assertRaises(c.Rejected):
            self.book.review(self.f.envelope, self.f.id, self.f.plan['destination_topic'], self.actor)

    def test_corrupt_audit_blocks_decision(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE review_events SET seal='bad' WHERE seq=0")
        with self.assertRaises(s.StoreUnavailable): self.approve()

    def test_service_guard_failure_is_audited(self):
        with patch.object(r, 'local_actor', return_value=self.actor), patch.object(r, 'ReviewBook', return_value=self.book), \
             patch.object(r, 'service_guard', side_effect=c.Rejected('service_state_changed')), redirect_stderr(io.StringIO()):
            self.assertEqual(r.main(['--db', str(self.db), 'show', '--plan', self.hash]), 1)
        self.assertEqual(self.events()[-1]['reason'], 'service_guard_failed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
