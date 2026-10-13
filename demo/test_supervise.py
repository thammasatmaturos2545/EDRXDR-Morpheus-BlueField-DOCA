import json, os, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace as R
from unittest.mock import patch
from supervise import supervise

class Tests(unittest.TestCase):
    def run_case(self, code=0, running=False, launch_error=False, inspect_error=False, oom=False):
        calls=[]
        def invoke(args,**kw):
            calls.append(args)
            if args[1]=='compose': return R(returncode=int(launch_error),stdout='a'*64+'\n',stderr='')
            if args[1]=='inspect': return R(returncode=int(inspect_error),stdout=json.dumps({
                'Status':'running' if running else 'exited','Running':running,
                'ExitCode':code,'OOMKilled':oom,'Error':''}),stderr='')
            return R(returncode=0,stdout='',stderr='')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,DEMO_RUN='test'):
            log=Path(tmp)/'console.txt'
            result=supervise(log,10,invoke,lambda:11,lambda _:None)
            saved=int(Path(str(log)+'.exit-code').read_text())
            self.assertEqual(result,saved)
        return result,calls
    def test_success(self): self.assertEqual(self.run_case()[0],0)
    def test_nonzero_preserved(self): self.assertEqual(self.run_case(code=7)[0],7)
    def test_container_timeout_preserved(self): self.assertEqual(self.run_case(code=124)[0],124)
    def test_deadline_stops_exact_id(self):
        result,calls=self.run_case(running=True)
        self.assertEqual(result,124)
        self.assertIn(['docker','stop','--time','5','a'*64],calls)
    def test_launch_failure_no_stop_or_retry(self):
        result,calls=self.run_case(launch_error=True)
        self.assertEqual(result,125); self.assertEqual(len(calls),1)
    def test_inspect_failure_not_success(self): self.assertEqual(self.run_case(inspect_error=True)[0],125)
    def test_oom_not_success(self): self.assertEqual(self.run_case(oom=True)[0],125)

if __name__=='__main__': unittest.main(verbosity=2)
