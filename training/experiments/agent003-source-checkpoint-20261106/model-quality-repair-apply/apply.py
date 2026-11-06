"""Scoped legacy-report path repair; never changes detector settings."""
from pathlib import Path
import argparse, fcntl, hashlib, json, os, shutil, subprocess, sys, time
import urllib.request, urllib.error

UNIT = 'nexus-all-events-prod-3006.service'
ROOT = Path('/mnt/nexus-copilot-mQTssj/model-quality-repair-plan-j2izri20')
EXPECTED = {
    'quality_report.json': 'd3855b285168d61f8d60a14eb22cf99aea0b71c948787ed36627e3308b6a0b6d',
    'parity_report.json': '331e61e36c34515ff96e281a584dac54adee8541c5df53a7da220b94f1dd5a35',
}
PATHS = ('/api/wazuh', '/api/events', '/api/nexus/v1/snapshot',
         '/api/nexus/v1/health', '/api/nexus/v1/lab',
         '/api/nexus/v1/dfp-diagnostic', '/api/nexus/v1/decisions')

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(info.st_uid == os.getuid() and info.st_nlink == 1
             and info.st_size <= 1048576, 'Private file metadata mismatch')
        raw = stream.read(1048577)
        need(len(raw) <= 1048576, 'Private file bound')
        return raw

def save(path, value):
    temporary = path.with_suffix('.pending')
    with temporary.open('w') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)

def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
    need(result.returncode == 0, 'Command failed: ' + Path(args[0]).name)
    return result.stdout.strip()

def show(key):
    return command(['systemctl', '--user', 'show', UNIT, '-p', key, '--value'])

def runtime():
    return {key: show(key) for key in (
        'MainPID', 'WorkingDirectory', 'ActiveState', 'SubState',
        'FragmentPath', 'DropInPaths')}

def report_environment():
    pid = show('MainPID')
    need(pid.isdigit() and pid != '0', 'Runtime PID unavailable')
    for part in Path('/proc/' + pid + '/environ').read_bytes().split(bytes([0])):
        if part.startswith(b'MODEL_QUALITY_REPORT_DIR='):
            return part.split(b'=', 1)[1].decode()
    return None

def http(path, body=False):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:3006' + path, timeout=8) as response:
            if not body:
                return response.status, None
            raw = response.read(1048577)
            need(len(raw) <= 1048576, 'HTTP body bound')
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as error:
        return error.code, None

def load():
    need(ROOT.resolve() == ROOT and not ROOT.is_symlink(), 'Plan root scope')
    info = ROOT.stat()
    need(info.st_uid == os.getuid() and info.st_mode & 0o777 == 0o700,
         'Private root permissions')
    plan = json.loads(read(ROOT / 'plan-private.json'))
    need(plan['unit'] == UNIT and plan['source_reports_sha256'] == EXPECTED
         and plan['changes_applied'] is False, 'Plan scope mismatch')
    frozen = Path(plan['frozen_report_directory'])
    env = Path(plan['private_environment_file'])
    candidate = Path(plan['proposed_dropin_file'])
    drop = Path(plan['proposed_dropin_path'])
    need(frozen == ROOT / 'reports' and env == ROOT / 'model-quality.env'
         and candidate == ROOT / 'proposed-drop-in.conf', 'Artifact scope mismatch')
    need(drop.parent == Path.home() / '.config/systemd/user' / (UNIT + '.d')
         and drop.name.endswith('.model-quality-20261105.conf'),
         'Drop-in scope mismatch')
    content = ('[Service]\nEnvironmentFile=' + str(env) + '\n').encode()
    need(read(candidate) == content and sha(content) == plan['proposed_dropin_sha256'],
         'Drop-in hash mismatch')
    need(read(env) == ('MODEL_QUALITY_REPORT_DIR=' + str(frozen) + '\n').encode(),
         'Environment scope mismatch')
    for name, digest in EXPECTED.items():
        need(sha(read(frozen / name)) == digest, 'Frozen report changed')
    return plan, drop, content

def restart():
    command(['systemctl', '--user', 'daemon-reload'])
    command(['systemctl', '--user', 'restart', '--no-block', UNIT])
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if show('ActiveState') == 'active' and show('SubState') == 'running':
            try:
                if http('/nexus/index.html')[0] == 200:
                    return
            except Exception:
                pass
        time.sleep(1)
    raise RuntimeError('NEXUS readiness timeout')

def rollback(plan, drop, automatic=False):
    result = ROOT / 'apply-result-private.json'
    if automatic and result.exists() and json.loads(read(result)).get('status') == 'QUALITY_PATH_REPAIR_PASS':
        print('WATCHDOG_NO_CHANGE; successful apply verified')
        return
    attempt = json.loads(read(ROOT / 'attempt-private.json'))
    need(show('WorkingDirectory') == plan['runtime_before']['WorkingDirectory'],
         'Runtime directory changed; review required')
    if os.path.lexists(drop):
        need(sha(read(drop)) == plan['proposed_dropin_sha256'],
             'Owned drop-in changed; refuse removal')
        drop.unlink()
        restart()
    need(report_environment() == attempt['previous_report_directory'],
         'Previous report environment not restored')
    need(http('/api/model-quality')[0] == attempt['baseline_quality_http'],
         'Quality baseline not restored')
    for path, status in attempt['baseline_api_statuses'].items():
        need(http(path)[0] == status, 'Rollback API mismatch')
    save(ROOT / 'rollback-result-private.json', {'status': 'ROLLBACK_PASS'})
    print('ROLLBACK_PASS; previous report path and API statuses restored', flush=True)

def apply(plan, drop, content):
    need(not (ROOT / 'attempt-private.json').exists(), 'Attempt exists; no retry')
    need(runtime() == plan['runtime_before'], 'Stale runtime plan')
    need(show('NeedDaemonReload') == 'no', 'Unrelated pending service configuration')
    need(not os.path.lexists(drop), 'Drop-in exists')
    need(all(Path(name).name < drop.name for name in show('DropInPaths').split()),
         'Drop-in ordering changed')
    need(drop.parent.is_dir() and drop.parent.resolve() == drop.parent
         and not drop.parent.is_symlink(), 'Drop-in parent scope')
    need(http('/api/model-quality')[0] == 503, 'Quality baseline changed')
    baseline = {path: http(path)[0] for path in PATHS}
    need(all(baseline[path] == 200 for path in PATHS[:4]), 'Core API baseline unhealthy')
    save(ROOT / 'attempt-private.json', {
        'baseline_quality_http': 503, 'baseline_api_statuses': baseline,
        'previous_report_directory': report_environment()})
    helper = ROOT / 'apply-quality-repair.py'
    need(not helper.exists(), 'Helper exists')
    shutil.copyfile(Path(__file__).resolve(), helper)
    helper.chmod(0o600)
    watchdog = 'nexus-quality-rollback-' + ROOT.name.rsplit('-', 1)[-1]
    command(['systemd-run', '--user', '--unit=' + watchdog, '--on-active=180s',
             '--timer-property=AccuracySec=1s', '--property=TimeoutStartSec=180',
             sys.executable, '-B', str(helper), '--automatic-rollback'])
    command(['systemctl', '--user', 'is-active', '--quiet', watchdog + '.timer'])
    print('INDEPENDENT_ROLLBACK_TIMER_ARMED', flush=True)
    installed = False
    try:
        need(runtime() == plan['runtime_before'], 'Runtime changed before apply')
        fd = os.open(drop, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        installed = True
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        restart()
        need(show('WorkingDirectory') == plan['runtime_before']['WorkingDirectory'],
             'Runtime directory changed')
        need(report_environment() == plan['frozen_report_directory'],
             'Effective report directory mismatch')
        status, data = http('/api/model-quality', True)
        need(status == 200 and type(data) is dict, 'Quality endpoint not200')
        need(data.get('source') == {
            'quality_sha256': EXPECTED['quality_report.json'],
            'parity_sha256': EXPECTED['parity_report.json']}, 'HTTP report hashes differ')
        need(data.get('quality', {}).get('scope') == 'development_only',
             'Legacy scope mismatch')
        need(data['quality']['threshold'] == data['parity']['threshold'],
             'Threshold mismatch')
        for path, status in baseline.items():
            need(http(path)[0] == status, 'Existing API status changed')
        save(ROOT / 'apply-result-private.json', {
            'status': 'QUALITY_PATH_REPAIR_PASS', 'report_scope': 'legacy_development_only',
            'report_hashes': EXPECTED, 'api_statuses_unchanged': True,
            'runtime_directory': show('WorkingDirectory'), 'main_pid': show('MainPID'),
            'detector_quality_accepted': False})
        print('MODEL_QUALITY_HTTP200_EXACT_REPORT_HASHES_PASS', flush=True)
        print('EXISTING_API_STATUSES_UNCHANGED; legacy development reports only')
        print('QUALITY_PATH_REPAIR_PASS; no detector/observer/users/DB/model/GPU changes')
        print('PRIVATE_REPORT', ROOT / 'apply-result-private.json')
    except BaseException:
        if installed:
            try:
                rollback(plan, drop)
            except Exception:
                print('ROLLBACK_NEEDS_REVIEW; timer retained; preserve private plan', flush=True)
        raise

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply-approved', action='store_true')
    parser.add_argument('--rollback', action='store_true')
    parser.add_argument('--automatic-rollback', action='store_true')
    args = parser.parse_args()
    need(sum((args.apply_approved, args.rollback, args.automatic_rollback)) == 1,
         'Select one explicit operation')
    plan, drop, content = load()
    with (ROOT / 'operation.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.apply_approved:
            apply(plan, drop, content)
        else:
            rollback(plan, drop, args.automatic_rollback)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('STOP', type(error).__name__,
              'scoped operation failed; preserve receipts; no automatic retry')
        raise SystemExit(1)
