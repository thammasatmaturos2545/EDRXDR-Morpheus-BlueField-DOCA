from pathlib import Path
import fcntl, hashlib, json, os, re, shutil, socket, stat, subprocess, sys, tempfile, time, math
import xml.etree.ElementTree as ET
CONFIG=Path('/var/ossec/etc/ossec.conf')
BASE=Path('/var/lib/edrxdr-endpoint-probes')

def digest(b): return hashlib.sha256(b).hexdigest()
def patch(raw, directory):
    text=raw.decode('utf-8')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper(): raise ValueError('XML declarations rejected')
    doc=ET.fromstring('<root>'+text+'</root>')
    blocks=doc.findall('.//syscheck')
    if len(blocks)!=1 or (blocks[0].findtext('disabled') or '').strip()!='no':
        raise ValueError('Expected one enabled syscheck block')
    if len(re.findall(r'</syscheck\s*>',text))!=1: raise ValueError('Ambiguous closing tag')
    if not re.fullmatch(r'/var/lib/edrxdr-endpoint-probes/probe-[a-z0-9_]+/files',directory):
        raise ValueError('Unexpected probe directory')
    entry='\n    <directories realtime="yes" check_all="yes" report_changes="no">'+directory+'</directories>\n'
    updated=re.sub(r'</syscheck\s*>',lambda m:entry+m.group(),text,count=1).encode()
    ET.fromstring('<root>'+updated.decode()+'</root>')
    return updated

def verified_agent_type(value):
    return value.strip() == 'agent' or re.fullmatch(r"WAZUH_TYPE=(?:agent|\"agent\"|'agent')", value.strip()) is not None

def command(args,timeout=60):
    r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if r.returncode: raise RuntimeError('Command failed: '+Path(args[0]).name)
    return r.stdout.decode(errors='replace').strip()

def write_config(raw, meta):
    if CONFIG.is_symlink() or not CONFIG.is_file(): raise RuntimeError('Config changed type')
    # Preserve owner/mode and replace atomically in the existing directory.
    fd,name=tempfile.mkstemp(prefix='.edrxdr-probe-',dir=str(CONFIG.parent))
    try:
        os.fchmod(fd,meta['mode']);os.fchown(fd,meta['uid'],meta['gid'])
        with os.fdopen(fd,'wb') as f: f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(name,CONFIG)
    finally:
        if os.path.exists(name): os.unlink(name)

def restore(root):
    receipt=json.loads((root/'receipt.json').read_text())
    with (root/'restore.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        original=(root/'original.conf').read_bytes()
        if digest(original)!=receipt['original_sha256']: raise RuntimeError('Backup hash mismatch')
        current=CONFIG.read_bytes()
        if digest(current)==receipt['proposed_sha256']:
            write_config(original,receipt)
        elif current!=original:
            # Do not overwrite concurrent administrator edits. Remove only our exact entry.
            entry=receipt['entry'].encode()
            if current.count(entry)!=1: raise RuntimeError('Concurrent change needs manual review; backup retained')
            replacement=current.replace(entry,b'',1)
            ET.fromstring('<root>'+replacement.decode()+'</root>')
            write_config(replacement,receipt)
        command(['/var/ossec/bin/wazuh-syscheckd','-t'])
        if not (root/'restored.json').exists():
            command(['systemctl','restart','wazuh-agent'],120)
            command(['systemctl','is-active','--quiet','wazuh-agent'])
            (root/'restored.json').write_text(json.dumps({'status':'PROBE_CONFIG_REMOVED_AGENT_ACTIVE',
                'original_bytes_restored':CONFIG.read_bytes()==original}))
    print('RESTORE_PASS; agent active; test artifacts retained',flush=True)

CASES=(('quiet-small-edits',4,2),('normal-bulk-update',8,0),('controlled-fast-update',8,0))

def content(case_id,index):
    if case_id not in {case[0] for case in CASES} or type(index)is not int or not 0<=index<12:
        raise ValueError('Owned scenario/index required')
    return ('synthetic owned text '+case_id+' '+str(index)+'\n').encode()

def manager_identity():
    ids=command(['docker','ps','--no-trunc','--filter','label=com.docker.compose.project=wazuh',
        '--filter','label=com.docker.compose.service=wazuh.manager','--format','{{.ID}}']).split()
    if len(ids)!=1 or not re.fullmatch('[a-f0-9]{64}',ids[0]):raise RuntimeError('Ambiguous group manager')
    fmt='{"id":{{json .Id}},"running":{{json .State.Running}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}}}'
    actual=json.loads(command(['docker','inspect','--format',fmt,ids[0]]))
    if actual!={'id':ids[0],'running':True,'project':'wazuh','service':'wazuh.manager'}:
        raise RuntimeError('Group manager metadata changed')
    fields={}
    for line in command(['docker','exec',ids[0],'/var/ossec/bin/agent_control','-i','003']).splitlines():
        key,sep,value=line.strip().partition(':')
        if sep:fields[key.strip().lower()]=value.strip()
    if fields.get('agent id')!='003' or fields.get('status','').lower()!='active' or fields.get('agent name') not in (socket.gethostname(),socket.getfqdn()):
        raise RuntimeError('Local Agent003 context not matched')
    return ids[0]

def expected_matches(files):
    return {(str(files/f'normal-{index:02}.txt'),digest(content(case_id,index))):case_id
            for case_id,count,_ in CASES for index in range(count)}

def summarize(raw,files):
    lookup=expected_matches(files);counts={case[0]:set() for case in CASES};case_events={case[0]:0 for case in CASES};seen={}
    duplicates=unmatched=foreign=wrong_mode=missing_identity=0
    for n,line in enumerate(raw.splitlines()):
        try:row=json.loads(line)
        except (ValueError,UnicodeError):
            if n==0 and len(raw)==8388608:continue
            raise ValueError('Malformed bounded alert sample')
        if type(row)is not dict:continue
        sc=row.get('syscheck')
        if type(sc)is not dict or type(sc.get('path'))is not str:continue
        path=sc['path']
        if not path.startswith(str(files)+'/'):continue
        if type(row.get('agent'))is not dict or row['agent'].get('id')!='003':foreign+=1;continue
        key=(path,sc.get('sha256_after'))
        if key not in lookup:unmatched+=1;continue
        if sc.get('event')!='modified' or sc.get('mode')!='realtime':wrong_mode+=1;continue
        identity=row.get('id')
        if type(identity)is not str or not identity:missing_identity+=1;continue
        fingerprint=digest(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())
        if identity in seen:
            if seen[identity]!=fingerprint:raise ValueError('Conflicting delivery identity')
            duplicates+=1;continue
        seen[identity]=fingerprint;counts[lookup[key]].add(path);case_events[lookup[key]]+=1
    complete=all(len(counts[case_id])==count for case_id,count,_ in CASES) and not (foreign or wrong_mode or missing_identity)
    signatures={case_id:{'modified_unique_paths':len(paths),'modified_events':case_events[case_id],'added':0,'deleted':0} for case_id,paths in counts.items()}
    return {'status':'CONTROLLED_FILE_BEHAVIOR_DELIVERY_PASS_NOT_DETECTION_QUALITY' if complete else 'CONTROLLED_DELIVERY_INCOMPLETE_NEEDS_REVIEW',
        'expected_modifications':{case_id:count for case_id,count,_ in CASES},
        'received_unique_modified_paths':{case_id:len(paths) for case_id,paths in counts.items()},
        'received_modified_event_counts':case_events,
        'all20_owned_modifications_matched_by_path_and_after_hash':complete,
        'normal_bulk_and_controlled_fast_have_same_case_aggregate_signature':
            signatures['normal-bulk-update']==signatures['controlled-fast-update'] if complete else None,
        'identical_delivery_retries':duplicates,'foreign_agent_matches':foreign,
        'wrong_mode_or_event_matches':wrong_mode,'missing_delivery_identity_matches':missing_identity,
        'other_target_events_not_used':unmatched,'scenario_labels_are_not_malware_ground_truth':True,
        'ransomware_detection_verified':False,'source_coverage_accepted':False,'threshold_selected':False,
        'model_invocations':0,'raw_values_exported':False}

def apply():
    if os.geteuid()!=0: raise RuntimeError('Run with sudo for local agent config only')
    if BASE.is_symlink(): raise RuntimeError('Unsafe base')
    BASE.mkdir(mode=0o700,exist_ok=True)
    bs=BASE.stat()
    if bs.st_uid!=0 or stat.S_IMODE(bs.st_mode)!=0o700: raise RuntimeError('Unsafe base ownership/mode')
    global_lock=(BASE/'active.lock').open('a')
    fcntl.flock(global_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if any(d.is_dir() and d.name.startswith('probe-') and (d/'receipt.json').exists() and not (d/'restored.json').exists() for d in BASE.iterdir()):
        raise RuntimeError('Previous probe not certified restored; inspect before another run')
    if shutil.disk_usage(BASE).free<1024**3: raise RuntimeError('Less than 1GiB free')
    if CONFIG.is_symlink() or CONFIG.stat().st_nlink!=1: raise RuntimeError('Unsafe config')
    command(['systemctl','is-active','--quiet','wazuh-agent'])
    command(['/var/ossec/bin/wazuh-syscheckd','-t'])
    # Refuse a manager installation: this probe is for the local agent only.
    info=command(['/var/ossec/bin/wazuh-control','info','-t'])
    if not verified_agent_type(info):
        raise RuntimeError('Local Wazuh installation is not verified agent type')
    manager=manager_identity()
    root=Path(tempfile.mkdtemp(prefix='probe-',dir=BASE));os.chmod(root,0o700)
    files=root/'files';files.mkdir(mode=0o700)
    for i in range(12): (files/f'normal-{i:02}.txt').write_text('synthetic plain text baseline\n')
    raw=CONFIG.read_bytes();st=CONFIG.stat();proposed=patch(raw,str(files))
    entry=(
        '\n    <directories realtime="yes" check_all="yes" report_changes="no">'+str(files)+'</directories>\n')
    receipt={'original_sha256':digest(raw),'proposed_sha256':digest(proposed),
             'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'entry':entry,
             'purpose':'controlled_file_behavior_comparison_not_ransomware_quality'}
    (root/'original.conf').write_bytes(raw)
    (root/'receipt.json').write_text(json.dumps(receipt))
    helper=root/'probe.py';shutil.copyfile(Path(__file__).resolve(),helper);os.chmod(helper,0o600)
    unit='edrxdr-fim-restore-'+root.name
    command(['systemd-run','--unit='+unit,'--on-active=10m','--timer-property=AccuracySec=1s',
             '--property=TimeoutStartSec=180','/usr/bin/python3','-B',str(helper),'--restore',str(root)])
    command(['systemctl','is-active','--quiet',unit+'.timer'])
    print('RESTORE_TIMER_ARMED; maximum 10 minutes',flush=True)
    try:
        if CONFIG.read_bytes()!=raw: raise RuntimeError('Config changed before activation')
        write_config(proposed,receipt)
        command(['/var/ossec/bin/wazuh-syscheckd','-t'])
        command(['systemctl','restart','wazuh-agent'],120)
        command(['systemctl','is-active','--quiet','wazuh-agent'])
        for i in range(4):
            print('BASELINE_WAIT_SECONDS',i*30,'; scan completion not yet verified',flush=True);time.sleep(30)
        cases=[]
        first=math.ceil(time.time()/60)*60+2
        end_by=time.monotonic()+240
        for number,(case_id,count,delay) in enumerate(CASES):
            target=first+number*60
            while time.time()<target:
                if time.monotonic()>end_by:raise RuntimeError('Controlled case deadline reached')
                time.sleep(min(1,target-time.time()))
            case={'case_id':case_id,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'owned_modifications':count,'purpose':'controlled-reference-scenario-not-attack-label'}
            for index in range(count):
                path=files/f'normal-{index:02}.txt'
                fd=os.open(path,os.O_WRONLY|os.O_TRUNC|os.O_NOFOLLOW)
                with os.fdopen(fd,'wb') as f:f.write(content(case_id,index));f.flush();os.fsync(f.fileno())
                if delay:time.sleep(delay)
            case['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());cases.append(case)
            (root/'controlled-cases-private.json').write_text(json.dumps({'cases':cases,'expected_reference_hashes_bound_in_script':True}))
            print('CASE_OPERATIONS_SUBMITTED',case_id,count,'; delivery not yet verified',flush=True)
        time.sleep(30)
        if manager_identity()!=manager:raise RuntimeError('Group manager identity changed')
        result=subprocess.run(['docker','exec',manager,'tail','-c','8388608','/var/ossec/logs/alerts/alerts.json'],capture_output=True,timeout=30,check=True)
        report=summarize(result.stdout,files)
        (root/'comparison-aggregate.json').write_text(json.dumps(report,sort_keys=True))
        print(json.dumps(report,sort_keys=True),flush=True)

    finally:
        restore(root)
    print('PRIVATE_REPORT_DIRECTORY',root)
    print('CONTROLLED_COMPARISON_FINISHED; no malware/model/GPU/BlueField; production detection unchanged')

if __name__=='__main__':
    os.umask(0o077)
    try:
        if sys.argv[1:]==['--apply-approved-controlled-comparison']: apply()
        elif sys.argv[1:]==['--describe-plan']:
            print(json.dumps({'scope':'Agent003 fresh owned scratch folder only','files':12,'cases':[{'case_id':a,'modifications':b} for a,b,_ in CASES],'expected_total_modifications':20,'independent_restore_timer_minutes':10,'local_wazuh_agent_restarts':'activation and restoration','preview_only_no_apply':True},sort_keys=True))
        elif len(sys.argv)==3 and sys.argv[1]=='--restore':
            root=Path(sys.argv[2]).resolve()
            if root.parent!=BASE or not re.fullmatch(r'probe-[a-z0-9_]+',root.name): raise ValueError('Invalid restore root')
            restore(root)
        else: raise ValueError('Explicit apply or restore argument required')
    except Exception as exc:
        print('STOP',type(exc).__name__,str(exc),'; preserve private artifacts; no automatic retry')
        sys.exit(1)
