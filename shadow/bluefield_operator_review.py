"""Offline Linux operator review CLI. No network client or replay command."""
import argparse
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import bluefield_operator_contract as c
import bluefield_operator_store as s

REASONS = {'needs_investigation', 'invalid_measurement', 'source_unavailable', 'not_authorized'}


def actor_check(actor):
    c.exact(actor, {'uid', 'name'}, 'invalid_actor')
    c.require(type(actor['uid']) is int and actor['uid'] > 0, 'nonroot_actor_required')
    c.token(actor['name'], c.IDENTITY, 'invalid_actor_name')


def local_actor():
    c.require(os.name == 'posix', 'linux_operator_required')
    import pwd
    c.require(os.getuid() == os.geteuid() and os.getuid() != 0, 'direct_nonroot_session_required')
    actor = {'uid': os.getuid(), 'name': pwd.getpwuid(os.getuid()).pw_name}
    actor_check(actor)
    return actor


def service_guard():
    state = subprocess.check_output(['systemctl', 'show', 'edrxdr-bluefield.service', '--no-pager',
                                     '-p', 'ActiveState', '-p', 'SubState', '-p', 'UnitFileState'],
                                    text=True, timeout=10)
    c.require(set(state.splitlines()) == {'ActiveState=inactive', 'SubState=dead', 'UnitFileState=disabled'}, 'service_state_changed')


def read_envelope(path):
    def pairs(items):
        out = {}
        for key, value in items:
            c.require(key not in out, 'duplicate_json_key')
            out[key] = value
        return out
    with Path(path).open('rb') as file:
        raw = file.read(65537)
    c.require(len(raw) <= 65536, 'envelope_too_large')
    def reject_constant(_):
        raise c.Rejected('nonfinite_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


def initialize(path, actor, clock=None):
    actor_check(actor)
    s.initialize(path)  # Explicit new database only, never migrate/replace old journals.
    book = ReviewBook(path, clock=clock)
    with book._transaction() as db:
        db.execute('CREATE TABLE reviews (plan_hash TEXT PRIMARY KEY, replay_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, seal TEXT NOT NULL)')
        db.execute('CREATE TABLE review_events (seq INTEGER PRIMARY KEY, payload TEXT NOT NULL, seal TEXT NOT NULL)')
        book._event(db, actor, 'initialized', None, 'new_private_journal')


class ReviewBook(s.Journal):
    def _events(self, db):
        count = db.execute('SELECT COUNT(*) FROM review_events').fetchone()[0]
        if count > 10000:
            raise s.StoreUnavailable('offline_audit_limit_reached')
        previous, events = None, []
        try:
            for seq, text, seal in db.execute('SELECT seq,payload,seal FROM review_events ORDER BY seq'):
                row = json.loads(text)
                c.exact(row, {'sequence', 'previous_sha256', 'time_utc', 'actor', 'action', 'plan_sha256', 'reason', 'artifact_sha256'}, 'invalid_event')
                actor_check(row['actor'])
                c.timestamp(row['time_utc'])
                c.require(seq == len(events) and row['sequence'] == seq and row['previous_sha256'] == previous and c.digest(row) == seal, 'broken_review_audit')
                previous = seal
                events.append({**row, 'event_sha256': seal})
        except (ValueError, KeyError, TypeError) as exc:
            raise s.StoreUnavailable('review_audit_corrupt') from exc
        return events

    def _event(self, db, actor, action, plan_hash, reason, artifact_hash=None):
        actor_check(actor)
        allowed = {'initialized': {'new_private_journal'}, 'reviewed': {'metadata_only_review'},
                   'approved': {'operator_confirmed'}, 'rejected': REASONS,
                   'denied': {'interactive_required', 'confirmation_failed', 'request_rejected', 'service_guard_failed'},
                   'export_intent': {'approval_artifact_requested'}, 'exported': {'approval_artifact_written'}}
        c.require(action in allowed and reason in allowed[action], 'invalid_audit_reason')
        if plan_hash is not None:
            c.token(plan_hash, c.HASH, 'invalid_plan_hash')
        if artifact_hash is not None:
            c.token(artifact_hash, c.HASH, 'invalid_artifact_hash')
        events = self._events(db)
        c.require(len(events) < 10000, 'offline_audit_limit_reached')
        now = c.now_checked(self.clock())
        if events:
            c.require(c.timestamp(events[-1]['time_utc']) <= now, 'audit_clock_reversed')
        row = {'sequence': len(events), 'previous_sha256': events[-1]['event_sha256'] if events else None,
               'time_utc': now.isoformat(), 'actor': actor, 'action': action,
               'plan_sha256': plan_hash, 'reason': reason, 'artifact_sha256': artifact_hash}
        db.execute('INSERT INTO review_events VALUES (?,?,?)', (len(events), c.canonical(row).decode(), c.digest(row)))

    def deny(self, actor, reason='request_rejected'):
        with self._transaction() as db:
            self._event(db, actor, 'denied', None, reason)

    def review(self, envelope, evidence_id, destination, actor):
        actor_check(actor)
        plan = c.review_plan(envelope, evidence_id, destination, self.clock())
        with self._transaction() as db:
            key = s._replay_key(plan)
            c.require(db.execute('SELECT 1 FROM reviews WHERE replay_key=?', (key,)).fetchone() is None, 'review_already_exists')
            data = {'plan': plan, 'envelope': envelope, 'evidence_id': evidence_id, 'reviewer': actor,
                    'state': 'pending', 'approval': None, 'decision_actor': None, 'decided_at_utc': None}
            db.execute('INSERT INTO reviews VALUES (?,?,?,?)', (plan['plan_sha256'], key, c.canonical(data).decode(), c.digest(data)))
            self._event(db, actor, 'reviewed', plan['plan_sha256'], 'metadata_only_review', c.digest(data))
        return plan

    def _review(self, db, plan_hash):
        c.token(plan_hash, c.HASH, 'invalid_plan_hash')
        events = self._events(db)
        row = db.execute('SELECT replay_key,payload,seal FROM reviews WHERE plan_hash=?', (plan_hash,)).fetchone()
        c.require(row is not None, 'review_not_found')
        try:
            data = json.loads(row[1])
            c.exact(data, {'plan', 'envelope', 'evidence_id', 'reviewer', 'state', 'approval', 'decision_actor', 'decided_at_utc'}, 'invalid_review')
            c.require(c.digest(data) == row[2] and data['plan']['plan_sha256'] == plan_hash and s._replay_key(data['plan']) == row[0], 'review_changed')
            c.validate_plan(data['plan'], data['envelope'], data['evidence_id'])
            actor_check(data['reviewer'])
            c.require(data['state'] in ('pending', 'approved', 'rejected'), 'invalid_review_state')
            if data['state'] == 'pending':
                c.require(data['approval'] is None and data['decision_actor'] is None and data['decided_at_utc'] is None, 'invalid_pending_state')
            else:
                actor_check(data['decision_actor'])
                c.timestamp(data['decided_at_utc'])
                if data['state'] == 'approved':
                    c.authorize(data['plan'], data['envelope'], data['evidence_id'], data['approval'],
                                c.timestamp(data['decided_at_utc']), data['decision_actor']['name'])
                else:
                    c.require(data['approval'] is None, 'rejected_has_approval')
            wanted = {'pending': 'reviewed', 'approved': 'approved', 'rejected': 'rejected'}[data['state']]
            c.require(any(e['plan_sha256'] == plan_hash and e['action'] == wanted and e['artifact_sha256'] == row[2] for e in events), 'review_audit_binding_missing')
        except (ValueError, KeyError, TypeError) as exc:
            raise s.StoreUnavailable('review_record_corrupt') from exc
        return data

    def inspect_review(self, plan_hash):
        with self._transaction() as db:
            return self._review(db, plan_hash)

    def decide(self, plan_hash, actor, approved, confirmed=False, ttl=600, reason='needs_investigation'):
        actor_check(actor)
        c.require(type(approved) is bool, 'invalid_decision')
        c.require(not approved or confirmed is True, 'confirmation_required')
        c.require(type(ttl) is int and 1 <= ttl <= 3600, 'invalid_ttl')
        with self._transaction() as db:
            data = self._review(db, plan_hash)
            c.require(data['state'] == 'pending', 'review_already_decided')
            now = c.now_checked(self.clock())
            c.require(c.timestamp(data['plan']['reviewed_at_utc']) <= now, 'decision_before_review')
            data.update(state='approved' if approved else 'rejected', decision_actor=actor, decided_at_utc=now.isoformat())
            if approved:
                approval = {'schema_version': 'bluefield-operator-approval-1', 'approval_id': uuid.uuid4().hex,
                            'decision': 'approve', 'operator': actor['name'], 'reason_code': 'investigate_original_record',
                            'plan_sha256': plan_hash, 'approved_at_utc': now.isoformat(),
                            'expires_at_utc': (now + timedelta(seconds=ttl)).isoformat()}
                c.authorize(data['plan'], data['envelope'], data['evidence_id'], approval, now, actor['name'])
                data['approval'] = approval
            else:
                c.require(reason in REASONS, 'invalid_rejection_reason')
            db.execute('UPDATE reviews SET payload=?,seal=? WHERE plan_hash=?', (c.canonical(data).decode(), c.digest(data), plan_hash))
            self._event(db, actor, data['state'], plan_hash, 'operator_confirmed' if approved else reason, c.digest(data))
        return data

    def export_approval(self, plan_hash, actor, path):
        # Durable export intent precedes file creation; never overwrite an artifact.
        path = s._check_path(path)
        with self._transaction() as db:
            data = self._review(db, plan_hash)
            c.require(data['state'] == 'approved' and data['decision_actor'] == actor, 'approval_owner_required')
            c.authorize(data['plan'], data['envelope'], data['evidence_id'], data['approval'], self.clock(), actor['name'])
            value = c.canonical(data['approval']) + b'\n'
            hash_value = hashlib.sha256(value).hexdigest()
            self._event(db, actor, 'export_intent', plan_hash, 'approval_artifact_requested', hash_value)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
        if os.name == 'posix':
            fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        with self._transaction() as db:
            self._event(db, actor, 'exported', plan_hash, 'approval_artifact_written', hash_value)
        return hash_value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    review = sub.add_parser('review')
    review.add_argument('--envelope', required=True, type=Path)
    review.add_argument('--evidence-id', required=True)
    review.add_argument('--destination', required=True)
    for action in ('show', 'approve', 'reject', 'export-approval'):
        action_parser = sub.add_parser(action)
        action_parser.add_argument('--plan', required=True)
        if action == 'approve': action_parser.add_argument('--ttl-seconds', type=int, default=600)
        if action == 'reject': action_parser.add_argument('--reason', choices=sorted(REASONS), required=True)
        if action == 'export-approval': action_parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    actor, book = None, None
    try:
        actor = local_actor()
        if args.command != 'init': book = ReviewBook(args.db)
        try:
            service_guard()
        except (c.Rejected, subprocess.SubprocessError, OSError):
            if book is not None: book.deny(actor, 'service_guard_failed')
            print('STOP: service_guard_failed', file=sys.stderr)
            return 1
        if args.command == 'init':
            initialize(args.db, actor)
            result = {'initialized': True, 'transport_enabled': False}
        elif args.command == 'review':
            result = book.review(read_envelope(args.envelope), args.evidence_id, args.destination, actor)
        elif args.command == 'show':
            result = book.inspect_review(args.plan)
        elif args.command == 'approve':
            data = book.inspect_review(args.plan)
            print(json.dumps({'plan': data['plan'], 'operator': actor, 'note': 'Original bytes only; approval does not make poison valid.'}, indent=2))
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                book.deny(actor, 'interactive_required')
                print('STOP: approval requires an interactive terminal', file=sys.stderr)
                return 1
            try:
                response = input('Type APPROVE ' + args.plan + ' to approve, otherwise cancel: ')
            except (EOFError, KeyboardInterrupt):
                response = ''
            if response != 'APPROVE ' + args.plan:
                book.deny(actor, 'confirmation_failed')
                print('Approval cancelled; no approval issued.', file=sys.stderr)
                return 1
            service_guard()  # Recheck after potentially long human interaction.
            result = book.decide(args.plan, actor, True, confirmed=True, ttl=args.ttl_seconds)
        elif args.command == 'reject':
            result = book.decide(args.plan, actor, False, reason=args.reason)
        else:
            result = {'approval_file_sha256': book.export_approval(args.plan, actor, args.output), 'transport_enabled': False}
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
        if book is not None and actor is not None:
            try: book.deny(actor)
            except Exception:
                print('STOP: denial_audit_unavailable', file=sys.stderr)
                return 2
        # Do not print untrusted input or arbitrary exception messages.
        print('STOP: request_rejected (' + type(exc).__name__ + ')', file=sys.stderr)
        return 1
    except s.StoreUnavailable:
        print('STOP: audit_store_unavailable; no successful operation reported', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
