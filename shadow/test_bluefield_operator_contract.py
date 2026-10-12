"""Synthetic offline tests: no Kafka/OpenSearch, GPU, driver or service access."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import unittest
import bluefield_operator_contract as c


class Contracts(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 13, 4, tzinfo=timezone.utc)
        self.raw = b'{"carrier":2}'  # Deliberately invalid measurement, never repaired.
        self.source = {'topic': 'shadow-bluefield-quarantine-input-fixture01', 'partition': 0, 'offset': 1}
        self.envelope = dict(schema_version='bluefield-quarantine-1', processing_mode='shadow_quarantine',
                             run_id='fixture01', reason_code='strict_validation_failed', error_type='ValueError',
                             validation_stage='validate_review', input_sha256=hashlib.sha256(self.raw).hexdigest(),
                             quarantined_at_utc=(self.now - timedelta(minutes=1)).isoformat(),
                             historical=True, production_ready=False, automated_response_allowed=False,
                             source=self.source.copy())
        self.id = hashlib.sha256(json.dumps(['fixture01', self.source['topic'], 0, 1, self.envelope['input_sha256']]).encode()).hexdigest()
        self.plan = c.review_plan(self.envelope, self.id, 'shadow-bluefield-controlled-replay-fixture02', self.now)
        self.approval = dict(schema_version='bluefield-operator-approval-1', approval_id='approval01',
                             decision='approve', operator='fixture-operator', reason_code='investigate_original_record',
                             plan_sha256=self.plan['plan_sha256'], approved_at_utc=self.now.isoformat(),
                             expires_at_utc=(self.now + timedelta(minutes=10)).isoformat())

    def auth(self, approval=None):
        return c.authorize(self.plan, self.envelope, self.id, self.approval if approval is None else approval,
                           self.now, 'fixture-operator')

    def test_valid_approval_is_bound_to_plan(self):
        self.assertRegex(self.auth(), '^[0-9a-f]{64}$')

    def test_missing_approval(self):
        with self.assertRaises(c.Rejected):
            c.authorize(self.plan, self.envelope, self.id, None, self.now, 'fixture-operator')

    def test_nonapproval_operator_and_binding(self):
        for key, value in [('decision', 'pending'), ('decision', 'reject'), ('operator', 'other'), ('plan_sha256', '0'*64)]:
            with self.subTest(key=key, value=value):
                a = {**self.approval, key: value}
                with self.assertRaises(c.Rejected): self.auth(a)

    def test_expired_future_or_excessive_ttl(self):
        for changes in ({'expires_at_utc': self.now.isoformat()},
                        {'approved_at_utc': (self.now + timedelta(seconds=1)).isoformat()},
                        {'expires_at_utc': (self.now + timedelta(hours=2)).isoformat()}):
            with self.assertRaises(c.Rejected): self.auth({**self.approval, **changes})

    def test_plan_and_evidence_tampering(self):
        self.plan['destination_topic'] = 'shadow-bluefield-controlled-replay-fixture03'
        with self.assertRaises(c.Rejected): self.auth()
        with self.assertRaises(c.Rejected): c.evidence(self.envelope, '0'*64)

    def test_extra_raw_fields_are_rejected(self):
        for key in ('raw_event', 'raw_payload', 'capture_scope'):
            with self.assertRaises(c.Rejected): c.evidence({**self.envelope, key: 'private'}, self.id)
        with self.assertRaises(c.Rejected): self.auth({**self.approval, 'raw_event': 'private'})

    def test_safety_flags_are_strict_booleans(self):
        for field, value in [('historical', 1), ('production_ready', True), ('automated_response_allowed', 0)]:
            with self.assertRaises(c.Rejected): c.evidence({**self.envelope, field: value}, self.id)

    def test_live_or_shared_destinations_rejected(self):
        for topic in ('bluefield-events', 'shadow-bluefield-input-v1', 'morpheus-input', 'replay-morpheus-input'):
            with self.assertRaises(c.Rejected): c.review_plan(self.envelope, self.id, topic, self.now)
        bad = copy.deepcopy(self.envelope)
        bad['source']['topic'] = 'bluefield-events'
        with self.assertRaises(c.Rejected): c.evidence(bad, self.id)

    def test_exact_bytes_preserve_poison(self):
        result = c.verify_source(self.plan, self.source, self.raw, 0, 3)
        self.assertIs(result, self.raw)
        self.assertEqual(json.loads(result)['carrier'], 2)

    def test_retention_absent_or_hash_mismatch(self):
        for raw, low, high in [(self.raw, 2, 3), (self.raw, 0, 1), (None, 0, 3), (b'{"carrier":null}', 0, 3)]:
            with self.assertRaises(c.Rejected): c.verify_source(self.plan, self.source, raw, low, high)

    def test_wrong_exact_position(self):
        for change in ({'offset': 2}, {'partition': True}, {'topic': 'shadow-bluefield-quarantine-input-fixture03'}):
            with self.assertRaises(c.Rejected): c.verify_source(self.plan, {**self.source, **change}, self.raw, 0, 3)

    def test_audit_order_and_unknown_cannot_retry(self):
        previous = None
        for state, reason in [('reviewed', 'review_created'), ('approved', 'operator_approved'),
                              ('intent_recorded', 'verified_original_bytes'), ('outcome_unknown', 'delivery_or_audit_uncertain')]:
            previous = c.audit_event(previous, 'attempt01', self.plan['plan_sha256'], state, reason, self.now)
        self.assertEqual(previous['sequence'], 3)
        with self.assertRaises(c.Rejected):
            c.audit_event(previous, 'attempt01', self.plan['plan_sha256'], 'intent_recorded', 'verified_original_bytes', self.now)

    def test_cannot_ack_without_intent(self):
        with self.assertRaises(c.Rejected):
            c.audit_event(None, 'attempt01', self.plan['plan_sha256'], 'acknowledged', 'destination_ack', self.now)

    def test_audit_tamper_and_payload_reason_rejected(self):
        row = c.audit_event(None, 'attempt01', self.plan['plan_sha256'], 'reviewed', 'review_created', self.now)
        row['time_utc'] = (self.now - timedelta(seconds=1)).isoformat()
        with self.assertRaises(c.Rejected):
            c.audit_event(row, 'attempt01', self.plan['plan_sha256'], 'approved', 'operator_approved', self.now)
        with self.assertRaises(c.Rejected):
            c.audit_event(None, 'attempt01', self.plan['plan_sha256'], 'reviewed', 'raw secret payload', self.now)

    def test_success_chain_contains_no_raw_or_approval_payload(self):
        row = None
        for state, reason in [('reviewed', 'review_created'), ('approved', 'operator_approved'),
                              ('intent_recorded', 'verified_original_bytes'), ('acknowledged', 'destination_ack')]:
            row = c.audit_event(row, 'attempt01', self.plan['plan_sha256'], state, reason, self.now)
        self.assertNotIn('carrier', json.dumps(row))
        self.assertEqual(row['state'], 'acknowledged')


if __name__ == '__main__':
    unittest.main(verbosity=2)
