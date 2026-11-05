"""Private human-decision store. Stdio only; no network/model/response execution."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys

MAX_CATALOG = 512 * 1024
MAX_REQUEST = 4096
MAX_ALERTS = 20
MAX_HISTORY = 100
HASH = re.compile(r'^[a-f0-9]{64}$')
IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$')
ACTIONS = {'investigating', 'agree_recommendation', 'no_action'}
SCHEMA = '''
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE decisions (
 seq INTEGER PRIMARY KEY AUTOINCREMENT,
 request_id TEXT NOT NULL UNIQUE,
 request_hash TEXT NOT NULL,
 alert_id TEXT NOT NULL,
 alert_revision TEXT NOT NULL,
 action TEXT NOT NULL,
 reason TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 decided_at TEXT NOT NULL
);
CREATE INDEX by_alert ON decisions(alert_id, seq);
CREATE TRIGGER no_decision_update BEFORE UPDATE ON decisions
 BEGIN SELECT RAISE(ABORT, 'append only'); END;
CREATE TRIGGER no_decision_delete BEFORE DELETE ON decisions
 BEGIN SELECT RAISE(ABORT, 'append only'); END;
'''


class Rejected(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


def need(condition, code='INVALID_REQUEST', status=400):
    if not condition:
        raise Rejected(status, code)


def exact(value, keys):
    return type(value) is dict and set(value) == set(keys)


def text(value, maximum, minimum=1):
    need(type(value) is str and minimum <= len(value) <= maximum
         and value == value.strip()
         and all(ord(c) >= 32 or c == '\n' for c in value), 'INVALID_TEXT')
    return value


def timestamp(value):
    text(value, 32)
    need(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', value))
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise Rejected(400, 'INVALID_TIME')
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def parse_json(raw, status=400):
    def pairs(values):
        result = {}
        for key, value in values:
            need(key not in result, 'DUPLICATE_JSON_KEY', status)
            result[key] = value
        return result
    def constant(value):
        raise Rejected(status, 'INVALID_JSON_NUMBER')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError):
        raise Rejected(status, 'INVALID_JSON')


def validate_catalog(value):
    need(exact(value, ('schema_version', 'generated_at', 'automated_response_allowed', 'items')))
    need(value['schema_version'] == 'nexus-human-review-v1'
         and value['automated_response_allowed'] is False)
    timestamp(value['generated_at'])
    need(type(value['items']) is list and len(value['items']) <= MAX_ALERTS)
    seen, items = set(), []
    keys = ('alert_id', 'endpoint_id', 'pipeline', 'source_mode', 'event_time',
            'detected_at', 'detector_id', 'detector_version', 'feature_contract',
            'coverage_status', 'validation_status', 'score', 'score_semantics',
            'findings', 'limitations', 'evidence_refs', 'recommendation')
    for row in value['items']:
        need(exact(row, keys))
        need(type(row['alert_id']) is str and HASH.fullmatch(row['alert_id'])
             and row['alert_id'] not in seen)
        seen.add(row['alert_id'])
        need(row['endpoint_id'] == '003')
        need(row['pipeline'] in ('dfp', 'endpoint-file-behavior'))
        need(row['source_mode'] in ('shadow', 'controlled-test', 'replay'))
        need(row['coverage_status'] in ('verified', 'incomplete', 'unknown'))
        need(row['validation_status'] in ('experimental', 'validated'))
        for key in ('detector_id', 'detector_version', 'feature_contract'):
            need(type(row[key]) is str and IDENT.fullmatch(row[key]))
        timestamp(row['event_time']); timestamp(row['detected_at'])
        semantics = {'dfp': ('reconstruction-error',),
                     'endpoint-file-behavior': ('rule-count', 'classifier-score')}
        need(row['score_semantics'] in semantics[row['pipeline']])
        if row['score'] is not None:
            score = row['score']
            need(type(score) in (int, float) and 0 <= score < float('inf'))
            if row['score_semantics'] == 'classifier-score':
                need(score <= 1)
        for key in ('findings', 'limitations'):
            need(type(row[key]) is list and 1 <= len(row[key]) <= 8)
            for item in row[key]: text(item, 500)
        refs = row['evidence_refs']
        need(type(refs) is list and 1 <= len(refs) <= 8)
        for ref in refs:
            need(exact(ref, ('event_uid', 'sha256')))
            need(all(type(ref[k]) is str and HASH.fullmatch(ref[k]) for k in ref))
        recommendation = row['recommendation']
        need(exact(recommendation, ('action', 'reason')))
        need(recommendation['action'] in ('investigate', 'consider_endpoint_isolation'))
        text(recommendation['reason'], 500)
        if recommendation['action'] != 'investigate':
            need(row['validation_status'] == 'validated'
                 and row['coverage_status'] == 'verified'
                 and row['source_mode'] != 'replay', 'UNSUPPORTED_CONTAINMENT_RECOMMENDATION')
        # Revision covers every displayed fact, recommendation and evidence reference.
        items.append(dict(row, alert_revision=digest(row)))
    return dict(value, items=items, response_execution_enabled=False)


def private_info(info, directory, uid):
    need((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
         and info.st_uid == uid and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
         and (directory or info.st_nlink == 1), 'PRIVATE_STORAGE_UNAVAILABLE', 503)


def check_root(root):
    need(hasattr(os, 'getuid') and root.is_absolute() and root.resolve() == root,
         'PRIVATE_STORAGE_UNAVAILABLE', 503)
    private_info(root.lstat(), True, os.getuid())
    parent = root.parent.stat()
    need(parent.st_uid == os.getuid() and not (parent.st_mode & 0o022),
         'PRIVATE_STORAGE_UNAVAILABLE', 503)


def secure_read(root, name, maximum):
    check_root(root)
    path = root / name
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        private_info(before, False, os.getuid())
        need(before.st_size <= maximum, 'PRIVATE_FILE_LIMIT', 503)
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        need(len(raw) <= maximum and
             (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
             'PRIVATE_FILE_CHANGED', 503)
        return raw


def principal(header, registry, write):
    # This is a separate named-reviewer registry, not the shared preview credential.
    need(exact(registry, ('schema_version', 'users'))
         and registry['schema_version'] == 'nexus-reviewers-v1'
         and type(registry['users']) is list and 1 <= len(registry['users']) <= 32,
         'REVIEW_AUTH_UNAVAILABLE', 503)
    seen_login, seen_actor = set(), set()
    for user in registry['users']:
        need(exact(user, ('login', 'actor_ref', 'role', 'salt', 'scrypt_sha256')),
             'REVIEW_AUTH_UNAVAILABLE', 503)
        need(type(user['login']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,48}', user['login'])
             and type(user['actor_ref']) is str and IDENT.fullmatch(user['actor_ref'])
             and user['role'] in ('viewer', 'reviewer')
             and type(user['salt']) is str and re.fullmatch('[a-f0-9]{32}', user['salt'])
             and type(user['scrypt_sha256']) is str and re.fullmatch('[a-f0-9]{128}', user['scrypt_sha256'])
             and user['login'] not in seen_login and user['actor_ref'] not in seen_actor,
             'REVIEW_AUTH_UNAVAILABLE', 503)
        seen_login.add(user['login']); seen_actor.add(user['actor_ref'])
    need(type(header) is str and len(header) <= 512
         and re.fullmatch(r'Basic [A-Za-z0-9+/]+={0,2}', header), 'AUTH_REQUIRED', 401)
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode('utf-8')
        login, password = decoded.split(':', 1)
    except (ValueError, UnicodeError):
        raise Rejected(401, 'AUTH_REQUIRED')
    need(16 <= len(password) <= 128, 'AUTH_REQUIRED', 401)
    user = next((user for user in registry['users'] if user['login'] == login), None)
    # A fixed-cost dummy computation avoids skipping the expensive check for unknown logins.
    salt = bytes.fromhex(user['salt']) if user else bytes(16)
    candidate = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
    expected = bytes.fromhex(user['scrypt_sha256']) if user else bytes(64)
    need(hmac.compare_digest(candidate, expected) and user is not None, 'AUTH_REQUIRED', 401)
    need(not write or user['role'] == 'reviewer', 'REVIEW_ROLE_REQUIRED', 403)
    return {'actor_ref': user['actor_ref'], 'role': user['role']}


def connect(root, write=False):
    check_root(root)
    path = root / 'decisions.sqlite3'
    private_info(path.lstat(), False, os.getuid())
    need(path.stat().st_size <= 64 * 1024 * 1024, 'DECISION_STORE_LIMIT', 503)
    for suffix in ('-journal', '-wal', '-shm'):
        sibling = root / ('decisions.sqlite3' + suffix)
        if os.path.lexists(sibling): private_info(sibling.lstat(), False, os.getuid())
    connection = sqlite3.connect(path.as_uri() + ('?mode=rw' if write else '?mode=ro'),
                                 uri=True, timeout=1)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA trusted_schema=OFF')
    if write: connection.execute('PRAGMA synchronous=FULL')
    return connection


def check_store(connection, catalog_sha):
    rows = dict(connection.execute('SELECT key, value FROM metadata'))
    need(rows == {'schema_version': 'nexus-decision-store-v1', 'catalog_sha256': catalog_sha},
         'STORE_CATALOG_MISMATCH', 503)


def records(connection, alert_id):
    count = connection.execute('SELECT COUNT(*) FROM decisions WHERE alert_id=?', (alert_id,)).fetchone()[0]
    need(count <= MAX_HISTORY, 'ALERT_HISTORY_LIMIT', 503)
    return [dict(row) for row in connection.execute(
        'SELECT seq, request_id, alert_id, alert_revision, action, reason, actor_ref, decided_at '
        'FROM decisions WHERE alert_id=? ORDER BY seq', (alert_id,))]


def decision(connection, body, actor, catalog, now):
    need(exact(body, ('request_id', 'alert_id', 'alert_revision', 'expected_seq', 'action', 'reason')))
    need(type(body['request_id']) is str and re.fullmatch(
        '[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}', body['request_id']))
    need(type(body['alert_id']) is str and HASH.fullmatch(body['alert_id']))
    need(type(body['alert_revision']) is str and HASH.fullmatch(body['alert_revision']))
    need(type(body['expected_seq']) is int and 0 <= body['expected_seq'] <= 2**53 - 1)
    need(body['action'] in ACTIONS)
    text(body['reason'], 500)
    row = next((row for row in catalog['items'] if row['alert_id'] == body['alert_id']), None)
    need(row is not None, 'ALERT_NOT_FOUND', 404)
    need(row['alert_revision'] == body['alert_revision'], 'ALERT_REVISION_CHANGED', 409)
    request_hash = digest(dict(body, actor_ref=actor['actor_ref']))
    previous = connection.execute('SELECT * FROM decisions WHERE request_id=?', (body['request_id'],)).fetchone()
    if previous:
        need(previous['request_hash'] == request_hash, 'IDEMPOTENCY_CONFLICT', 409)
        return {'replayed': True, 'decision': {k: previous[k] for k in previous.keys() if k != 'request_hash'}}
    latest = connection.execute('SELECT COALESCE(MAX(seq),0) FROM decisions WHERE alert_id=?',
                                 (body['alert_id'],)).fetchone()[0]
    need(latest == body['expected_seq'], 'DECISION_CHANGED_RELOAD_REQUIRED', 409)
    need(connection.execute('SELECT COUNT(*) FROM decisions WHERE alert_id=?',
                            (body['alert_id'],)).fetchone()[0] < MAX_HISTORY, 'ALERT_HISTORY_LIMIT', 409)
    values = (body['request_id'], request_hash, body['alert_id'], body['alert_revision'],
              body['action'], body['reason'], actor['actor_ref'], now)
    cursor = connection.execute('INSERT INTO decisions '
        '(request_id, request_hash, alert_id, alert_revision, action, reason, actor_ref, decided_at) '
        'VALUES (?,?,?,?,?,?,?,?)', values)
    result = connection.execute('SELECT * FROM decisions WHERE seq=?', (cursor.lastrowid,)).fetchone()
    return {'replayed': False, 'decision': {k: result[k] for k in result.keys() if k != 'request_hash'}}


def handle(request, root, catalog_sha):
    need(exact(request, ('method', 'authorization', 'body')))
    need(request['method'] in ('GET', 'POST'))
    need(type(catalog_sha) is str and HASH.fullmatch(catalog_sha), 'CATALOG_NOT_PINNED', 503)
    write = request['method'] == 'POST'
    registry = parse_json(secure_read(root, 'reviewers.json', 32 * 1024), 503)
    actor = principal(request['authorization'], registry, write)
    raw = secure_read(root, 'catalog-' + catalog_sha + '.json', MAX_CATALOG)
    need(hashlib.sha256(raw).hexdigest() == catalog_sha, 'CATALOG_HASH_MISMATCH', 503)
    try:
        catalog = validate_catalog(parse_json(raw, 503))
    except Rejected:
        raise Rejected(503, 'INVALID_CATALOG')
    connection = connect(root, write)
    try:
        if write:
            connection.execute('BEGIN IMMEDIATE')
        check_store(connection, catalog_sha)
        if write:
            result = decision(connection, request['body'], actor, catalog,
                              datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
            connection.commit()
            return {'status': 200, 'body': dict(result, response_executed=False)}
        need(request['body'] is None)
        connection.execute('BEGIN')
        items = []
        for row in catalog['items']:
            history = records(connection, row['alert_id'])
            items.append(dict(row, history=history, latest_seq=history[-1]['seq'] if history else 0))
        return {'status': 200, 'body': dict(catalog, items=items, principal=actor,
                                          catalog_sha256=catalog_sha)}
    finally:
        connection.close()  # Includes rollback on rejected/failed writes.


def initialize(root, catalog_sha):
    """Explicit offline provisioning only; never called by the HTTP endpoint."""
    check_root(root)
    need(HASH.fullmatch(catalog_sha), 'CATALOG_NOT_PINNED', 503)
    raw = secure_read(root, 'catalog-' + catalog_sha + '.json', MAX_CATALOG)
    need(hashlib.sha256(raw).hexdigest() == catalog_sha, 'CATALOG_HASH_MISMATCH', 503)
    validate_catalog(parse_json(raw, 503))
    database = root / 'decisions.sqlite3'
    fd = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    connection = sqlite3.connect(database)
    try:
        connection.execute('PRAGMA synchronous=FULL')
        connection.executescript(SCHEMA)
        connection.executemany('INSERT INTO metadata VALUES (?,?)', (
            ('schema_version', 'nexus-decision-store-v1'), ('catalog_sha256', catalog_sha)))
        connection.commit()
    finally:
        connection.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--catalog-sha256', required=True)
    parser.add_argument('--initialize', action='store_true')
    args = parser.parse_args()
    try:
        if args.initialize:
            initialize(Path(args.root), args.catalog_sha256)
            result = {'status': 200, 'body': {'initialized': True, 'response_executed': False}}
        else:
            raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
            need(len(raw) <= MAX_REQUEST, 'REQUEST_LIMIT', 413)
            result = handle(parse_json(raw), Path(args.root), args.catalog_sha256)
    except Rejected as exc:
        result = {'status': exc.status, 'body': {'error': exc.code}}
    except Exception:
        result = {'status': 503, 'body': {'error': 'DECISION_REVIEW_UNAVAILABLE'}}
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
