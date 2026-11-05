"""Synthetic contracts, named auth, and real SQLite transactions; no VM/private IO."""
import base64
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('decision_review', BASE / 'server/decision_review.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    return {'schema_version': 'nexus-human-review-v1', 'generated_at': '2026-11-05T04:00:00Z',
            'automated_response_allowed': False, 'items': [{
        'alert_id': 'a' * 64, 'endpoint_id': '003', 'pipeline': 'dfp',
        'source_mode': 'controlled-test', 'event_time': '2026-11-05T03:00:00Z',
        'detected_at': '2026-11-05T03:01:00Z', 'detector_id': 'synthetic-dfp',
        'detector_version': 'test-only', 'feature_contract': 'synthetic-six-counts',
        'coverage_status': 'unknown', 'validation_status': 'experimental', 'score': 0,
        'score_semantics': 'reconstruction-error', 'findings': ['Synthetic finding <script>'],
        'limitations': ['Synthetic test; no detection quality claim'],
        'evidence_refs': [{'event_uid': 'b' * 64, 'sha256': 'c' * 64}],
        'recommendation': {'action': 'investigate', 'reason': 'Review synthetic evidence'},
    }]}


def registry(role='reviewer'):
    salt = bytes(range(16))
    password = 'synthetic-not-a-real-password'
    return {'schema_version': 'nexus-reviewers-v1', 'users': [{
        'login': 'test-reviewer', 'actor_ref': 'synthetic-actor', 'role': role,
        'salt': salt.hex(), 'scrypt_sha256': hashlib.scrypt(
            password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64).hex()}]}


def auth(login='test-reviewer', password='synthetic-not-a-real-password'):
    return 'Basic ' + base64.b64encode((login + ':' + password).encode()).decode()


class Tests(unittest.TestCase):
    def test_duplicate_json_keys_and_nonfinite_json_rejected(self):
        for raw in ('{"action":"investigating","action":"no_action"}', '{"score":NaN}', '{'):
            with self.assertRaises(m.Rejected): m.parse_json(raw)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='decision-test-', dir=BASE / 'tests')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'decisions.sqlite3'
        self.catalog = m.validate_catalog(fixture())
        self.raw = json.dumps(fixture()).encode()
        self.sha = hashlib.sha256(self.raw).hexdigest()
        with self.session() as db:
            db.executescript(m.SCHEMA)
            db.executemany('INSERT INTO metadata VALUES (?,?)', (
                ('schema_version', 'nexus-decision-store-v1'), ('catalog_sha256', self.sha)))

    def connection(self):
        db = sqlite3.connect(self.db, timeout=2)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def session(self):
        db = self.connection()
        try:
            with db:
                yield db
        finally:
            db.close()

    def body(self, **changes):
        value = dict(request_id='11111111-1111-4111-8111-111111111111', alert_id='a' * 64,
                     alert_revision=self.catalog['items'][0]['alert_revision'], expected_seq=0,
                     action='agree_recommendation', reason='Synthetic review reason')
        return dict(value, **changes)

    def save(self, body=None, actor='synthetic-actor'):
        with self.session() as db:
            db.execute('BEGIN IMMEDIATE')
            return m.decision(db, body or self.body(), {'actor_ref': actor}, self.catalog,
                              '2026-11-05T04:00:00Z')

    def test_catalog_revisions_cover_evidence_and_recommendations_without_mutation(self):
        value = fixture(); original = deepcopy(value)
        result = m.validate_catalog(value)
        self.assertEqual(value, original)
        self.assertEqual(result['items'][0]['score'], 0)
        self.assertFalse(result['response_execution_enabled'])
        value['items'][0]['recommendation']['reason'] = 'Changed recommendation'
        self.assertNotEqual(m.validate_catalog(value)['items'][0]['alert_revision'],
                            result['items'][0]['alert_revision'])

    def test_catalog_rejects_fabricated_scope_scores_raw_fields_and_response_flags(self):
        changes = [lambda x: x.update(automated_response_allowed=True),
            lambda x: x['items'][0].update(endpoint_id='004'),
            lambda x: x['items'][0].update(score=True),
            lambda x: x['items'][0].update(score=float('nan')),
            lambda x: x['items'][0].update(score=float('inf')),
            lambda x: x['items'][0].update(full_log='not exported'),
            lambda x: x['items'][0].update(event_time='2026-02-30T00:00:00Z'),
            lambda x: x['items'][0].update(source_mode='live'),
            lambda x: x['items'].append(deepcopy(x['items'][0]))]
        for change in changes:
            value = fixture(); change(value)
            with self.assertRaises(m.Rejected): m.validate_catalog(value)

    def test_unvalidated_or_replay_cannot_recommend_isolation(self):
        value = fixture(); row = value['items'][0]
        row['recommendation']['action'] = 'consider_endpoint_isolation'
        with self.assertRaises(m.Rejected): m.validate_catalog(value)
        row.update(validation_status='validated', coverage_status='verified')
        m.validate_catalog(value)
        row['source_mode'] = 'replay'
        with self.assertRaises(m.Rejected): m.validate_catalog(value)

    def test_named_auth_and_viewer_cannot_write(self):
        self.assertEqual(m.principal(auth(), registry(), True)['actor_ref'], 'synthetic-actor')
        for header in ('', 'Basic !!!', auth(password='wrong-password-xxxx'), auth(login='unknown')):
            with self.assertRaises(m.Rejected) as error: m.principal(header, registry(), True)
            self.assertEqual(error.exception.status, 401)
        with self.assertRaises(m.Rejected) as error: m.principal(auth(), registry('viewer'), True)
        self.assertEqual(error.exception.status, 403)

    def test_duplicate_registry_identity_rejected(self):
        users = registry(); users['users'].append(deepcopy(users['users'][0]))
        with self.assertRaises(m.Rejected) as error: m.principal(auth(), users, True)
        self.assertEqual(error.exception.status, 503)

    def test_restart_persistence_and_idempotent_retry(self):
        first = self.save(); second = self.save()
        self.assertFalse(first['replayed']); self.assertTrue(second['replayed'])
        self.assertEqual(first['decision'], second['decision'])
        with self.session() as db:
            self.assertEqual(len(m.records(db, 'a' * 64)), 1)

    def test_other_actor_or_changed_idempotent_payload_conflicts(self):
        self.save()
        for body, actor in [(self.body(reason='changed'), 'synthetic-actor'),
                            (self.body(), 'different-actor')]:
            with self.assertRaises(m.Rejected) as error: self.save(body, actor)
            self.assertEqual(error.exception.status, 409)

    def test_stale_revision_sequence_and_spoofed_actor_rejected(self):
        for body in (self.body(alert_revision='f' * 64), self.body(expected_seq=True),
                     self.body(actor_ref='forged'), self.body(execute=True),
                     self.body(reason=''), self.body(action='block')):
            with self.assertRaises(m.Rejected): self.save(body)
        self.save()
        with self.assertRaises(m.Rejected) as error:
            self.save(self.body(request_id='22222222-2222-4222-8222-222222222222'))
        self.assertEqual(error.exception.code, 'DECISION_CHANGED_RELOAD_REQUIRED')

    def test_concurrent_decisions_only_one_expected_sequence_wins(self):
        def submit(number):
            body = self.body(request_id=str(number) * 8 + '-1111-4111-8111-' + str(number) * 12)
            try:
                self.save(body); return 200
            except m.Rejected as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(submit, [1, 2])), [200, 409])
        with self.session() as db: self.assertEqual(len(m.records(db, 'a' * 64)), 1)

    def test_append_only_history_and_plain_text_sql_payload(self):
        reason = "<script>alert(1)</script>'; DROP TABLE decisions; --"
        self.save(self.body(reason=reason))
        with self.session() as db:
            self.assertEqual(m.records(db, 'a' * 64)[0]['reason'], reason)
            with self.assertRaises(sqlite3.IntegrityError): db.execute('DELETE FROM decisions')
            with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE decisions SET reason='x'")

    def test_private_permissions_owner_links_and_symlinks(self):
        valid = dict(st_mode=stat.S_IFREG | 0o600, st_uid=1000, st_nlink=1)
        m.private_info(SimpleNamespace(**valid), False, 1000)
        for change in ({'st_mode': stat.S_IFREG | 0o644}, {'st_uid': 0},
                       {'st_nlink': 2}, {'st_mode': stat.S_IFLNK | 0o600}):
            with self.assertRaises(m.Rejected):
                m.private_info(SimpleNamespace(**dict(valid, **change)), False, 1000)

    def test_auth_failure_does_not_open_database_or_catalog(self):
        reads = []
        def read(root, name, maximum):
            reads.append(name); return json.dumps(registry()).encode()
        with patch.object(m, 'secure_read', side_effect=read), patch.object(m, 'connect') as opened:
            with self.assertRaises(m.Rejected):
                m.handle(dict(method='GET', authorization='', body=None), self.root, self.sha)
            opened.assert_not_called()
        self.assertEqual(reads, ['reviewers.json'])

    def test_full_handle_returns_server_actor_and_no_response_execution(self):
        users = json.dumps(registry()).encode()
        def read(root, name, maximum): return users if name == 'reviewers.json' else self.raw
        with patch.object(m, 'secure_read', side_effect=read), \
                patch.object(m, 'connect', side_effect=lambda root, write: self.connection()):
            result = m.handle(dict(method='POST', authorization=auth(), body=self.body()), self.root, self.sha)
            self.assertFalse(result['body']['response_executed'])
            result = m.handle(dict(method='GET', authorization=auth(), body=None), self.root, self.sha)
        self.assertEqual(result['body']['items'][0]['history'][0]['actor_ref'], 'synthetic-actor')
        self.assertNotIn('password', json.dumps(result))
        self.assertNotIn('scrypt_sha256', json.dumps(result))

    def test_wrong_catalog_pin_and_store_pin_fail_closed(self):
        users = json.dumps(registry()).encode()
        with patch.object(m, 'secure_read', side_effect=lambda root, name, maximum:
                          users if name == 'reviewers.json' else self.raw), patch.object(m, 'connect') as opened:
            with self.assertRaises(m.Rejected):
                m.handle(dict(method='GET', authorization=auth(), body=None), self.root, 'f' * 64)
            opened.assert_not_called()
        with self.session() as db:
            with self.assertRaises(m.Rejected): m.check_store(db, 'f' * 64)

    @unittest.skipUnless(hasattr(os, 'getuid'), 'Actual POSIX permissions require the VM')
    def test_actual_private_files_auth_and_sqlite_end_to_end(self):
        self.root.chmod(0o700); self.db.chmod(0o600)
        for name, raw in [('reviewers.json', json.dumps(registry()).encode()),
                          ('catalog-' + self.sha + '.json', self.raw)]:
            target = self.root / name
            with target.open('xb') as stream: stream.write(raw)
            target.chmod(0o600)
        before = self.db.read_bytes()
        result = m.handle(dict(method='GET', authorization=auth(), body=None), self.root, self.sha)
        self.assertEqual(result['status'], 200)
        self.assertEqual(self.db.read_bytes(), before)
        result = m.handle(dict(method='POST', authorization=auth(), body=self.body()), self.root, self.sha)
        self.assertEqual(result['status'], 200)
        self.assertFalse(result['body']['response_executed'])

    @unittest.skipUnless(hasattr(os, 'getuid'), 'Actual no-follow permissions require the VM')
    def test_actual_symlink_and_public_mode_denied(self):
        self.root.chmod(0o700)
        target = self.root / 'synthetic-private.json'
        target.write_bytes(b'{}'); target.chmod(0o600)
        link = self.root / 'reviewers.json'
        link.symlink_to(target)
        with self.assertRaises(OSError): m.secure_read(self.root, 'reviewers.json', 100)
        link.unlink()
        target.chmod(0o644)
        with self.assertRaises(m.Rejected): m.secure_read(self.root, target.name, 100)


if __name__ == '__main__':
    unittest.main(verbosity=2)
