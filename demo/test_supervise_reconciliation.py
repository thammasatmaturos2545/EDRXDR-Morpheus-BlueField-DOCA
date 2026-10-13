import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace as R
from unittest.mock import patch
from supervise import supervise

class ReconciliationTests(unittest.TestCase):
    def case(self, mode):
        calls=[]
        inspections=0
        ticks=iter([11] if mode=='expired' else [9,11,11])
        def invoke(args, **kwargs):
            nonlocal inspections
            calls.append(args)
            if args[1]=='compose':
                if mode=='launch_timeout':
                    raise subprocess.TimeoutExpired(args,30)
                return R(returncode=0,stdout='a'*64,stderr='')
            if args[1]=='inspect':
                inspections+=1
                if mode=='interrupt' and inspections==1:
                    raise KeyboardInterrupt()
                exited=inspections>1 and mode not in ('still_running','inspect_failure')
                return R(returncode=int(mode=='inspect_failure'),stdout=json.dumps({
                    'Status':'exited' if exited else 'running','Running':not exited}),stderr='')
            return R(returncode=int(mode=='stop_failure' and args[1]=='stop'),stdout='',stderr='')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,DEMO_RUN='test'):
            log=Path(tmp)/'run'
            code=supervise(log,10,invoke,lambda:next(ticks,11),lambda _:None)
            report=json.loads(Path(str(log)+'.supervisor.json').read_text())
            self.assertEqual(code,report['result'])
        return code,report,calls

    def test_expired_never_calls_docker(self):
        code,report,calls=self.case('expired')
        self.assertEqual(code,124)
        self.assertEqual(calls,[])
        self.assertFalse(report['reconciliation_required'])

    def test_launch_timeout_requires_reconciliation_without_guessing_identity(self):
        code,report,calls=self.case('launch_timeout')
        self.assertEqual(code,125)
        self.assertTrue(report['reconciliation_required'])
        self.assertEqual(len(calls),1)

    def test_stop_success_is_verified(self):
        code,report,_=self.case('normal')
        self.assertEqual(code,124)
        self.assertTrue(report['stop_confirmed'])

    def test_stop_return_code_does_not_prove_exit(self):
        _,report,_=self.case('still_running')
        self.assertFalse(report['stop_confirmed'])
        self.assertTrue(report['reconciliation_required'])

    def test_failed_stop_but_independently_exited(self):
        _,report,_=self.case('stop_failure')
        self.assertTrue(report['stop_confirmed'])

    def test_unavailable_inspection_is_unknown(self):
        _,report,_=self.case('inspect_failure')
        self.assertTrue(report['reconciliation_required'])

    def test_keyboard_interrupt_stops_exact_container(self):
        code,report,calls=self.case('interrupt')
        self.assertEqual(code,130)
        self.assertTrue(report['stop_confirmed'])
        self.assertIn(['docker','stop','--time','5','a'*64],calls)

if __name__=='__main__':
    unittest.main(verbosity=2)
