from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
if sys.argv[1:]!=['--audit-existing-projections']:
    raise SystemExit('Explicit read-only audit flag required')
subprocess.run([sys.executable,'-B','-m','unittest','-v','test_audit.py'],cwd=root,check=True,timeout=30)
subprocess.run([sys.executable,'-B',str(root/'audit.py')],cwd=root,check=True,timeout=20)
