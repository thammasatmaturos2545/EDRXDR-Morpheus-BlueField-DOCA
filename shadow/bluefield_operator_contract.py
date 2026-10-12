"""Offline contracts only. No broker, filesystem audit store, approval issuer or replay worker."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re

RUN = re.compile(r'[a-z0-9][a-z0-9-]{7,39}')
HASH = re.compile(r'[0-9a-f]{64}')
IDENTITY = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}')
ENVELOPE_FIELDS = {'schema_version', 'processing_mode', 'run_id', 'reason_code',
                   'error_type', 'validation_stage', 'input_sha256', 'quarantined_at_utc',
                   'historical', 'production_ready', 'automated_response_allowed', 'source'}


class Rejected(ValueError):
    """Stable reason code only: never embeds raw data or exception messages."""


def require(condition, code):
    if not condition:
        raise Rejected(code)


def exact(obj, keys, code):
    require(type(obj) is dict and set(obj) == set(keys), code)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def timestamp(value):
    require(type(value) is str, 'invalid_timestamp')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise Rejected('invalid_timestamp') from None
    require(dt.utcoffset() is not None, 'timestamp_without_timezone')
    return dt


def now_checked(now):
    require(isinstance(now, datetime) and now.utcoffset() is not None, 'invalid_clock')
    return now.astimezone(timezone.utc)


def token(value, pattern, code):
    require(type(value) is str and pattern.fullmatch(value) is not None, code)


def coordinates(source):
    exact(source, {'topic', 'partition', 'offset'}, 'invalid_source_fields')
    token(source['topic'], re.compile(r'shadow-bluefield-quarantine-input-[a-z0-9][a-z0-9-]{7,39}'), 'source_not_isolated')
    for field in ('partition', 'offset'):
        require(type(source[field]) is int and 0 <= source[field] <= 2**63 - 1, 'invalid_source_position')
    require(source['partition'] == 0, 'v1_requires_partition_zero')


def evidence(envelope, evidence_id):
    exact(envelope, ENVELOPE_FIELDS, 'invalid_envelope_fields')
    token(envelope['run_id'], RUN, 'invalid_run_id')
    coordinates(envelope['source'])
    require(envelope['source']['topic'] == 'shadow-bluefield-quarantine-input-' + envelope['run_id'], 'run_source_mismatch')
    require(envelope['schema_version'] == 'bluefield-quarantine-1' and
            envelope['processing_mode'] == 'shadow_quarantine' and
            envelope['reason_code'] == 'strict_validation_failed' and
            envelope['validation_stage'] == 'validate_review', 'invalid_quarantine_contract')
    require(envelope['historical'] is True and envelope['production_ready'] is False and
            envelope['automated_response_allowed'] is False, 'unsafe_flags')
    token(envelope['input_sha256'], HASH, 'invalid_input_hash')
    token(envelope['error_type'], IDENTITY, 'invalid_error_class')
    timestamp(envelope['quarantined_at_utc'])
    # Match checkpoint 829169b's document ID algorithm, including JSON spaces.
    identity = [envelope['run_id'], envelope['source']['topic'], envelope['source']['partition'],
                envelope['source']['offset'], envelope['input_sha256']]
    expected = hashlib.sha256(json.dumps(identity).encode('utf-8')).hexdigest()
    require(evidence_id == expected, 'evidence_id_mismatch')
    return digest(envelope)


def review_plan(envelope, evidence_id, destination, now):
    now = now_checked(now)
    evidence_hash = evidence(envelope, evidence_id)
    token(destination, re.compile(r'shadow-bluefield-controlled-replay-[a-z0-9][a-z0-9-]{7,39}'), 'destination_not_isolated')
    require(timestamp(envelope['quarantined_at_utc']) <= now, 'future_evidence')
    plan = {'schema_version': 'bluefield-operator-review-1', 'evidence_id': evidence_id,
            'evidence_sha256': evidence_hash, 'source': deepcopy(envelope['source']),
            'input_sha256': envelope['input_sha256'], 'destination_topic': destination,
            'reviewed_at_utc': now.isoformat(), 'max_records': 1,
            'historical': True, 'production_ready': False, 'automated_response_allowed': False}
    return {**plan, 'plan_sha256': digest(plan)}


def validate_plan(plan, envelope, evidence_id):
    require(type(plan) is dict and 'reviewed_at_utc' in plan and 'destination_topic' in plan, 'invalid_plan')
    expected = review_plan(envelope, evidence_id, plan['destination_topic'], timestamp(plan['reviewed_at_utc']))
    require(canonical(plan) == canonical(expected), 'plan_changed')


def authorize(plan, envelope, evidence_id, approval, now, trusted_operator):
    """trusted_operator MUST come from a separately authenticated execution context.

    This comparison is not identity authentication or a signature verifier.
    Supplying a name from the approval itself is forbidden for future integration.
    """
    now = now_checked(now)
    validate_plan(plan, envelope, evidence_id)
    exact(approval, {'schema_version', 'approval_id', 'decision', 'operator', 'reason_code',
                     'plan_sha256', 'approved_at_utc', 'expires_at_utc'}, 'approval_required_or_invalid')
    require(approval['schema_version'] == 'bluefield-operator-approval-1' and approval['decision'] == 'approve', 'not_approved')
    token(trusted_operator, IDENTITY, 'trusted_operator_required')
    require(approval['operator'] == trusted_operator, 'operator_mismatch')
    token(approval['approval_id'], IDENTITY, 'invalid_approval_id')
    require(approval['reason_code'] == 'investigate_original_record', 'invalid_approval_reason')
    require(approval['plan_sha256'] == plan['plan_sha256'], 'approval_plan_mismatch')
    start, end = timestamp(approval['approved_at_utc']), timestamp(approval['expires_at_utc'])
    require(timestamp(plan['reviewed_at_utc']) <= start <= now < end, 'approval_not_current')
    require(0 < (end - start).total_seconds() <= 3600, 'approval_ttl_exceeded')
    return digest({'plan': plan['plan_sha256'], 'approval': approval})


def verify_source(plan, actual_source, raw, low, high):
    """Caller must re-authorize before every attempt; accepts only exact Kafka bytes.

    Transport must use explicit assign/seek, disable commits and verify returned
    topic/partition/offset. There is no fallback to an archived file.
    """
    coordinates(actual_source)
    require(actual_source == plan['source'], 'source_position_mismatch')
    require(type(low) is int and type(high) is int and 0 <= low <= high, 'invalid_watermarks')
    require(low <= actual_source['offset'] < high, 'source_unavailable')
    require(type(raw) is bytes and 0 < len(raw) <= 4 * 1024 * 1024, 'source_missing_or_oversize')
    require(hashlib.sha256(raw).hexdigest() == plan['input_sha256'], 'source_hash_mismatch')
    return raw  # No JSON reserialization, payload correction or validation bypass.


STATES = {
    'new': {'reviewed'},
    'reviewed': {'approved', 'rejected'},
    'approved': {'intent_recorded', 'rejected'},
    'intent_recorded': {'acknowledged', 'outcome_unknown'},
    'outcome_unknown': set(), 'acknowledged': set(), 'rejected': set(),
}
REASONS = {'reviewed': {'review_created'}, 'approved': {'operator_approved'},
           'rejected': {'approval_missing', 'approval_invalid', 'source_unavailable', 'hash_mismatch', 'operator_rejected'},
           'intent_recorded': {'verified_original_bytes'}, 'acknowledged': {'destination_ack'},
           'outcome_unknown': {'delivery_or_audit_uncertain'}}


def audit_event(previous, attempt_id, plan_sha256, state, reason_code, now):
    """Build an allowlisted audit event; NOT a durable or concurrency-safe journal.

    A future runner must persist intent before publishing. After intent, a crash
    or ambiguous ACK requires reconciliation, never an automatic retry.
    """
    token(attempt_id, IDENTITY, 'invalid_attempt_id')
    token(plan_sha256, HASH, 'invalid_plan_hash')
    require(previous is None or type(previous) is dict, 'invalid_previous_audit')
    old_state = 'new' if previous is None else previous.get('state')
    require(old_state in STATES and state in STATES[old_state], 'invalid_audit_transition')
    require(reason_code in REASONS[state], 'invalid_audit_reason')
    when = now_checked(now)
    if previous is not None:
        exact(previous, {'schema_version', 'attempt_id', 'plan_sha256', 'sequence', 'state', 'reason_code',
                         'time_utc', 'previous_sha256', 'event_sha256'}, 'invalid_previous_audit')
        require(previous['attempt_id'] == attempt_id and previous['plan_sha256'] == plan_sha256, 'audit_identity_mismatch')
        require(previous['schema_version'] == 'bluefield-replay-audit-1' and type(previous['sequence']) is int and previous['sequence'] >= 0, 'invalid_previous_audit')
        require(digest({k: v for k, v in previous.items() if k != 'event_sha256'}) == previous['event_sha256'], 'audit_hash_mismatch')
        require(timestamp(previous['time_utc']) <= when, 'audit_time_reversed')
    row = {'schema_version': 'bluefield-replay-audit-1', 'attempt_id': attempt_id,
           'plan_sha256': plan_sha256, 'sequence': 0 if previous is None else previous['sequence'] + 1,
           'state': state, 'reason_code': reason_code, 'time_utc': when.isoformat(),
           'previous_sha256': None if previous is None else previous['event_sha256']}
    return {**row, 'event_sha256': digest(row)}
