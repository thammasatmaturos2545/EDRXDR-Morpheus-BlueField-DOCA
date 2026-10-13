from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, tempfile
root=Path(__file__).resolve().parent
repo=Path.home()/'EDRXDR-Morpheus'
manifest=json.loads((root/'manifest.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
if not head.startswith('cb514aa'): raise SystemExit('STOP: checkpoint changed; review before installing')
for rel,want in manifest['expected'].items():
    if (repo/rel).is_symlink() or sha(repo/rel)!=want: raise SystemExit('STOP: source changed: '+rel)
for rel,want in manifest['payload'].items():
    if (repo/rel).exists() or (repo/rel).is_symlink(): raise SystemExit('STOP: target already exists: '+rel)
    if sha(root/'payload'/rel)!=want: raise SystemExit('STOP: payload hash mismatch')
with tempfile.TemporaryDirectory(prefix='edrxdr-operator-sink-tests-') as temp:
    stage=Path(temp)
    for rel in manifest['expected']:
        (stage/Path(rel).name).write_bytes((repo/rel).read_bytes())
    for rel in manifest['payload']:
        if rel.endswith('.py'): (stage/Path(rel).name).write_bytes((root/'payload'/rel).read_bytes())
    scratch=stage/'tmp';scratch.mkdir(mode=0o700)
    env=dict(os.environ,TMPDIR=str(scratch),TEMP=str(scratch),TMP=str(scratch),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(stage),'-p','test_bluefield_operator_*.py'],capture_output=True,text=True,timeout=90,env=env)
    print(result.stdout);print(result.stderr)
    if result.returncode: raise SystemExit('STOP: tests failed; no project source installed')
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
evidence=repo/'training/evidence'/('bluefield-operator-step8-'+stamp)
evidence.mkdir(parents=True,exist_ok=False)
(evidence/'validation.txt').write_text(result.stdout+result.stderr)
(evidence/'manifest.json').write_bytes((root/'manifest.json').read_bytes())
for rel in manifest['payload']:
    p=repo/rel
    with p.open('xb') as f: f.write((root/'payload'/rel).read_bytes())
(evidence/'install_sink.py').write_bytes(Path(__file__).read_bytes())
print('PASS: three new files installed; no existing source/docs overwritten, no service/broker/approval changes')
print('Evidence:',evidence)
