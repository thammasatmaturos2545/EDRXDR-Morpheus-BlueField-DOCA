"""One explicit frozen CPU diagnostic in a bounded networkless container."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

LAB=Path('/home/saiuser/edrxdr-nvidia-lab-znmqaTGL')
NEW=LAB/'dfp-postcapture-development-ksg7k9_y'
MODEL_DIR=LAB/'dfp-archive-cpu-prototype-uy_2ita1'
CPU=LAB/'dfp-cpu-adapter-RMNy70Z4'
REPORT='6de4aa5337450a5b3bf7359774169f04f22a8f63f00a72ff04dca985bdcb06df'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def read(path,expected=None,limit=8*1024*1024):
    require(path.is_file() and not path.is_symlink(),'input missing or redirected')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    require(len(raw)<=limit,'input size bound')
    if expected is not None:require(sha(raw)==expected,'input binding mismatch')
    return raw


def command(*args):
    return subprocess.run(args,capture_output=True,check=True,timeout=30).stdout


def inspect(cid):
    rows=json.loads(command('docker','inspect',cid))
    require(len(rows)==1 and rows[0]['Id']==cid,'container identity')
    return rows[0]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-frozen-cpu-diagnostic',action='store_true');args=parser.parse_args()
    if not args.run_frozen_cpu_diagnostic:parser.error('explicit --run-frozen-cpu-diagnostic required')
    os.umask(0o077);base=Path(__file__).resolve().parent
    for name,digest in json.loads(read(base/'SHA256.json')).items():
        require(Path(name).name==name,'package path');read(base/name,digest)
    subprocess.run([sys.executable,'-B','-m','unittest','-q','test_contract.py'],cwd=base,check=True,timeout=60)
    from contract import MODEL,SOURCE,CAPTURE,PYTHON,validate
    report=json.loads(read(NEW/'aggregate-report.json',REPORT))
    require(report['source_capture_sha256']==CAPTURE and report['records']==845 and report['windows']==12 and
            report['logging_restored_receipt_verified'] is True and report['raw_hash_overlap_occurrences']==0 and
            report['all_event_times_after_fitting_capture'] is True,'new-capture checkpoint')
    manifest=json.loads(read(NEW/'SHA256.json'))
    features_raw=read(NEW/'features-development-private.jsonl',manifest['features-development-private.jsonl'])
    coverage_raw=read(NEW/'coverage-review-private.jsonl',manifest['coverage-review-private.jsonl'])
    validate([json.loads(x) for x in features_raw.splitlines()],[json.loads(x) for x in coverage_raw.splitlines()])
    read(MODEL_DIR/'model-private.pkl',MODEL)
    read(CPU/'source-manifest.json',SOURCE)
    images=json.loads(command('docker','image','inspect','edrxdr-morpheus-train:25.06'))
    require(len(images)==1 and images[0]['Os']=='linux' and images[0]['Architecture']=='amd64' and
            re.fullmatch(r'sha256:[a-f0-9]{64}',images[0]['Id']),'local CPU image identity/platform')
    image=images[0]['Id']
    probe=['docker','run','--rm','--pull=never','--runtime','runc','--network','none','--read-only',
           '--user',f'{os.getuid()}:{os.getgid()}','--cap-drop','ALL','--security-opt','no-new-privileges',
           '--memory','4g','--cpus','2','--pids-limit','128','--tmpfs','/tmp:rw,nosuid,nodev,size=128m',
           '-e','NVIDIA_VISIBLE_DEVICES=void','-e','CUDA_VISIBLE_DEVICES=-1',
           '-e','PYTHONDONTWRITEBYTECODE=1','-e','XDG_CACHE_HOME=/tmp/cache',
           '--entrypoint',PYTHON,image,'-B','-c',
           'import sys,numpy,pandas,torch; print("MORPHEUS_PYTHON_IMPORT_PASS",sys.executable)']
    environment=subprocess.run(probe,capture_output=True,timeout=90)
    require(environment.returncode==0 and b'MORPHEUS_PYTHON_IMPORT_PASS' in environment.stdout,
            'Morpheus environment import preflight failed; no model loaded')
    print('MORPHEUS_PYTHON_IMPORT_PREFLIGHT_PASS; no model loaded',flush=True)
    out=Path(tempfile.mkdtemp(prefix='dfp-frozen-cpu-diagnostic-',dir=LAB));(out/'result').mkdir()
    plan=dict(mode='frozen_cpu_diagnostic_no_fit',model_sha256=MODEL,cpu_source_manifest_sha256=SOURCE,
              source_capture_sha256=CAPTURE,features_sha256=sha(features_raw),coverage_sha256=sha(coverage_raw),
              image_id=image,quality_evaluation_authorized=False,threshold_selection_allowed=False)
    plan_path=out/'plan-private.json';plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    name='edrxdr-dfp-cpu-diag-'+out.name.rsplit('-',1)[-1]
    label='edrxdr.purpose=frozen-cpu-diagnostic-20261104'
    args=['docker','create','--pull=never','--name',name,'--label',label,'--runtime','runc',
          '--network','none','--read-only','--user',f'{os.getuid()}:{os.getgid()}',
          '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','4g','--cpus','2','--pids-limit','128',
          '--tmpfs','/tmp:rw,nosuid,nodev,size=128m',
          '-e','NVIDIA_VISIBLE_DEVICES=void','-e','CUDA_VISIBLE_DEVICES=-1',
          '-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONUNBUFFERED=1','-e','XDG_CACHE_HOME=/tmp/cache',
          '-e','TORCH_HOME=/tmp/torch','-e','OMP_NUM_THREADS=2','-e','MKL_NUM_THREADS=2',
          '-v',f'{base}:/candidate:ro','-v',f'{MODEL_DIR}/model-private.pkl:/model/model.pkl:ro',
          '-v',f'{CPU}/source-manifest.json:/code/source-manifest.json:ro',
          '-v',f'{CPU}/dfencoder_cpu:/code/dfencoder_cpu:ro',
          '-v',f'{NEW}/features-development-private.jsonl:/inputs/features.jsonl:ro',
          '-v',f'{NEW}/coverage-review-private.jsonl:/inputs/coverage.jsonl:ro',
          '-v',f'{plan_path}:/inputs/plan.json:ro','-v',f'{out}/result:/output:rw',
          '--workdir','/candidate','--entrypoint',PYTHON,image,'-B','/candidate/worker.py']
    cid=command(*args).decode().strip();require(re.fullmatch('[a-f0-9]{64}',cid),'new container ID')
    c=inspect(cid);host=c['HostConfig']
    require(c['Image']==image and c['Name']=='/'+name and c['Config']['Labels'].get('edrxdr.purpose')=='frozen-cpu-diagnostic-20261104'
            and host['Runtime']=='runc' and host['NetworkMode']=='none' and host['ReadonlyRootfs'] is True
            and not host.get('DeviceRequests') and not host.get('Devices'),'CPU isolation inspection')
    print('FROZEN_CPU_DIAGNOSTIC_START; no fit, no GPU, no network, no services changed',flush=True)
    print('PRIVATE_OUTPUT',out,flush=True)
    with (out/'run-private.log').open('xb') as log:
        try:result=subprocess.run(['docker','start','--attach',cid],stdout=log,stderr=subprocess.STDOUT,timeout=300)
        except subprocess.TimeoutExpired:
            current=inspect(cid)
            require(current['Name']=='/'+name and current['Config']['Labels'].get('edrxdr.purpose')=='frozen-cpu-diagnostic-20261104','timeout target identity')
            command('docker','stop','--time','20',cid)
            raise ValueError('CPU diagnostic timeout; own container stopped; keep private output')
    c=inspect(cid)
    if result.returncode!=0 or c['State']['ExitCode']!=0:
        text=read(out/'run-private.log',limit=262144).decode('utf-8',errors='replace')
        for line in text.splitlines():
            if re.fullmatch(r'CPU_DIAGNOSTIC_STOP MISSING_MODULE [A-Za-z_][A-Za-z0-9_.]{0,100}',line):
                print(line)
    require(result.returncode==0 and c['State']['Status']=='exited' and c['State']['ExitCode']==0 and
            c['State']['OOMKilled'] is False,'CPU worker failed; keep private log; no automatic retry')
    summary=json.loads(read(out/'result/aggregate-report.json'))
    require(summary['status']=='FROZEN_CPU_NEW_CAPTURE_DIAGNOSTIC_PASS_NOT_QUALITY_ACCEPTANCE' and
            summary['model_sha256']==MODEL and summary['source_capture_sha256']==CAPTURE and
            summary['training_performed'] is False and summary['gpu_used'] is False,'CPU result contract')
    result_manifest=json.loads(read(out/'result/SHA256.json'))
    for name,digest in result_manifest.items():
        require(Path(name).name==name,'result path');read(out/'result'/name,digest)
    print(json.dumps(summary,sort_keys=True,allow_nan=False))
    print('REPORT_SHA256',sha(read(out/'result/aggregate-report.json')))
    print('STOPPED_DIAGNOSTIC_CONTAINER',cid)
    print('FROZEN_CPU_DIAGNOSTIC_COMPLETE; originals unchanged; no threshold, labels, deployment or BERT replacement')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('FROZEN_CPU_LAUNCH_STOP',str(error) if type(error) is ValueError else type(error).__name__,
              '; details withheld; no automatic retry')
        raise SystemExit(1)
