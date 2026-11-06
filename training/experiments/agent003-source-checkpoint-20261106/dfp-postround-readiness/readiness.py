"""Final observer integrity review, separate from coverage/model quality acceptance."""
from pathlib import Path
from datetime import datetime, timedelta
import argparse, hashlib, json, os, sqlite3, subprocess, tempfile, time
from projection_audit import summarize, stamp

ROOT = Path('/mnt/nexus-copilot-mQTssj/dfp-prospective-data/dfp-prospective-observation-pysjui5a')
COLLECTOR = Path('/mnt/nexus-copilot-mQTssj/dfp-observer-v2-package-w1WF8PGn/dfp-prospective-observer')
UNIT = 'edrxdr-dfp-auth-prospective-pysjui5a.service'
BASE = Path('/mnt/nexus-copilot-mQTssj')

def need(ok,message):
    if not ok:
        raise ValueError(message)

def private(path,limit):
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        before = os.fstat(stream.fileno())
        need(before.st_uid==os.getuid() and before.st_nlink==1
             and before.st_mode&0o777==0o600 and before.st_size<=limit,
             'Private observer artifact metadata mismatch')
        raw=stream.read(limit+1)
        after=os.fstat(stream.fileno())
        need(len(raw)<=limit and (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
             (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),
             'Observer artifact changed during read')
        return raw

def evaluate(receipt,projection,polls,unit,db_ok,bound_hash,account_windows,accounts):
    start=stamp(receipt['observation_started_utc'])
    maximum=receipt['maximum_seconds']
    need(type(maximum) is int and 1<=maximum<=86400,'Approved duration metadata invalid')
    end=start+timedelta(seconds=maximum)
    need(type(polls) is list and 1<=len(polls)<=4000,'Poll-ledger bound')
    clock_ok=True;gaps=[];previous=None;caps=[];free=[];monotonic=[]
    for item in polls:
        observed=stamp(item['observed_at_utc'])
        elapsed=item['elapsed_monotonic_seconds']
        need(type(elapsed) in (int,float) and 0<=elapsed<=maximum,
             'Ledger elapsed value outside approved interval')
        clock_ok &= abs((observed-start).total_seconds()-elapsed)<=5
        if previous is not None:
            gaps.append((observed-previous).total_seconds())
        previous=observed;monotonic.append(elapsed)
        caps.append(item['returned_rows']);free.append(item['free_disk_bytes'])
    totals_match=(receipt['records_preserved']==projection['snapshot_records']
        and receipt['polls_committed']==len(polls)
        and receipt['candidate_event_kind_counts']==projection['candidate_event_kind_counts']
        and receipt['unscored_reason_counts']==projection['unscored_reason_counts']
        and receipt['observed_account_time_buckets']==account_windows
        and receipt['candidate_account_count']==accounts)
    checks={
        'final_receipt_sha256_bound':bound_hash,
        'observer_finished_normally':receipt['status']=='OBSERVATION_FINISHED_NOT_QUALITY_ACCEPTANCE'
            and receipt.get('failure_type') is None,
        'original_unit_not_running':unit.get('ActiveState') in ('inactive','failed')
            or unit.get('LoadState')=='not-found',
        'original_unit_success_result':unit.get('LoadState')=='not-found'
            or (unit.get('Result')=='success' and unit.get('ExecMainStatus')=='0'),
        'sqlite_quick_check_ok':db_ok,'receipt_projection_ledger_counts_match':totals_match,
        'ledger_clock_alignment_within_original_5s_guard':bool(clock_ok),
        'poll_times_strictly_increasing':all(gap>0 for gap in gaps)
            and all(b>a for a,b in zip(monotonic,monotonic[1:])),
        'first_poll_near_start':0<=monotonic[0]<=5,
        'last_poll_near_original_deadline':-5<=(end-previous).total_seconds()<=60,
        'polls_below_original_5000_record_query_cap':all(type(x)is int and 0<=x<=5000 for x in caps),
        'recorded_free_disk_above_original_10GiB_guard':all(type(x)is int and x>=10*1024**3 for x in free),
        'record_elapsed_duration_reached_original_maximum':abs(receipt['seconds_observed']-maximum)<=1,
        'stored_record_times_within_approved_interval':projection['record_times_inside_approved_interval'],
        'safety_flags_not_promoted':all(receipt.get(k)is False for k in
            ('source_coverage_accepted','baseline_accepted','training_performed','gpu_used','automated_response_allowed'))
            and receipt.get('model_invocations')==0}
    return {
        'status':'FINAL_CAPTURE_TECHNICAL_CHECK_PASS_NOT_QUALITY_ACCEPTANCE'
            if all(checks.values()) else 'FINAL_CAPTURE_TECHNICAL_CHECK_NEEDS_REVIEW',
        'technical_checks':{k:'pass' if v else 'fail' for k,v in checks.items()},
        'snapshot_records':projection['snapshot_records'],'candidate_records':projection['candidate_records'],
        'unscored_records':projection['unscored_records'],
        'candidate_event_kind_counts':projection['candidate_event_kind_counts'],
        'unscored_reason_counts':projection['unscored_reason_counts'],
        'account_count':accounts,'observed_account_time_buckets':account_windows,
        'polls':len(polls),'maximum_poll_gap_seconds':max(gaps) if gaps else None,
        'poll_gaps_over_45_seconds':sum(gap>45 for gap in gaps),
        'last_poll_to_authorized_source_deadline_seconds':(end-previous).total_seconds(),
        'poll_gap_metrics_do_not_prove_source_completeness':True,
        'acceptance':{name:'not_assessed' for name in (
            'physical_endpoint_identity','source_exposure_and_retention','representative_normal_baseline',
            'experimental_activity_context','independent_reference_labels',
            'threshold_calibration','independent_detection_quality','trusted_live_producer')},
        'training_allowed_by_this_audit':False,'new_observer_allowed':False,
        'threshold_selected':False,'bert_replacement_allowed':False,'automated_response_allowed':False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit-original-completed-round',action='store_true')
    args=parser.parse_args()
    need(args.audit_original_completed_round and os.geteuid()!=0,'Explicit audit flag and ordinary user required')
    need(ROOT.resolve()==ROOT and not ROOT.is_symlink()
         and ROOT.stat().st_uid==os.getuid() and ROOT.stat().st_mode&0o777==0o700,'Original observation scope')
    receipt_raw=private(ROOT/'receipt.json',65536);receipt=json.loads(receipt_raw)
    result=subprocess.run(['systemctl','show',UNIT,'--no-pager','-p','LoadState','-p','ActiveState',
        '-p','SubState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True,timeout=15)
    unit=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    need(unit.get('LoadState') in ('loaded','not-found'),'Original unit metadata unavailable')
    if receipt['status']=='OBSERVING':
        need(unit.get('ActiveState') in ('active','activating','deactivating'),
             'Stale OBSERVING receipt but original unit not running; review without retry')
        print('WAIT_ORIGINAL_OBSERVER_COMPLETION; no source/DB/key/model reads; no new round or extension')
        return
    need(unit.get('ActiveState') not in ('active','activating','deactivating'),
         'Original unit still running/transitioning; do not touch')
    base=Path(__file__).resolve().parent
    for name,digest in json.loads((base/'source-bindings.json').read_bytes()).items():
        need(Path(name).name==name and hashlib.sha256((COLLECTOR/name).read_bytes()).hexdigest()==digest,
             'Original collector source binding changed')
    hashes=json.loads(private(ROOT/'aggregate-SHA256.json',65536))
    bound=hashes=={'receipt.json':hashlib.sha256(receipt_raw).hexdigest()}
    need(bound,'Final receipt hash mismatch')
    dbfile=ROOT/'observations-private.sqlite'
    before=dbfile.stat()
    need(not dbfile.is_symlink() and before.st_uid==os.getuid() and before.st_nlink==1
         and before.st_size<=200*1024*1024,'Final DB metadata bound')
    db=sqlite3.connect(dbfile.as_uri()+'?mode=ro',uri=True,timeout=1)
    started=time.monotonic()
    db.set_progress_handler(lambda:int(time.monotonic()-started>15),10000)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        need(db.execute('SELECT COUNT(*) FROM records').fetchone()[0]<=10000,
             'Final normalized-record audit cap exceeded')
        db_ok=db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        rows=list(db.execute('SELECT identity,projection FROM records'))
        projection=summarize(rows)
        account_buckets=set();accounts=set()
        start=stamp(receipt['observation_started_utc'])
        end=start+timedelta(seconds=receipt['maximum_seconds'])
        interval_ok=True
        for _,raw in rows:
            row=json.loads(raw)
            interval_ok &= start<=stamp(row['event_time_utc'])<=end
            if row['status']=='candidate_mapping_only_not_scored' and row['subject_ref'] is not None:
                accounts.add(row['subject_ref'])
                account_buckets.add((row['subject_ref'],int(stamp(row['event_time_utc']).timestamp())//300))
        projection['record_times_inside_approved_interval']=bool(interval_ok)
        need(db.execute('SELECT COUNT(*) FROM polls').fetchone()[0]<=4000,'Poll ledger cap exceeded')
        polls=[json.loads(row[0]) for row in db.execute('SELECT ledger FROM polls ORDER BY number')]
        report=evaluate(receipt,projection,polls,unit,db_ok,bound,len(account_buckets),len(accounts))
    finally:
        db.close()
    digest=hashlib.sha256()
    fd=os.open(dbfile,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        need(info.st_ino==before.st_ino and info.st_size==before.st_size,'Final DB inode changed')
        total=0
        while True:
            chunk=stream.read(1024*1024)
            if not chunk:
                break
            total+=len(chunk)
            need(total<=200*1024*1024 and time.monotonic()-started<=20,'DB hash size/time bound')
            digest.update(chunk)
    after=dbfile.stat()
    need((before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
         (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),
         'Final DB changed during audit; preserve originals')
    need(private(ROOT/'receipt.json',65536)==receipt_raw,'Final receipt changed during audit')
    report.update(observer_files_modified=False,raw_messages_read=False,keys_read=False,
                  model_invocations=0,reviewer_credentials_read=False,new_collection_started=False,
                  observation_db_sha256=digest.hexdigest(),
                  final_receipt_sha256=hashlib.sha256(receipt_raw).hexdigest())
    os.umask(0o077)
    out=Path(tempfile.mkdtemp(prefix='dfp-postround-readiness-',dir=BASE))
    raw=json.dumps(report,sort_keys=True,indent=2).encode()
    (out/'aggregate-report.json').write_bytes(raw)
    print(json.dumps(report,sort_keys=True))
    print('AGGREGATE_REPORT',out/'aggregate-report.json')
    print('REPORT_SHA256',hashlib.sha256(raw).hexdigest())

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print('POSTROUND_AUDIT_STOP',type(error).__name__,'details withheld; originals preserved; no automatic retry')
        raise SystemExit(1)
