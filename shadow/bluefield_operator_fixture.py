"""One new synthetic source record; never controlled replay or approval."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
import bluefield_operator_contract as c
from bluefield_operator_kafka import KafkaReader, validate_metadata
from bluefield_operator_source import inspect_source
from bluefield_common import TARGET

RAW = b'{"fixture":"operator-source-v1","carrier":2}'


def bundle(run_id, offset=0, digest=None):
    c.token(run_id, c.RUN, 'invalid_run_id')
    now = datetime.now(timezone.utc)
    source = {'topic': 'shadow-bluefield-quarantine-input-' + run_id, 'partition': 0, 'offset': offset}
    envelope = dict(schema_version='bluefield-quarantine-1', processing_mode='shadow_quarantine',
                    run_id=run_id, reason_code='strict_validation_failed', error_type='ValueError',
                    validation_stage='validate_review', input_sha256=digest or hashlib.sha256(RAW).hexdigest(),
                    quarantined_at_utc=now.isoformat(), historical=True, production_ready=False,
                    automated_response_allowed=False, source=source)
    evidence_id = hashlib.sha256(json.dumps([run_id, source['topic'], 0, offset,
                                            envelope['input_sha256']]).encode()).hexdigest()
    plan = c.review_plan(envelope, evidence_id, 'shadow-bluefield-controlled-replay-' + run_id, now)
    return plan, envelope, evidence_id


def report(event, **fields):
    print(json.dumps({'kind': event, **fields}, allow_nan=False), flush=True)


def exercise(backend, *, allowed, emit=report):
    c.require(allowed == '1', 'fixture_mutation_disabled')
    # Generated internally; never accept a historical run ID or an arbitrary topic.
    run_id = 'opread-' + uuid.uuid4().hex
    missing_id = 'opmiss-' + uuid.uuid4().hex
    plan, envelope, evidence_id = bundle(run_id)
    topic = plan['source']['topic']
    missing = bundle(missing_id)
    topics = backend.topics()
    c.require(topic not in topics and missing[0]['source']['topic'] not in topics, 'fixture_name_collision')
    emit('fixture_intent', run_id=run_id, topic=topic, fixture_only=True,
         replay_authorized=False, input_sha256=envelope['input_sha256'])
    backend.create(topic)
    emit('fixture_topic_created', topic=topic)
    c.require(backend.bounds(topic) == (0, 0), 'fixture_not_empty')
    ack = backend.publish(topic, RAW)
    c.require(ack == {'topic': topic, 'partition': 0, 'offset': 0}, 'fixture_ack_mismatch')
    emit('fixture_source_ack', **ack)
    c.require(backend.bounds(topic) == (0, 1), 'fixture_not_single_record')
    result = backend.inspect(plan, envelope, evidence_id)
    c.require(result['status'] == 'verified_at_read' and result['replay_authorized'] is False,
              'inspection_not_verified')
    negatives = [
        ('hash_mismatch', bundle(run_id, digest='0'*64), 'source_hash_mismatch'),
        ('offset_at_end', bundle(run_id, offset=1), 'source_unavailable'),
        ('topic_missing', missing, 'source_topic_missing')]
    checked = []
    for label, data, expected in negatives:
        try:
            backend.inspect(*data)
        except c.Rejected as exc:
            c.require(str(exc) == expected, 'unexpected_negative_result')
            checked.append(label)
        else:
            raise c.Rejected('negative_case_accepted')
    c.require(missing[0]['source']['topic'] not in backend.topics(), 'missing_topic_created')
    c.require(backend.bounds(topic) == (0, 1), 'fixture_changed_during_read')
    result = dict(status='PASS', run_id=run_id, source=plan['source'],
                  input_sha256=envelope['input_sha256'], source_records=1,
                  negative_cases=checked, fixture_only=True, replay_authorized=False,
                  approval_issued=False, controlled_replay_sent=False,
                  production_ready=False, automated_response_allowed=False,
                  source_topic_retained=True)
    emit('fixture_reader_result', **result)
    return result


class Runtime:
    def __init__(self):
        import confluent_kafka as api
        from confluent_kafka.admin import AdminClient, NewTopic
        c.require(api.version()[0] == '2.6.1' and api.libversion()[0] == '2.6.1', 'unsupported_kafka_client')
        self.api, self.NewTopic = api, NewTopic
        self.admin = AdminClient({'bootstrap.servers': TARGET, 'socket.timeout.ms': 5000, 'log_level': 0})
        self.owned = None
        self.sent = False

    def topics(self):
        return set(validate_metadata(self.admin.list_topics(timeout=10)).topics)

    def create(self, topic):
        c.coordinates({'topic': topic, 'partition': 0, 'offset': 0})
        c.require(topic.startswith('shadow-bluefield-quarantine-input-opread-') and
                  self.owned is None and topic not in self.topics(), 'fixture_create_denied')
        futures = self.admin.create_topics([self.NewTopic(topic, num_partitions=1, replication_factor=1,
            config={'retention.ms': '86400000', 'cleanup.policy': 'delete', 'segment.ms': '60000'})],
            operation_timeout=10, request_timeout=15)
        futures[topic].result(timeout=16)
        self.owned = topic  # No adoption/retry if creation outcome is uncertain.

    def bounds(self, topic):
        c.require(topic == self.owned, 'not_owned_fixture')
        reader = KafkaReader()
        try:
            c.require(reader.partitions(topic, 5) == {0}, 'fixture_metadata_unavailable')
            return reader.watermarks(topic, 0, 5)
        finally: reader.close()

    def publish(self, topic, raw):
        c.require(topic == self.owned and not self.sent and raw == RAW, 'fixture_publish_denied')
        c.require(topic in self.topics(), 'fixture_missing_before_publish')
        self.sent = True  # Never retry an uncertain publish in this process.
        producer = self.api.Producer({'bootstrap.servers': TARGET, 'acks': 'all',
            'enable.idempotence': True, 'delivery.timeout.ms': 10000,
            'request.timeout.ms': 3000, 'socket.timeout.ms': 5000, 'log_level': 0})
        replies = []
        def delivered(error, message):
            replies.append(None if error else {'topic': message.topic(),
                           'partition': message.partition(), 'offset': message.offset()})
        producer.produce(topic, value=raw, partition=0, on_delivery=delivered)
        remaining = producer.flush(12)
        c.require(remaining == 0 and len(replies) == 1 and replies[0] is not None, 'fixture_delivery_uncertain')
        return replies[0]

    def inspect(self, plan, envelope, evidence_id):
        return inspect_source(plan, envelope, evidence_id, KafkaReader(), timeout_seconds=15)


def main():
    try:
        allowed = os.environ.get('BLUEFIELD_OPERATOR_FIXTURE_ALLOWED')
        c.require(allowed == '1', 'fixture_mutation_disabled')
        exercise(Runtime(), allowed=allowed)
        return 0
    except c.Rejected as exc:
        report('fixture_reader_failed', reason=str(exc), replay_authorized=False)
        return 1
    except Exception:
        report('fixture_reader_failed', reason='runtime_failure', replay_authorized=False)
        return 1


if __name__ == '__main__': raise SystemExit(main())
