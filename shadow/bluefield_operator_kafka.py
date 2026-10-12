"""Read-only confluent-kafka 2.6.1 adapter; no producer or commit API."""
import argparse
import json
import time
import uuid
import bluefield_operator_contract as c
from bluefield_common import TARGET, EXPECTED_CLUSTER_ID, REPLAY_TOPICS, FORBIDDEN_LIVE_TOPICS
from bluefield_operator_source import inspect_source
from bluefield_operator_review import read_envelope


def validate_metadata(meta):
    c.require(meta.cluster_id == EXPECTED_CLUSTER_ID, 'wrong_cluster')
    c.require({(b.host, b.port) for b in meta.brokers.values()} == {('kafka', 29092)}, 'wrong_listener')
    c.require(REPLAY_TOPICS.issubset(meta.topics), 'replay_signature_missing')
    c.require(not FORBIDDEN_LIVE_TOPICS.intersection(meta.topics), 'live_topics_detected')
    for name in REPLAY_TOPICS:
        c.require(not meta.topics[name].error, 'replay_metadata_error')
    return meta


class KafkaReader:
    def __init__(self, api=None):
        if api is None:
            import confluent_kafka as api
        c.require(api.version()[0] == '2.6.1' and api.libversion()[0] == '2.6.1', 'unsupported_kafka_client')
        self.api = api
        # confluent Consumer requires group.id. Manual assign never subscribes or
        # joins a group; random identity must not reuse any pipeline group.
        self.client = api.Consumer({
            'bootstrap.servers': TARGET,
            'group.id': 'edrxdr-operator-readonly-' + uuid.uuid4().hex,
            'enable.auto.commit': False, 'enable.auto.offset.store': False,
            'allow.auto.create.topics': False, 'auto.offset.reset': 'error',
            'enable.partition.eof': True, 'socket.timeout.ms': 5000,
            'session.timeout.ms': 6000, 'fetch.wait.max.ms': 100,
            'fetch.message.max.bytes': 4*1024*1024,
            'queued.max.messages.kbytes': 8192, 'log_level': 0})
        self.bound = None
        self.closed = False

    def metadata(self, timeout):
        # Request ALL topic metadata: never request/create a missing named topic.
        return validate_metadata(self.client.list_topics(timeout=timeout))

    def partitions(self, topic, timeout):
        c.coordinates({'topic': topic, 'partition': 0, 'offset': 0})
        meta = self.metadata(timeout)
        item = meta.topics.get(topic)
        if item is None: return None
        c.require(not item.error, 'source_metadata_error')
        c.require(set(item.partitions) == {0}, 'unexpected_source_partitions')
        c.require(not item.partitions[0].error, 'source_partition_error')
        self.bound = topic
        return {0}

    def watermarks(self, topic, partition, timeout):
        c.require(topic == self.bound and partition == 0, 'unverified_source')
        return self.client.get_watermark_offsets(self.api.TopicPartition(topic, partition),
                                                 timeout=timeout, cached=False)

    def fetch_exact(self, topic, partition, offset, timeout):
        c.require(topic == self.bound and partition == 0, 'unverified_source')
        c.coordinates({'topic': topic, 'partition': partition, 'offset': offset})
        deadline = time.monotonic() + timeout
        # Offset in assignment is an explicit seek; no stored offset fallback.
        self.client.assign([self.api.TopicPartition(topic, partition, offset)])
        left = deadline - time.monotonic()
        c.require(left > 0, 'source_read_timeout')
        message = self.client.poll(left)
        if message is None: return None
        c.require(not message.error(), 'source_fetch_error')
        actual = {'topic': message.topic(), 'partition': message.partition(), 'offset': message.offset()}
        c.require(actual == {'topic': topic, 'partition': partition, 'offset': offset}, 'source_position_mismatch')
        return {'source': actual, 'value': message.value()}

    def close(self):
        if not self.closed:
            self.client.close()  # auto commit disabled, including on close
            self.closed = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('preflight')
    cmd = sub.add_parser('inspect')
    cmd.add_argument('--plan', required=True)
    cmd.add_argument('--envelope', required=True)
    cmd.add_argument('--evidence-id', required=True)
    args = parser.parse_args()
    reader = None
    try:
        if args.command == 'inspect':
            plan, envelope = read_envelope(args.plan), read_envelope(args.envelope)
            c.validate_plan(plan, envelope, args.evidence_id)
        reader = KafkaReader()
        if args.command == 'preflight':
            reader.metadata(10)
            result = {'status': 'broker_identity_checked', 'replay_authorized': False}
        else:
            result = inspect_source(plan, envelope, args.evidence_id, reader, timeout_seconds=20)
        reader.close()
        print(json.dumps(result, allow_nan=False))
        return 0
    except c.Rejected as exc:
        print(json.dumps({'status': 'rejected', 'reason': str(exc), 'replay_authorized': False}))
        return 1
    except Exception:
        print(json.dumps({'status': 'rejected', 'reason': 'reader_failed', 'replay_authorized': False}))
        return 1
    finally:
        if reader is not None and not reader.closed:
            try: reader.close()
            except Exception: pass


if __name__ == '__main__':
    raise SystemExit(main())
