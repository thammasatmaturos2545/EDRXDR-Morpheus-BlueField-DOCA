from pathlib import Path
import subprocess,sys
if sys.argv[1:]!=['--synthetic-self-test']:
    raise SystemExit('Only explicit synthetic tests are supported; no real data reader')
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-B','-m','unittest','-v','test_evaluation.py'],cwd=root,check=True,timeout=30)
print('DFP_DESCRIPTIVE_EVALUATION_CORE_PASS; synthetic only')
print('No real data/model/key reads, fitting, threshold selection, collector or runtime changes')
