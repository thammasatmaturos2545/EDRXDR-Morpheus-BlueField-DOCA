"""Local SQLite audit journal for offline review tests. No transport or approval issuer.

Only use a trusted, private directory on a local filesystem. One canonical journal
per deployment is required; copying/recreating journals defeats deduplication.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import stat

import bluefield_operator_contract as c


class StoreUnavailable(RuntimeError):
    pass


def _check_path(path):
    path = Path(os.path.abspath(path))
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise StoreUnavailable('symlink_path_forbidden')
    if not path.parent.is_dir():
        raise StoreUnavailable('private_parent_required')
    if os.name == 'posix':
        mode = path.parent.stat()
        if mode.st_uid != os.getuid() or mode.st_mode & 0o077:
            raise StoreUnavailable('parent_must_be_owned_and_private')
    return path


def initialize(path):
    """Explicit new-journal creation only. Never silently replace an existing DB."""
    path = _check_path(path)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        db = sqlite3.connect(path, timeout=5, isolation_level=None)
        try:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE attempts (attempt_id TEXT PRIMARY KEY, approval_id TEXT UNIQUE NOT NULL, replay_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, seal TEXT NOT NULL)')
            db.execute('PRAGMA user_version=1')
            db.commit()
        finally:
            db.close()
        if os.name == 'posix':
            fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    except (OSError, sqlite3.Error) as exc:
        # Retain any failed/partial DB for inspection. Do not recreate or retry.
        raise StoreUnavailable('journal_initialization_failed') from exc


def _replay_key(plan):
    return c.digest({k: plan[k] for k in ('source', 'input_sha256', 'destination_topic')})


class Journal:
    def __init__(self, path, clock=None):
        self.path = _check_path(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @contextmanager
    def _transaction(self):
        db = None
        try:
            info = self.path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise StoreUnavailable('regular_journal_required')
            if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
                raise StoreUnavailable('journal_must_be_owned_and_private')
            # mode=rw refuses to create a new journal if the original is missing.
            db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5, isolation_level=None)
            db.execute('PRAGMA synchronous=FULL')
            if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete' or db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise StoreUnavailable('unexpected_journal_configuration')
            db.execute('BEGIN IMMEDIATE')
            if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise StoreUnavailable('journal_integrity_failed')
            yield db
            self._commit(db)
        except (OSError, sqlite3.Error) as exc:
            raise StoreUnavailable('audit_storage_failed_no_send_authorized') from exc
        finally:
            if db is not None:
                if db.in_transaction:
                    db.rollback()
                db.close()

    def _commit(self, db):
        db.commit()

    def reserve(self, attempt_id, plan, envelope, evidence_id, approval,
                trusted_operator, actual_source, raw, low, high):
        """Atomically consume approval and persist intent. Never sends a message.

        The future transport must obtain raw/coordinates/watermarks from the
        original broker. This offline API cannot prove the origin of supplied bytes.
        """
        c.token(attempt_id, c.IDENTITY, 'invalid_attempt_id')
        # Snapshot caller-owned data so changes cannot alter a recorded approval.
        plan, envelope, approval = deepcopy((plan, envelope, approval))
        actual_source = deepcopy(actual_source)
        with self._transaction() as db:
            now = c.now_checked(self.clock())  # Check expiry AFTER acquiring lock.
            authorization = c.authorize(plan, envelope, evidence_id, approval, now, trusted_operator)
            c.verify_source(plan, actual_source, raw, low, high)
            key = _replay_key(plan)
            if db.execute('SELECT 1 FROM attempts WHERE attempt_id=? OR approval_id=? OR replay_key=?',
                          (attempt_id, approval['approval_id'], key)).fetchone():
                raise c.Rejected('attempt_approval_or_replay_already_reserved')
            events = []
            for state, reason in (('reviewed', 'review_created'), ('approved', 'operator_approved'),
                                  ('intent_recorded', 'verified_original_bytes')):
                events.append(c.audit_event(events[-1] if events else None, attempt_id,
                                            plan['plan_sha256'], state, reason, now))
            payload = {'plan': plan, 'envelope': envelope, 'evidence_id': evidence_id,
                       'approval': approval, 'trusted_operator': trusted_operator,
                       'authorization_sha256': authorization, 'events': events, 'receipt': None}
            db.execute('INSERT INTO attempts VALUES (?, ?, ?, ?, ?)',
                       (attempt_id, approval['approval_id'], key, c.canonical(payload).decode(), c.digest(payload)))
        return {'attempt_id': attempt_id, 'state': 'intent_recorded', 'transport_enabled': False}

    def _load(self, db, attempt_id):
        row = db.execute('SELECT approval_id,replay_key,payload,seal FROM attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
        c.require(row is not None, 'attempt_not_found')
        try:
            payload = json.loads(row[2])
            c.exact(payload, {'plan', 'envelope', 'evidence_id', 'approval', 'trusted_operator',
                              'authorization_sha256', 'events', 'receipt'}, 'corrupt_audit_fields')
            c.require(c.digest(payload) == row[3], 'corrupt_audit_seal')
            events, plan, approval = payload['events'], payload['plan'], payload['approval']
            c.require(type(events) is list and len(events) in (3, 4), 'corrupt_audit_length')
            c.require([e['state'] for e in events[:3]] == ['reviewed', 'approved', 'intent_recorded'], 'corrupt_audit_sequence')
            previous = None
            for event in events:
                expected = c.audit_event(previous, attempt_id, plan['plan_sha256'], event['state'],
                                         event['reason_code'], c.timestamp(event['time_utc']))
                c.require(c.canonical(event) == c.canonical(expected), 'corrupt_audit_chain')
                previous = event
            auth = c.authorize(plan, payload['envelope'], payload['evidence_id'], approval,
                               c.timestamp(events[2]['time_utc']), payload['trusted_operator'])
            c.require(auth == payload['authorization_sha256'] and approval['approval_id'] == row[0] and
                      _replay_key(plan) == row[1], 'corrupt_approval_binding')
            if events[-1]['state'] == 'acknowledged':
                self._receipt(plan, payload['receipt'])
            else:
                c.require(payload['receipt'] is None, 'unexpected_receipt')
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise StoreUnavailable('audit_record_corrupt') from exc
        return payload

    @staticmethod
    def _receipt(plan, receipt):
        c.exact(receipt, {'topic', 'partition', 'offset'}, 'invalid_receipt')
        c.require(receipt['topic'] == plan['destination_topic'], 'receipt_destination_mismatch')
        c.require(type(receipt['partition']) is int and receipt['partition'] == 0 and
                  type(receipt['offset']) is int and 0 <= receipt['offset'] <= 2**63 - 1, 'invalid_receipt_position')

    def record_outcome(self, attempt_id, outcome, receipt=None):
        c.require(outcome in ('acknowledged', 'outcome_unknown'), 'invalid_outcome')
        receipt = deepcopy(receipt)
        with self._transaction() as db:
            payload = self._load(db, attempt_id)
            events = payload['events']
            c.require(events[-1]['state'] == 'intent_recorded', 'terminal_attempt_cannot_retry')
            if outcome == 'acknowledged':
                self._receipt(payload['plan'], receipt)
            else:
                c.require(receipt is None, 'unknown_outcome_has_no_receipt')
            reason = 'destination_ack' if outcome == 'acknowledged' else 'delivery_or_audit_uncertain'
            events.append(c.audit_event(events[-1], attempt_id, payload['plan']['plan_sha256'],
                                        outcome, reason, self.clock()))
            payload['receipt'] = receipt
            db.execute('UPDATE attempts SET payload=?,seal=? WHERE attempt_id=?',
                       (c.canonical(payload).decode(), c.digest(payload), attempt_id))

    def inspect(self, attempt_id):
        with self._transaction() as db:
            result = self._load(db, attempt_id)
        state = result['events'][-1]['state']
        return {'state': state, 'requires_reconciliation': state in ('intent_recorded', 'outcome_unknown'),
                'retry_allowed': False, 'transport_enabled': False, 'audit': result}
