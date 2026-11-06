"""Pure descriptive metrics for externally frozen decisions/reference cases. No fit/threshold search."""
from datetime import datetime
import hashlib, json, statistics

FIELDS = {'case_ref','entity_ref','partition','window_start','window_end','members',
          'label','label_evidence_sha256','coverage','scored','alert','detected_at'}
HASH_CHARS = set('0123456789abcdef')

def need(ok, message):
    if not ok:
        raise ValueError(message)

def ref(value):
    return type(value) is str and len(value)==64 and set(value)<=HASH_CHARS

def stamp(value):
    need(type(value) is str and len(value)<=40, 'Invalid case time')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    need(result.tzinfo is not None and result.utcoffset().total_seconds()==0,
         'UTC case time required')
    return result

def ratio(numerator,denominator):
    return numerator/denominator if denominator else None

def metrics(values):
    tp,fp,tn,fn=(values[key] for key in ('tp','fp','tn','fn'))
    return dict(values,n=tp+fp+tn+fn,precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),
                f1=ratio(2*tp,2*tp+fp+fn),false_positive_rate=ratio(fp,fp+tn))

def evaluate(cases,protocol,expected_protocol_sha256):
    need(type(protocol) is dict and set(protocol)=={
        'schema_version','pipeline','feature_contract','detector_artifact_sha256',
        'decision_policy_sha256','window_seconds','scope','endpoint_id'},'Exact protocol required')
    raw=json.dumps(protocol,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    need(ref(expected_protocol_sha256) and hashlib.sha256(raw).hexdigest()==expected_protocol_sha256,
         'External protocol pin mismatch')
    need(protocol['schema_version']=='dfp-evaluation-contract-draft-1'
         and protocol['pipeline']=='dfp' and protocol['scope']=='engineering_descriptive_only'
         and protocol['endpoint_id']=='003'
         and protocol['feature_contract']=='linux-journal-auth-observed-counts-engineering-0'
         and protocol['window_seconds']==300,'Unsupported evaluation contract')
    need(ref(protocol['detector_artifact_sha256']) and ref(protocol['decision_policy_sha256']),
         'Frozen artifact/policy bindings required')
    need(type(cases) is list and len(cases)<=10000,'Case bound')
    seen=set();membership=set();intervals={};partitions={};rows=[]
    for case in cases:
        need(type(case) is dict and set(case)==FIELDS,'Unknown/raw/missing case fields')
        need(ref(case['case_ref']) and case['case_ref'] not in seen and ref(case['entity_ref']),
             'Duplicate or invalid case/entity identity')
        seen.add(case['case_ref'])
        part=case['partition']
        need(part in ('fit','calibration','evaluation'),'Unknown partition')
        start,end=stamp(case['window_start']),stamp(case['window_end'])
        need((end-start).total_seconds()==300 and start.microsecond==0
             and int(start.timestamp())%300==0,'Window contract mismatch')
        partitions.setdefault(part,[]).append((start,end))
        intervals.setdefault(case['entity_ref'],[]).append((start,end))
        members=case['members']
        need(type(members) is list and 1<=len(members)<=500,'Source membership bound')
        for member in members:
            need(ref(member) and member not in membership,'Duplicate membership or split leakage')
            membership.add(member)
        need(len(membership)<=100000,'Total membership bound')
        label=case['label']
        need(label in ('positive','negative','unknown'),'Reference label missing/invalid')
        need(case['label_evidence_sha256'] is None if label=='unknown'
             else ref(case['label_evidence_sha256']),'Reference evidence binding required')
        need(case['coverage'] in ('accepted','unknown','incomplete'),'Coverage scope required')
        need(type(case['scored']) is bool,'Scored status must be explicit')
        need(type(case['alert']) is bool if case['scored'] else case['alert'] is None,
             'Unscored case cannot be silently converted to a negative')
        if case['alert'] is True:
            detected=stamp(case['detected_at'])
            need(detected>=end,'Closed-window detection cannot precede window end')
        else:
            need(case['detected_at'] is None,'No-alert case has no detection timestamp')
        rows.append((case,start,end))
    need(len(intervals)<=1,'Evaluate each account-specific model separately')
    for entity,values in intervals.items():
        ordered=sorted(values)
        need(all(b[0]>=a[1] for a,b in zip(ordered,ordered[1:])),
             'Overlapping cases for same entity')
    order=['fit','calibration','evaluation']
    for index,left in enumerate(order):
        for right in order[index+1:]:
            if left in partitions and right in partitions:
                need(max(end for _,end in partitions[left])<=min(start for start,_ in partitions[right]),
                     'Nonchronological split overlap')
    scored={key:0 for key in ('tp','fp','tn','fn')}
    pipeline={key:0 for key in ('tp','fp','tn','fn')}
    counts={'evaluation_cases':0,'excluded_unknown_coverage':0,'excluded_incomplete_coverage':0,
            'excluded_unknown_reference':0,'eligible_reference_cases':0,
            'eligible_scored_cases':0,'positive_unscored_cases':0,'negative_unscored_cases':0}
    negative_seconds=0;latencies=[]
    for case,start,end in rows:
        if case['partition']!='evaluation':
            continue
        counts['evaluation_cases']+=1
        # Independent reasons are counted nonexclusively.
        counts['excluded_unknown_coverage']+=int(case['coverage']=='unknown')
        counts['excluded_incomplete_coverage']+=int(case['coverage']=='incomplete')
        counts['excluded_unknown_reference']+=int(case['label']=='unknown')
        if case['coverage']!='accepted' or case['label']=='unknown':
            continue
        counts['eligible_reference_cases']+=1
        positive=case['label']=='positive'
        if not positive:
            negative_seconds+=(end-start).total_seconds()
        if case['scored']:
            counts['eligible_scored_cases']+=1
            key=('tp' if positive else 'fp') if case['alert'] else ('fn' if positive else 'tn')
            scored[key]+=1
            if positive and case['alert']:
                latencies.append((stamp(case['detected_at'])-end).total_seconds())
        else:
            counts['positive_unscored_cases' if positive else 'negative_unscored_cases']+=1
        # Pipeline outcome: no emitted alert on known covered positive is a missed case.
        emitted=case['scored'] and case['alert'] is True
        key=('tp' if positive else 'fp') if emitted else ('fn' if positive else 'tn')
        pipeline[key]+=1
    hours=negative_seconds/3600
    return {'schema_version':'dfp-descriptive-evaluation-draft-1',
        'scope':'engineering_descriptive_only','protocol_sha256':expected_protocol_sha256,
        'case_count':len(cases),'entity_count':len(intervals),'source_memberships_checked':len(membership),
        'case_accounting':counts,
        'exclusion_reason_counts_are_nonexclusive':True,
        'conditional_scored_case_metrics':metrics(scored),
        'end_to_end_eligible_case_metrics':metrics(pipeline),
        'eligible_case_scoring_fraction':ratio(counts['eligible_scored_cases'],counts['eligible_reference_cases']),
        'labelled_negative_entity_hours':hours if negative_seconds else None,
        'false_alerts_per_labelled_negative_entity_hour':ratio(pipeline['fp'],hours),
        'true_positive_window_end_to_alert_seconds':{
            'count':len(latencies),'median':statistics.median(latencies) if latencies else None,
            'maximum':max(latencies) if latencies else None},
        'independent_label_authenticity_verified_by_this_function':False,
        'coverage_claims_verified_by_this_function':False,'quality_acceptance':False,
        'threshold_selected_by_this_function':False,'model_invocations':0,'training_performed':False,
        'production_ready':False,'automated_response_allowed':False}
