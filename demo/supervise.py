"""Bounded Docker CLI supervision; no GPU imports or automatic retries."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

def supervise(log, deadline, invoke=subprocess.run, clock=time.time, pause=time.sleep):
    log=Path(log)
    def save(suffix, value):
        Path(str(log)+suffix).write_text(value, encoding='utf-8')
    def call(args, seconds=10):
        return invoke(args, capture_output=True, text=True, timeout=seconds)
    result=125
    cid=None
    reason='launcher_failed'
    try:
        launched=call(['docker','compose','-f','compose.yml','run','-d','--name',
            'edrxdr-demo-'+os.environ['DEMO_RUN'],'--no-deps','--pull','never','worker'],30)
        save('.launch.stdout',launched.stdout)
        save('.launch.stderr',launched.stderr)
        save('.launch.exit-code',str(launched.returncode)+'\n')
        if launched.returncode != 0:
            raise RuntimeError('launch_failed_no_retry')
        cid=launched.stdout.strip()
        if not re.fullmatch('[0-9a-f]{64}',cid):
            cid=None
            raise RuntimeError('invalid_container_id_no_retry')
        save('.container-id',cid+'\n')
        while True:
            state_result=call(['docker','inspect',cid,'--format','{{json .State}}'],5)
            save('.inspect.stderr',state_result.stderr)
            if state_result.returncode:
                raise RuntimeError('inspect_failed')
            state=json.loads(state_result.stdout)
            save('.container-state.json',state_result.stdout)
            if state.get('Status')=='exited' and state.get('Running') is False:
                code=state.get('ExitCode')
                if type(code) is not int or not 0<=code<=255:
                    raise RuntimeError('invalid_exit_code')
                if state.get('OOMKilled') is not False or state.get('Error') != '':
                    raise RuntimeError('container_runtime_error')
                result=code
                reason='container_exited'
                break
            if clock()>=deadline:
                result=124
                reason='supervisor_deadline'
                break
            pause(2)
    except Exception as exc:
        reason=type(exc).__name__+':'+str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__
    finally:
        # Only the exact ID returned by our launch is inspected/stopped.
        # Never remove a container or alter shared services.
        if cid:
            if reason!='container_exited':
                try:
                    stopped=call(['docker','stop','--time','5',cid],15)
                    save('.stop-result',str(stopped.returncode)+'\n'+stopped.stderr)
                except Exception as exc:
                    save('.stop-result',type(exc).__name__+'\n')
            try:
                logs=call(['docker','logs',cid],15)
                log.write_text(logs.stdout+logs.stderr,encoding='utf-8')
                if logs.returncode and result==0:
                    result=125; reason='log_collection_failed'
            except Exception as exc:
                save('.logs-error',type(exc).__name__+'\n')
                if result==0: result=125; reason='log_collection_failed'
        save('.exit-code',str(result)+'\n')
        save('.supervisor.json',json.dumps({'result':result,'reason':reason,
            'ended_at_epoch':clock(),'container_retained':cid is not None})+'\n')
    return result

if __name__=='__main__':
    sys.exit(supervise(sys.argv[1],int(os.environ['DEMO_STOP_EPOCH'])+10))
