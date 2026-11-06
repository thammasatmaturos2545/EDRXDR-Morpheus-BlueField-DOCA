"""Prepare frozen legacy reports and a proposed drop-in. Never applies/restarts."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile,urllib.request,urllib.error
UNIT='nexus-all-events-prod-3006.service'
SOURCE=Path('/home/saiuser/EDRXDR-Morpheus/reports/morpheus-raw-offline-check-20261008T203523Z-1803526')
EXPECTED={'quality_report.json':'d3855b285168d61f8d60a14eb22cf99aea0b71c948787ed36627e3308b6a0b6d',
          'parity_report.json':'331e61e36c34515ff96e281a584dac54adee8541c5df53a7da220b94f1dd5a35'}
def show(key):
    return subprocess.run(['systemctl','--user','show',UNIT,'-p',key,'--value'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
def runtime():
    return {key:show(key) for key in ('MainPID','WorkingDirectory','ActiveState','SubState','FragmentPath','DropInPaths')}
def main():
    os.umask(0o077)
    before=runtime()
    if before['ActiveState']!='active' or before['SubState']!='running' or not before['MainPID'].isdigit() or before['MainPID']=='0':
        raise RuntimeError('NEXUS runtime not stable active')
    reports={}
    for name,expected in EXPECTED.items():
        fd=os.open(SOURCE/name,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as f:
            stat=os.fstat(f.fileno())
            if stat.st_size>1024*1024:raise RuntimeError('Report byte bound')
            raw=f.read(1024*1024+1)
        if hashlib.sha256(raw).hexdigest()!=expected:raise RuntimeError('Verified report changed')
        reports[name]=raw
    q=json.loads(reports['quality_report.json']);p=json.loads(reports['parity_report.json'])
    if q['scope']!='development_only' or q['threshold']!=p['threshold']:raise RuntimeError('Scope/threshold changed')
    names=[Path(name).name for name in before['DropInPaths'].split()]
    last=max(names,default='00-base.conf')
    proposed_name=last+'.model-quality-20261105.conf'
    if len(proposed_name)>240 or '/' in proposed_name:raise RuntimeError('Drop-in basename needs manual review')
    proposed=Path.home()/'.config/systemd/user'/f'{UNIT}.d'/proposed_name
    if proposed.exists() or proposed.is_symlink():raise RuntimeError('Proposed drop-in exists; do not overwrite')
    for name in before['DropInPaths'].split():
        if Path(name).name>=proposed.name:raise RuntimeError('Drop-in ordering needs review')
    try:
        with urllib.request.urlopen('http://127.0.0.1:3006/api/model-quality',timeout=10) as r:status=r.status
    except urllib.error.HTTPError as exc:status=exc.code
    if status!=503:raise RuntimeError('Quality endpoint baseline is not expected503')
    root=Path(tempfile.mkdtemp(prefix='model-quality-repair-plan-',dir='/mnt/nexus-copilot-mQTssj'))
    frozen=root/'reports';frozen.mkdir(mode=0o700)
    for name,raw in reports.items():
        with (frozen/name).open('xb') as f:f.write(raw)
    env=root/'model-quality.env';env.write_text('MODEL_QUALITY_REPORT_DIR='+str(frozen)+'\n')
    content='[Service]\nEnvironmentFile='+str(env)+'\n'
    candidate=root/'proposed-drop-in.conf';candidate.write_text(content)
    plan={'schema_version':'model-quality-path-repair-plan-1','unit':UNIT,'runtime_before':before,
        'source_reports_sha256':EXPECTED,'report_scope':'legacy_development_only_not_new_DFP_quality',
        'frozen_report_directory':str(frozen),'private_environment_file':str(env),
        'proposed_dropin_path':str(proposed),'proposed_dropin_sha256':hashlib.sha256(content.encode()).hexdigest(),
        'proposed_dropin_file':str(candidate),'baseline_quality_http':status,
        'changes_applied':False,'restart_performed':False,'approval_required_for_apply':True,
        'rollback':'Remove only newly installed hash-matching drop-in; daemon-reload and restart only NEXUS3006; preserve all artifacts.'}
    if runtime()!=before:raise RuntimeError('Runtime changed during preparation; retain artifacts and review')
    (root/'plan-private.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('FROZEN_LEGACY_REPORTS_VERIFIED; quality/parity hashes bound')
    print('PRIVATE_PREPARATION',root)
    print('PROPOSED_RUNTIME_CHANGE append one EnvironmentFile; restart only NEXUS3006')
    print('WORKING_DIRECTORY_UNCHANGED',before['WorkingDirectory'])
    print('NOT_APPLIED; no restart/env/drop-in/repo/model/GPU/collector changes')
if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('STOP',type(exc).__name__,'preparation failed; details withheld; no automatic retry')
        raise SystemExit(1)
