"""Read-only VM metadata collection; never starts/retries a capture or service."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error

REPO = Path('/home/saiuser/EDRXDR-Morpheus')
LAB = Path('/home/saiuser/edrxdr-nvidia-lab-znmqaTGL')
PREP = Path('/mnt/nexus-copilot-mQTssj/dfp-approved-preflight-qui6r9nz')


def command(*args):
    env = {**os.environ, 'GIT_OPTIONAL_LOCKS':'0'}
    return subprocess.run(args, capture_output=True, check=True, timeout=30, env=env).stdout


def bounded_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
        raise ValueError('metadata file missing/redirected/oversized')
    return json.loads(path.read_bytes())


def pilot_status():
    consumed = PREP/'approval-consumed.json'
    if not consumed.exists():
        return {'status':'NO_CONSUMED_APPROVAL_FILE', 'start_confirmed':False,
                'interpretation':'not proof that logging is disabled; do not launch a duplicate'}
    value = bounded_json(consumed)
    attempt = Path(value['attempt'])
    if attempt.is_symlink() or attempt.resolve().parent != PREP.resolve() or not attempt.name.startswith('approved-55m-'):
        raise ValueError('unexpected saved attempt')
    s = bounded_json(attempt/'state.json')
    safe = ('status','activation_restart_started','armed_at_utc','activation_started_utc',
            'observation_started_utc','seconds_since_armed','archive_growth_bytes','stop_reason',
            'restoration_started_utc','restored_at_utc','logall_json','startup_original_bytes_restored',
            'effective_original_restored','manager_required_processes_ready','service_restoration_verified',
            'worker_error_type','restore_error_type','capture_error_type','model_invocations',
            'training_performed','gpu_used','direct_kafka_opensearch_writes')
    result = {k:s[k] for k in safe if k in s}
    result['private_attempt'] = str(attempt)
    if type(s.get('capture')) is dict:
        result['capture'] = {k:v for k,v in s['capture'].items() if k in
                             ('status','capture_sha256','capture_bytes','capture_lines','window_complete')}
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def http_code(path):
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open('http://127.0.0.1:3006'+path, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        code = error.code; error.close(); return code


def main():
    os.umask(0o077)
    base = Path(__file__).resolve().parent
    for name, expected in bounded_json(base/'SHA256.json').items():
        path = base/name
        if Path(name).name != name or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('package hash binding failed')
    subprocess.run([sys.executable,'-B','-m','unittest','-q','test_acceptance.py','test_collect.py'],cwd=base,check=True,timeout=60)
    from acceptance import evaluate
    manifest = bounded_json(base/'acceptance.json')
    report = dict(collected_at_utc=datetime.now(timezone.utc).isoformat(),
                  acceptance=evaluate(manifest), checks={}, model_invocations=0,
                  runtime_changes=False, capture_start_or_retry=False)
    def record(name, callback):
        try: report['checks'][name] = callback()
        except Exception as error: report['checks'][name] = {'status':'UNAVAILABLE','error_type':type(error).__name__}
    status_before = command('git','-C',str(REPO),'status','--porcelain=v1','-z')
    record('git',lambda:dict(branch=command('git','-C',str(REPO),'branch','--show-current').decode().strip(),
                             head=command('git','-C',str(REPO),'rev-parse','HEAD').decode().strip(),
                             staged_names=command('git','-C',str(REPO),'diff','--cached','--name-only').decode().splitlines(),
                             worktree_status_sha256=hashlib.sha256(status_before).hexdigest()))
    record('nexus_service',lambda:command('systemctl','--user','show','nexus-all-events-prod-3006.service',
                                        '--no-pager','-p','ActiveState','-p','SubState','-p','WorkingDirectory','-p','MainPID').decode().splitlines())
    record('archive_units',lambda:json.loads(command('systemctl','--user','list-units','--all','--output=json',
                                                    '--no-pager','edrxdr-archive*')))
    record('archive_timers',lambda:json.loads(command('systemctl','--user','list-timers','--all','--output=json',
                                                     '--no-pager','edrxdr-archive*')))
    record('approved_pilot',pilot_status)
    record('containers',lambda:command('docker','ps','--format','{{.Names}}\t{{.Status}}').decode().splitlines())
    for label,path in [('nexus_page','/nexus/index.html'),('lab_without_auth','/api/nexus/v1/lab')]:
        record(label,lambda path=path:dict(http_status=http_code(path),auth_supplied=False))
    status_after = command('git','-C',str(REPO),'status','--porcelain=v1','-z')
    report['git_status_unchanged_during_collection'] = status_after == status_before
    report['archive_logging_current_value_verified'] = False
    report['note'] = 'Saved pilot state is a receipt, not a fresh effective-config check; no config contents read.'
    out = Path(tempfile.mkdtemp(prefix='project-delivery-status-',dir=LAB))
    raw = (json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
    with (out/'aggregate-status.json').open('xb') as stream: stream.write(raw)
    print(json.dumps(report,sort_keys=True,allow_nan=False))
    print('PRIVATE_STATUS_DIRECTORY',out)
    print('REPORT_SHA256',hashlib.sha256(raw).hexdigest())
    print('No repo/index/service/config changes, model, training, GPU, raw-log/key reads or capture launch')


if __name__=='__main__':
    try: main()
    except Exception as error:
        print('STATUS_COLLECTION_STOP',type(error).__name__,'details withheld; no automatic retry')
        raise SystemExit(1)
