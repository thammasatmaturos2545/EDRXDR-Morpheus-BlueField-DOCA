"""Start only the approved empty-catalog named-review preview, bounded to1hour."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, hashlib, json, os, secrets, shlex, socket, subprocess
import sys, time, urllib.request, urllib.error

ROOT = Path('/mnt/nexus-copilot-mQTssj/human-review-preview-prepared-7bnf620l')
PRODUCTION = 'nexus-all-events-prod-3006.service'
UNIT = 'nexus-human-review-preview-7bnf620l.service'

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=25)
    need(result.returncode == 0, 'Scoped service command failed')
    return result.stdout.strip()

def show(unit, key):
    return command(['systemctl', '--user', 'show', unit, '-p', key, '--value'])

def production():
    return {key: show(PRODUCTION, key)
            for key in ('ActiveState', 'SubState', 'MainPID', 'WorkingDirectory')}

def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(info.st_uid == os.getuid() and info.st_nlink == 1
             and info.st_mode & 0o777 == 0o600 and info.st_size <= 1048576,
             'Private artifact metadata mismatch')
        raw = stream.read(1048577)
        need(len(raw) <= 1048576, 'Private artifact byte bound')
        return raw

def save(path, value):
    temporary = path.with_suffix('.pending')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)

def load():
    need(os.geteuid() != 0, 'Run without sudo')
    need(ROOT.resolve() == ROOT and not ROOT.is_symlink()
         and ROOT.stat().st_uid == os.getuid()
         and ROOT.stat().st_mode & 0o777 == 0o700, 'Preparation root scope')
    plan = json.loads(read(ROOT/'preview-plan-private.json'))
    need(plan['schema_version'] == 'named-review-empty-preview-plan-1'
         and plan['frontend'] == str(ROOT/'frontend')
         and plan['private_root'] == str(ROOT/'private-review')
         and plan['port'] == 3013 and plan['host'] == '127.0.0.1'
         and plan['maximum_seconds'] == 3600 and plan['catalog_items'] == 0
         and plan['preview_started'] is False, 'Preview plan scope mismatch')
    need(hashlib.sha256(read(ROOT/'private-review/reviewers.json')).hexdigest()
         == plan['registry_sha256_private'], 'Staged registry changed')
    raw = read(ROOT/'private-review'/('catalog-'+plan['catalog_sha256']+'.json'))
    catalog = json.loads(raw)
    need(hashlib.sha256(raw).hexdigest() == plan['catalog_sha256']
         and catalog['items'] == [] and catalog['automated_response_allowed'] is False,
         'Expected pinned empty catalog')
    need(hashlib.sha256((ROOT/'frontend/.next/BUILD_ID').read_bytes()).hexdigest()
         == plan['build_id_sha256'], 'Built release identity changed')
    return plan

def http(port, path, post=False, text=False):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f'http://127.0.0.1:{port}'+path, data=b'{}' if post else None,
        headers={'Content-Type': 'application/json'} if post else {})
    try:
        with opener.open(request, timeout=5) as response:
            raw = response.read(65537) if text else b''
            need(len(raw) <= 65536, 'HTTP body bound')
            return response.status, dict(response.headers), raw
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), b''

def stop_owned(plan, token):
    result = subprocess.run(
        ['systemctl', '--user', 'show', UNIT, '-p', 'LoadState', '--value'],
        capture_output=True, text=True, timeout=15)
    if result.stdout.strip() in ('', 'not-found'):
        return False
    need(show(UNIT, 'WorkingDirectory') == plan['frontend'], 'Preview ownership directory mismatch')
    values = shlex.split(show(UNIT, 'Environment'))
    need('NEXUS_PREVIEW_OWNER='+token in values, 'Preview ownership token mismatch')
    command(['systemctl', '--user', 'stop', UNIT])
    return True

def check_port():
    with socket.socket() as sock:
        need(sock.connect_ex(('127.0.0.1', 3013)) != 0, 'Port3013 occupied')

def node_and_path(plan):
    pid = plan['production_before']['MainPID']
    need(str(Path('/proc/'+pid+'/exe').resolve(strict=True)) == plan['node'],
         'Node identity differs from production')
    runtime_path = None
    for part in Path('/proc/'+pid+'/environ').read_bytes().split(bytes([0])):
        if part.startswith(b'PATH='):
            runtime_path = part.split(b'=', 1)[1].decode()
    need(runtime_path and '\n' not in runtime_path, 'Runtime PATH unavailable')
    return runtime_path

def start(plan):
    need(not (ROOT/'launch-attempt-private.json').exists(), 'Launch attempt exists; no retry')
    need(production() == plan['production_before'], 'Stale production snapshot')
    check_port()
    listed = command(['systemctl', '--user', 'list-units', '--all',
                      '--plain', '--no-legend', UNIT])
    need(not listed, 'Preview unit already exists')
    runtime_path = node_and_path(plan)
    before_http = {path: http(3006, path)[0] for path in (
        '/nexus/index.html', '/api/model-quality', '/api/wazuh', '/api/events')}
    need(all(status == 200 for status in before_http.values()), 'Production API baseline unhealthy')
    database = ROOT/'private-review/decisions.sqlite3'
    before_db = hashlib.sha256(read(database)).hexdigest()
    token = secrets.token_hex(16)
    save(ROOT/'launch-attempt-private.json', {
        'unit': UNIT, 'owner_token': token, 'production_api_statuses': before_http,
        'database_sha256_before_unauthenticated_checks': before_db})
    args = ['systemd-run', '--user', '--quiet', '--collect', '--unit='+UNIT,
            '--working-directory='+plan['frontend'],
            '--property=RuntimeMaxSec=3600', '--property=TimeoutStopSec=30',
            '--property=Restart=no', '--property=MemoryMax=1G',
            '--property=CPUQuota=100%', '--property=TasksMax=128',
            '--setenv=PATH='+runtime_path, '--setenv=NEXT_TELEMETRY_DISABLED=1',
            '--setenv=NEXUS_PREVIEW_OWNER='+token,
            '--setenv=NEXUS_DECISION_REVIEW_ENABLED=1',
            '--setenv=NEXUS_DECISION_CATALOG_SHA256='+plan['catalog_sha256'],
            plan['node'], str(ROOT/'frontend/node_modules/next/dist/bin/next'),
            'start', '--hostname', '127.0.0.1', '--port', '3013']
    try:
        command(args)
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            try:
                status, _, page = http(3013, '/nexus/decision-review.html', text=True)
                if status == 200 and b'PREVIEW' in page:
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError('Preview startup timeout')
        for post in (False, True):
            status, headers, _ = http(3013, '/api/nexus/v1/decisions', post=post)
            need(status == 401 and any(
                key.lower() == 'www-authenticate' and 'NEXUS Named Reviewers' in value
                for key, value in headers.items()), 'Unauthenticated API not denied')
        need(hashlib.sha256(read(database)).hexdigest() == before_db,
             'Unauthenticated check changed private DB')
        need(production() == plan['production_before'], 'Production runtime changed')
        for path, status in before_http.items():
            need(http(3006, path)[0] == status, 'Production API status changed')
        since = int(show(UNIT, 'ActiveEnterTimestampMonotonic'))/1000000
        remaining = max(0, int(3600-(time.monotonic()-since)))
        stop_by = datetime.now(timezone(timedelta(hours=7)))+timedelta(seconds=remaining+30)
        save(ROOT/'launch-result-private.json', {
            'status': 'NAMED_REVIEW_EMPTY_PREVIEW_PASS',
            'unit': UNIT, 'invocation_id': show(UNIT, 'InvocationID'),
            'seconds_remaining_at_check': remaining, 'catalog_items': 0,
            'production_unchanged': True, 'authenticated_workflow_verified': False})
        print('NAMED_REVIEW_EMPTY_PREVIEW_PASS; unauthenticated GET/POST401')
        print('PREVIEW_URL http://127.0.0.1:3013/nexus/decision-review.html')
        print('PREVIEW_UNIT', UNIT)
        print('SECONDS_REMAINING', remaining)
        print('STOP_BY_BANGKOK_WITH_30S_STOP_GRACE', stop_by.isoformat())
        print('PRODUCTION3006_UNCHANGED; named login/browser check pending')
    except BaseException:
        try:
            stopped = stop_owned(plan, token)
            print('FAILED_PREVIEW_OWNED_UNIT_STOPPED', stopped)
        except Exception:
            print('STOP_OWNERSHIP_UNVERIFIED; no unrelated unit stopped; inspect private attempt')
        raise

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-approved-preview', action='store_true')
    parser.add_argument('--stop-owned-preview', action='store_true')
    args = parser.parse_args()
    need(args.start_approved_preview != args.stop_owned_preview, 'Select one explicit operation')
    plan = load()
    if args.start_approved_preview:
        start(plan)
    else:
        attempt = json.loads(read(ROOT/'launch-attempt-private.json'))
        print('OWNED_PREVIEW_STOPPED', stop_owned(plan, attempt['owner_token']))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        safe = str(error) if type(error) is RuntimeError else type(error).__name__
        print('PREVIEW_STOP', safe, '; no automatic retry; preserve private artifacts')
        raise SystemExit(1)
