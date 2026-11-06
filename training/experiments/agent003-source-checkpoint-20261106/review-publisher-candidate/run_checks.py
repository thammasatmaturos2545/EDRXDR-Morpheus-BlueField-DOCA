from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
root=Path(__file__).resolve().parent
repo=Path('/home/saiuser/EDRXDR-Morpheus')
manifest=json.loads((root/'candidate-sha256.json').read_bytes())
for name,digest in manifest.items():
    rel=Path(name)
    if rel.is_absolute() or '..' in rel.parts or hashlib.sha256((root/rel).read_bytes()).hexdigest()!=digest:
        raise SystemExit('STOP candidate payload binding failed')
for name,digest in json.loads((root/'baseline-bindings.json').read_bytes()).items():
    raw=subprocess.run(['git','show','HEAD:'+name],cwd=repo,capture_output=True,check=True,timeout=30).stdout
    if hashlib.sha256(raw).hexdigest()!=digest:raise SystemExit('STOP committed baseline source changed')
for name in ('decision_review.py','revision_reader.py','catalog_lifecycle.py'):
    if (root/name).read_bytes()!=(root/'frontend/server'/name).read_bytes():
        raise SystemExit('STOP tested/server module mismatch')
print('BASELINE_AND_CANDIDATE_SOURCE_BINDING_PASS',flush=True)
node=shutil.which('node')
if not node:raise SystemExit('STOP existing Node executable unavailable; no installation')
env=os.environ.copy();env['NODE_PATH']=str(repo/'frontend/node_modules')
for args in ([sys.executable,'-B','-m','unittest','discover','-s',str(root),'-p','test_*.py','-v'],
             [sys.executable,'-B',str(root/'frontend/tests/test_decision_review.py')],
             [node,str(root/'frontend/tests/decision-review.cjs')]):
    subprocess.run(args,cwd=root,env=env,check=True,timeout=120)
print('EVIDENCE_POLICY_PUBLISHER_OFFLINE_PASS; synthetic only')
print('No live catalog/users/DB/runtime/repo/model/GPU/collector changes; NOT_DEPLOYED')
