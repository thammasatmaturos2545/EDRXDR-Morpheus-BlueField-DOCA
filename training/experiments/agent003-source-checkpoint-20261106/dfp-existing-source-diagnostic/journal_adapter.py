"""Narrow journal message parser; no Wazuh decoder or rule IDs fabricated."""
import re
SCHEMA='linux-journal-auth-projection-candidate-0'
SSH={'sshd','sshd-session'}
PROGRAMS=SSH|{'sudo','su','login','cron','crond'}
def fail(reason):
    return dict(schema_version=SCHEMA,source_program=None,event_kind=None,data={},pam_service=None,parse_status=reason)
def project(message,program):
    if program not in PROGRAMS:return fail('unsupported_source_program')
    if type(message) is not str:return fail('nontext_message')
    if len(message.encode('utf-8'))>32768:return fail('message_too_large')
    if '\n' in message or '\r' in message:return fail('multiline_message_unverified')
    text=re.sub(r'^(?:sshd|sshd-session|sudo)(?:\[\d+\])?:\s*','',message)
    kind=None;data={};service=None
    if program in SSH:
        m=re.fullmatch(r'Accepted (?:password|publickey|keyboard-interactive(?:/pam)?) for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)(?:\s+[^\r\n]*)?',text)
        if m:kind='ssh_auth_success';data={'dstuser':m['user'],'srcip':m['ip'],'srcport':m['port']}
        if kind is None:
            m=re.fullmatch(r'Failed (?:password|publickey|keyboard-interactive(?:/pam)?) for (?P<invalid>invalid user )?(?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)(?:\s+[^\r\n]*)?',text)
            if m:
                kind='ssh_invalid_user_attempt' if m['invalid'] else 'ssh_auth_failure'
                data={'srcuser' if m['invalid'] else 'dstuser':m['user'],'srcip':m['ip'],'srcport':m['port']}
        if kind is None:
            m=re.fullmatch(r'Invalid user (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)(?:\s+[^\r\n]*)?',text)
            if m:kind='ssh_invalid_user_attempt';data={'srcuser':m['user'],'srcip':m['ip'],'srcport':m['port']}
    if kind is None:
        m=re.fullmatch(r'pam_unix\((?P<service>[A-Za-z0-9_.-]{1,64}):session\): session (?P<action>opened|closed) for user (?P<user>[^\s()]{1,256})(?:\(uid=\d+\))?(?: by (?P<actor>[^\s()]{1,256})?\(uid=(?P<uid>\d+)\))?\s*',text)
        if m:
            kind='pam_session_open' if m['action']=='opened' else 'pam_session_close';service=m['service']
            data={'dstuser':m['user']}
            if m['actor']:data['srcuser']=m['actor']
            if m['uid']:data['uid']=m['uid']
    if kind is None and text.startswith('pam_unix('):
        m=re.match(r'pam_unix\((?P<service>[A-Za-z0-9_.-]{1,64}):auth\): authentication failure(?:;|$)',text)
        if m:
            users=re.findall(r'(?:^|[;\s])user=([^\s;]+)',text)
            if len(users)==1:kind='pam_auth_failure';service=m['service'];data={'dstuser':users[0]}
    if kind is None and program=='sudo':
        m=re.fullmatch(r'\s*(?P<actor>[^\s:]{1,256})\s*:\s*TTY=[^;\r\n]{1,256};\s*PWD=[^;\r\n]{1,1024};\s*USER=(?P<target>[^;\s]{1,256})\s*;\s*COMMAND=[^\r\n]+',text)
        if m:kind='sudo_invocation';data={'srcuser':m['actor'],'dstuser':m['target']}
    if kind is None:return fail('unsupported_message_format')
    return dict(schema_version=SCHEMA,source_program=program,event_kind=kind,data=data,pam_service=service,parse_status='format_candidate')
def route(value):
    d=dict(status='unscored',reason='invalid_journal_projection',event_kind=None,subject_field=None,
           subject_role=None,secondary_field=None,profile_scope=None)
    if type(value) is not dict or set(value)!={'schema_version','source_program','event_kind','data','pam_service','parse_status'}:return d
    if value['schema_version']!=SCHEMA or type(value['data']) is not dict:return d
    if value['parse_status']!='format_candidate':d['reason']='unsupported_message_format';return d
    program=value['source_program'];kind=value['event_kind'];data=value['data'];service=value['pam_service']
    if program not in PROGRAMS or not set(data)<={'srcuser','dstuser','srcip','srcport','uid'}:return d
    if any(type(v) is not str or not v.strip() or len(v)>256 or any(ord(c)<32 or ord(c)==127 for c in v) for v in data.values()):return d
    if 'srcport' in data and (not data['srcport'].isdecimal() or not 1<=int(data['srcport'])<=65535):d['reason']='invalid_source_port';return d
    if kind in ('ssh_auth_success','ssh_auth_failure','ssh_invalid_user_attempt'):
        if program not in SSH or service is not None:return d
        field='srcuser' if kind=='ssh_invalid_user_attempt' else 'dstuser'
        role='attempted_name_not_verified_account' if field=='srcuser' else 'candidate_account'
        if field=='srcuser' and 'dstuser' in data:return d
    elif kind=='sudo_invocation':
        if program!='sudo' or service is not None:return d
        field='srcuser';role='initiating_account'
    elif kind in ('pam_session_open','pam_session_close','pam_auth_failure'):
        if service!=program and not (program=='sshd-session' and service=='sshd'):
            d['reason']='pam_service_program_conflict';return d
        if service in ('cron','crond'):
            d['reason']='cron_context_not_auth_baseline';return d
        field='dstuser';role='session_target_account' if kind!='pam_auth_failure' else 'candidate_account'
    else:return d
    if field not in data:d['reason']='subject_field_missing';return d
    d.update(status='candidate_mapping_only_not_scored',reason='unverified_journal_format_identity_and_coverage',
             event_kind=kind,subject_field=field,subject_role=role,
             profile_scope='endpoint_attempt_context_only' if kind=='ssh_invalid_user_attempt' else 'account_candidate_not_approved')
    return d
