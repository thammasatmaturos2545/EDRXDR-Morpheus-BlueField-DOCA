"""Explicitly approved historical journal diagnostics only; no collection or writes."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse, hashlib, hmac, json, os, selectors, sqlite3, subprocess, time
from journal_adapter import project
from diagnostic_candidate import labels

ROOT = Path('/mnt/nexus-copilot-mQTssj/dfp-prospective-data/dfp-prospective-observation-pysjui5a')
COLLECTOR = Path('/mnt/nexus-copilot-mQTssj/dfp-observer-v2-package-w1WF8PGn/dfp-prospective-observer')
KEY = Path('/home/saiuser/edrxdr-nvidia-lab-znmqaTGL/dfp-auth-cpu-development-eoriljcd/source-refs-private.key')
PROGRAMS = ('sshd','sshd-session','sudo','su','login')
UNITS = ('ssh.service','sshd.service')
FIELDS = {'__SEQNUM','__SEQNUM_ID','__CURSOR','__REALTIME_TIMESTAMP',
          '__MONOTONIC_TIMESTAMP','_BOOT_ID','_SYSTEMD_UNIT','_COMM',
          'SYSLOG_IDENTIFIER','MESSAGE'}
MAX_ROWS = 1000
MAX_BYTES = 8 * 1024 * 1024

def need(ok, message):
    if not ok:
        raise ValueError(message)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),
                      ensure_ascii=False,allow_nan=False).encode()

def parse(raw):
    def pairs(values):
        result = {}
        for key,value in values:
            need(key not in result,'Duplicate source JSON key')
            result[key] = value
        return result
    return json.loads(raw,object_pairs_hook=pairs)

def mac(key, domain, *values):
    return hmac.new(key,canonical(['bounded-journal-auth-observation-0',domain,*values]),
                    hashlib.sha256).hexdigest()

def utc(value):
    need(type(value) is str and len(value)<=40,'Invalid UTC interval')
    value = datetime.fromisoformat(value.replace('Z','+00:00'))
    need(value.tzinfo is not None and value.utcoffset().total_seconds()==0,
         'UTC required')
    return value

def private_read(path,maximum):
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info = os.fstat(stream.fileno())
        need(info.st_uid==os.getuid() and info.st_nlink==1
             and info.st_mode&0o777==0o600 and info.st_size<=maximum,
             'Private source metadata mismatch')
        raw = stream.read(maximum+1)
        need(len(raw)<=maximum,'Private source size bound')
        return raw

def snapshot():
    need(ROOT.resolve()==ROOT and not ROOT.is_symlink()
         and ROOT.stat().st_uid==os.getuid()
         and ROOT.stat().st_mode&0o777==0o700,'Observation root scope')
    receipt = parse(private_read(ROOT/'receipt.json',65536))
    plan = parse(private_read(ROOT/'plan-private.json',1048576))
    start = utc(receipt['observation_started_utc'])
    dbfile = ROOT/'observations-private.sqlite'
    info = dbfile.lstat()
    need(dbfile.is_file() and not dbfile.is_symlink()
         and info.st_uid==os.getuid() and info.st_nlink==1
         and info.st_size<=200*1024*1024,'Read-only DB scope')
    db = sqlite3.connect(dbfile.as_uri()+'?mode=ro',uri=True,timeout=1)
    deadline = time.monotonic()+5
    db.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        count = db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        need(count<=MAX_ROWS,'Snapshot exceeds approved1000record bound')
        last = db.execute('SELECT ledger FROM polls ORDER BY number DESC LIMIT 1').fetchone()
        need(last is not None,'Poll ledger unavailable')
        end = utc(parse(last[0])['observed_at_utc'])
        expected = {}
        for identity,fingerprint,projection in db.execute('SELECT identity,fingerprint,projection FROM records'):
            row = parse(projection)
            if row['status']=='unscored' and row['reason']=='unsupported_message_format':
                expected[identity] = fingerprint
        need(start<=end and (end-start).total_seconds()<=86400,'Historical interval scope')
    finally:
        db.close()
    need(expected,'No target records require historical-source diagnosis')
    return count,start,end,expected,plan['experiment_key_sha256']

def query_args(start,end):
    args = ['sudo','-n','journalctl','--no-pager','--quiet',
            '--since',start.strftime('%Y-%m-%d %H:%M:%S.%f UTC'),
            '--until',end.strftime('%Y-%m-%d %H:%M:%S.%f UTC'),
            '--output=json',
            '--output-fields=MESSAGE,__REALTIME_TIMESTAMP,_SYSTEMD_UNIT,_COMM,SYSLOG_IDENTIFIER',
            '--lines=1001']
    terms = [field+'='+value for field in ('_COMM','SYSLOG_IDENTIFIER') for value in PROGRAMS]
    terms += ['_SYSTEMD_UNIT='+unit for unit in UNITS]
    for i,term in enumerate(terms):
        if i:
            args.append('+')
        args.append(term)
    return args

def bounded_query(args):
    # Only stdout is captured. No journal stderr/raw text is forwarded or persisted.
    child = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    selection = selectors.DefaultSelector()
    selection.register(child.stdout,selectors.EVENT_READ)
    chunks,total,deadline = [],0,time.monotonic()+20
    try:
        while True:
            need(time.monotonic()<deadline,'Historical query timeout')
            events = selection.select(timeout=0.2)
            if not events:
                continue
            chunk = os.read(child.stdout.fileno(),65536)
            if not chunk:
                break
            total += len(chunk)
            need(total<=MAX_BYTES,'Historical query byte cap exceeded')
            chunks.append(chunk)
        need(child.wait(timeout=2)==0,'Historical journal read failed; sudo cache/permissions may be unavailable')
        return b''.join(chunks)
    finally:
        selection.close()
        child.stdout.close()
        if child.poll() is None:
            child.kill()  # This exact child was started and owned by this helper.
            child.wait(timeout=3)

def summarize(raw,key,expected,start,end):
    need(type(raw) is bytes and len(raw)<=MAX_BYTES,'Source byte bound')
    lines = raw.splitlines()
    need(len(lines)<=MAX_ROWS,'Historical query reached approved row cap')
    need(type(key) is bytes and len(key)==32,'Exact reference key required')
    seen,matched = set(),set()
    causes,families,indicators,metadata_cases = Counter(),Counter(),Counter(),Counter()
    for line in lines:
        need(len(line)<=262144,'Source line bound')
        row = parse(line)
        need(type(row) is dict and set(row)<=FIELDS,'Historical source field contract changed')
        boot,cursor,stamp = row.get('_BOOT_ID'),row.get('__CURSOR'),row.get('__REALTIME_TIMESTAMP')
        need(type(boot) is str and len(boot)==32 and all(c in '0123456789abcdef' for c in boot)
             and type(cursor) is str and 1<=len(cursor)<=2048
             and type(stamp) is str and stamp.isdecimal(),'Historical identity fields unavailable')
        event = datetime.fromtimestamp(int(stamp)/1000000,timezone.utc)
        need(start<=event<=end,'Historical source outside snapshot interval')
        identity = mac(key,'journal_record',boot,cursor)
        need(identity not in seen,'Duplicate historical source identity')
        seen.add(identity)
        if identity not in expected:
            continue
        need(mac(key,'payload',row)==expected[identity],
             'Matched identity payload differs; no reclassification permitted')
        programs = set()
        for field in ('_COMM','SYSLOG_IDENTIFIER'):
            value = row.get(field)
            need(value is None or type(value) is str,'Historical source metadata shape')
            if value in PROGRAMS:
                programs.add(value)
        program = next(iter(programs)) if len(programs)==1 else None
        metadata_cases['one_selected_program' if len(programs)==1 else
                       'ambiguous_selected_programs' if programs else 'no_selected_program'] += 1
        projection = project(row.get('MESSAGE'),program)
        need(projection['parse_status'] != 'format_candidate',
             'Recovered parser outcome conflicts with stored unsupported reason')
        diagnostic = labels(projection,program)
        causes[diagnostic['parse_status']] += 1
        families[diagnostic['source_family']] += 1
        indicator = 'no_supported_format_indicator'
        message = row.get('MESSAGE')
        if type(message) is str and diagnostic['parse_status']=='unsupported_message_format':
            if program in ('sshd','sshd-session') and message.startswith((
                    'Connection closed by ','Connection reset by ','Disconnected from ',
                    'Received disconnect from ','Disconnecting ','Connection from ')):
                indicator = 'ssh_transport_notice_format_only'
            elif message.startswith('pam_unix('):
                indicator = 'other_pam_format_only'
            elif program=='sudo':
                indicator = 'other_sudo_format_only'
        indicators[indicator] += 1
        matched.add(identity)
    return {'status':'EXISTING_SOURCE_MATCHED_DIAGNOSTICS_NOT_SEMANTIC_ACCEPTANCE',
        'historical_source_rows_read':len(lines),'target_snapshot_unscored_records':len(expected),
        'exact_identity_and_payload_matched_targets':len(matched),
        'targets_not_recovered_from_current_retention':len(set(expected)-matched),
        'parser_stage_counts':dict(causes),'source_family_counts':dict(families),
        'metadata_selection_counts':dict(metadata_cases),'format_indicator_counts':dict(indicators),
        'format_indicators_are_not_auth_or_attack_ground_truth':True,
        'missing_source_is_not_benign':True,'baseline_accepted':False,
        'source_coverage_accepted':False,'records_reclassified_or_modified':0,
        'raw_messages_read_locally':True,'raw_messages_saved_or_exported':False,
        'reference_key_read_locally':True,'other_keys_read':False,
        'model_invocations':0,'training_performed':False,'gpu_used':False,
        'new_collector_started':False,'observer_modified':False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--approved-existing-source-review',action='store_true')
    args = parser.parse_args()
    need(args.approved_existing_source_review and os.geteuid()!=0,
         'Explicit approval flag and ordinary user required')
    base = Path(__file__).resolve().parent
    for name,digest in parse((base/'source-bindings.json').read_bytes()).items():
        need(Path(name).name==name and hashlib.sha256((COLLECTOR/name).read_bytes()).hexdigest()==digest,
             'Original collector source changed')
    count,start,end,expected,key_sha = snapshot()
    key = private_read(KEY,32)
    need(len(key)==32 and hashlib.sha256(key).hexdigest()==key_sha,'Reference key binding mismatch')
    raw = bounded_query(query_args(start,end))
    result = summarize(raw,key,expected,start,end)
    result['snapshot_records'] = count
    result['interval_start_utc'] = start.isoformat()
    result['interval_end_utc'] = end.isoformat()
    print(json.dumps(result,sort_keys=True))
    print('EXISTING_SOURCE_DIAGNOSTIC_COMPLETE; no raw text/identity/key values exported; originals unchanged')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('SOURCE_REVIEW_STOP',type(error).__name__,'details withheld; preserve originals; no automatic retry')
        raise SystemExit(1)
