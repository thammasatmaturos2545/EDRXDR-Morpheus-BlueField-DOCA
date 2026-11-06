"""Read-only normalized projection audit. No raw journal or key/model access."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, re, sqlite3, time

ROOT = Path('/mnt/nexus-copilot-mQTssj/dfp-prospective-data/dfp-prospective-observation-pysjui5a')
COLLECTOR = Path('/mnt/nexus-copilot-mQTssj/dfp-observer-v2-package-w1WF8PGn/dfp-prospective-observer')
FIELDS = {'schema_version','journal_record_ref','event_time_utc','poll_observed_at_utc',
    'query_snapshot_sha256','query_row','status','reason','event_kind','subject_role',
    'subject_ref','actor_ref','target_ref','attempt_ref','source_ip_ref','model_scored',
    'window_complete','source_coverage_accepted','training_eligible','identity_scope'}
KINDS = {'ssh_auth_success','ssh_auth_failure','ssh_invalid_user_attempt',
         'pam_session_open','pam_session_close','pam_auth_failure','sudo_invocation'}
REASONS = {'unsupported_message_format','invalid_journal_projection','invalid_source_port',
    'pam_service_program_conflict','cron_context_not_auth_baseline','subject_field_missing',
    'invalid_projection_or_ip','account_outside_reviewed_cohort',
    'unverified_journal_format_identity_and_coverage'}
ROLES = {'attempted_name_not_verified_account','candidate_account','initiating_account',
         'session_target_account'}

def need(ok, message):
    if not ok:
        raise ValueError(message)

def parse(raw):
    def pairs(items):
        output = {}
        for key, value in items:
            need(key not in output, 'Duplicate JSON key')
            output[key] = value
        return output
    return json.loads(raw, object_pairs_hook=pairs)

def reference(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None

def stamp(value):
    need(type(value) is str and len(value) <= 40, 'Invalid projection time')
    moment = datetime.fromisoformat(value.replace('Z','+00:00'))
    need(moment.tzinfo is not None and moment.utcoffset().total_seconds() == 0,
         'Expected UTC projection time')
    return moment.astimezone(timezone.utc)

def summarize(rows):
    reasons, kinds, statuses, role_counts = Counter(), Counter(), Counter(), Counter()
    buckets = {}
    identities = set()
    unknown_kind = with_subject = unknown_reasons = total = 0
    first = last = None
    maximum_lag = 0.0
    for identity, raw in rows:
        total += 1
        need(total <= 100000 and type(raw) is str and len(raw.encode()) <= 16384,
             'Projection audit row/byte bound')
        row = parse(raw)
        need(type(row) is dict and set(row) == FIELDS, 'Projection schema changed')
        need(reference(identity) and row['journal_record_ref'] == identity
             and identity not in identities, 'Projection record identity conflict')
        identities.add(identity)
        need(row['schema_version'] == 'bounded-journal-auth-observation-0'
             and row['identity_scope'] == 'bounded_journal_observation_candidate_not_legacy_event_uid',
             'Projection identity scope changed')
        need(reference(row['query_snapshot_sha256']) and type(row['query_row']) is int
             and 1 <= row['query_row'] <= 5000, 'Projection query coordinates invalid')
        need(all(row[key] is False for key in ('model_scored','window_complete',
             'source_coverage_accepted','training_eligible')), 'Safety flags changed')
        need(row['status'] in ('unscored','candidate_mapping_only_not_scored'),
             'Unknown projection status')
        for key in ('subject_ref','actor_ref','target_ref','attempt_ref','source_ip_ref'):
            need(row[key] is None or reference(row[key]), 'Private reference shape changed')
        need(row['event_kind'] is None or row['event_kind'] in KINDS, 'Unknown event kind')
        need(row['subject_role'] is None or row['subject_role'] in ROLES, 'Unknown subject role')
        event, observed = stamp(row['event_time_utc']), stamp(row['poll_observed_at_utc'])
        need(observed >= event, 'Projection timing inconsistent')
        maximum_lag = max(maximum_lag, (observed-event).total_seconds())
        first = event if first is None else min(first,event)
        last = event if last is None else max(last,event)
        bucket = int(event.timestamp())//300
        flags = buckets.setdefault(bucket,set())
        statuses[row['status']] += 1
        if row['status'] == 'unscored':
            reason = row['reason'] if row['reason'] in REASONS else 'other_unscored_reason_not_exported'
            reasons[reason] += 1
            unknown_reasons += int(reason == 'other_unscored_reason_not_exported')
            unknown_kind += int(row['event_kind'] is None)
            with_subject += int(row['subject_ref'] is not None)
            flags.add('unscored')
        else:
            need(row['event_kind'] in KINDS, 'Candidate missing event kind')
            kinds[row['event_kind']] += 1
            if row['subject_role'] is not None:
                role_counts[row['subject_role']] += 1
            flags.add('candidate')
    unscored = statuses['unscored']
    return {
        'status':'NORMALIZED_UNSCORED_ACCOUNTING_NOT_RAW_FORMAT_DIAGNOSIS',
        'snapshot_records':total, 'unique_records':len(identities),
        'candidate_records':statuses['candidate_mapping_only_not_scored'],
        'unscored_records':unscored,
        'unscored_record_fraction':unscored/total if total else None,
        'unscored_reason_counts':dict(reasons), 'candidate_event_kind_counts':dict(kinds),
        'candidate_subject_role_counts':dict(role_counts),
        'unscored_without_recoverable_event_kind':unknown_kind,
        'unscored_with_subject_ref':with_subject, 'masked_unknown_reason_rows':unknown_reasons,
        'observed_event_time_buckets':len(buckets),
        'buckets_containing_unscored':sum('unscored' in flags for flags in buckets.values()),
        'buckets_containing_both_candidate_and_unscored':sum(len(flags)==2 for flags in buckets.values()),
        'observed_event_span_seconds':(last-first).total_seconds() if first else 0,
        'maximum_first_poll_observation_lag_seconds':maximum_lag if total else None,
        'parser_subreason_retained':False, 'source_program_retained':False,
        'unscored_fraction_is_not_false_negative_rate':True,
        'source_coverage_accepted':False, 'baseline_accepted':False,
        'accepted_complete_windows':0, 'training_eligible_windows':0,
        'raw_messages_read':False, 'keys_read':False, 'model_invocations':0,
        'record_edits':0, 'observer_source_changes':False,
    }

def main():
    base = Path(__file__).resolve().parent
    for name, digest in json.loads((base/'observer-source-bindings.json').read_bytes()).items():
        need(Path(name).name == name and hashlib.sha256((COLLECTOR/name).read_bytes()).hexdigest()
             == digest, 'Original observer source binding changed')
    need(ROOT.resolve() == ROOT and not ROOT.is_symlink(), 'Observation root scope')
    info = ROOT.stat()
    need(info.st_uid == os.getuid() and info.st_mode & 0o777 == 0o700, 'Observation root permissions')
    path = ROOT/'observations-private.sqlite'
    info = path.lstat()
    need(path.is_file() and not path.is_symlink() and info.st_uid == os.getuid()
         and info.st_nlink == 1 and info.st_size <= 200*1024*1024, 'Database metadata bound')
    db = sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=1)
    start = time.monotonic()
    db.set_progress_handler(lambda:int(time.monotonic()-start>10),10000)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        columns = [row[1] for row in db.execute('PRAGMA table_info(records)')]
        need(columns == ['identity','fingerprint','projection'], 'Stored record schema changed')
        count = db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        need(count <= 100000, 'Snapshot record cap')
        def records():
            for item in db.execute('SELECT identity,projection FROM records'):
                need(time.monotonic()-start <= 10, 'Read-only audit deadline')
                yield item
        report = summarize(records())
        need(report['snapshot_records'] == count, 'Read snapshot accounting mismatch')
    finally:
        db.close()
    report.update(database_opened_read_only=True,
                  original_journal_queries=0, raw_values_exported=False,
                  snapshot_may_differ_from_live_receipt=True)
    print(json.dumps(report,sort_keys=True))
    print('READ_ONLY_PROJECTION_AUDIT_PASS; no observer restart/reclassification/model/GPU/key/raw-log access')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('STOP_PROJECTION_AUDIT',type(error).__name__,'details withheld; no automatic retry')
        raise SystemExit(1)
