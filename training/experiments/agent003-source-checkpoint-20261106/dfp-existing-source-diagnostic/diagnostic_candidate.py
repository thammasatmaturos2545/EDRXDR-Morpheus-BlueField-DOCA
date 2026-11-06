"""Finite diagnostic labels for a FUTURE adapter; not installed in any collector."""
from journal_adapter import route

PARSE = {'format_candidate','unsupported_source_program','nontext_message',
         'message_too_large','multiline_message_unverified','unsupported_message_format'}
ROUTE = {'invalid_journal_projection','unsupported_message_format','invalid_source_port',
         'pam_service_program_conflict','cron_context_not_auth_baseline','subject_field_missing',
         'unverified_journal_format_identity_and_coverage'}

def labels(projection, program):
    family = {'sshd':'ssh','sshd-session':'ssh','sudo':'sudo','su':'su',
              'login':'login','cron':'cron','crond':'cron'}.get(program,'other')
    if program is None:
        family = 'ambiguous_or_missing'
    value = projection.get('parse_status') if type(projection) is dict else None
    parse_status = value if type(value) is str and value in PARSE else 'other'
    result = route(projection)
    value = result['reason']
    reason = value if value in ROUTE else 'other'
    return {'schema_version':'parser-diagnostics-candidate-1','source_family':family,
            'parse_status':parse_status,'route_reason':reason}
