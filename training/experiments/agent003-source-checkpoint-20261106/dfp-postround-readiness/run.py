from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-B','-m','unittest','-v','test_readiness.py'],cwd=root,check=True,timeout=30)
subprocess.run([sys.executable,'-B',str(root/'readiness.py'),'--audit-original-completed-round'],cwd=root,check=True,timeout=45)
