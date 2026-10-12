"""Offline fake-client tests. No broker or service calls."""
import unittest
from types import SimpleNamespace as N
import bluefield_operator_kafka as k
import bluefield_operator_contract as c
import test_bluefield_operator_contract as fixtures
from bluefield_operator_source import inspect_source


def metadata():
    return N(cluster_id=k.EXPECTED_CLUSTER_ID, brokers={1:N(host='kafka',port=29092)},
             topics={t:N(error=None,partitions={0:N(error=None)}) for t in k.REPLAY_TOPICS})


class Client:
    def __init__(self, config):
        self.config=config; self.meta=metadata(); self.calls=[]; self.message=None
    def list_topics(self, **kwargs):
        self.calls.append(('metadata',kwargs)); return self.meta
    def get_watermark_offsets(self, tp, **kwargs):
        self.calls.append(('bounds',kwargs)); return (0,3)
    def assign(self, tps): self.calls.append(('assign',tps))
    def poll(self, timeout): self.calls.append(('poll',timeout)); return self.message
    def close(self): self.calls.append(('close',))


class KafkaTests(unittest.TestCase):
    def setUp(self):
        self.api=N(version=lambda:('2.6.1',0),libversion=lambda:('2.6.1',0),
                   Consumer=Client,TopicPartition=lambda t,p,o=None:(t,p,o))
        self.r=k.KafkaReader(self.api)
        self.f=fixtures.Contracts(); self.f.setUp()
        self.topic=self.f.source['topic']
        self.r.client.meta.topics[self.topic]=N(error=None,partitions={0:N(error=None)})
    def test_readonly_settings_and_unique_id(self):
        cfg=self.r.client.config
        for field in ['enable.auto.commit','enable.auto.offset.store','allow.auto.create.topics']:
            self.assertIs(cfg[field],False)
        self.assertEqual(cfg['auto.offset.reset'],'error')
        self.assertNotEqual(cfg['group.id'],k.KafkaReader(self.api).client.config['group.id'])
    def test_wrong_cluster(self):
        self.r.client.meta.cluster_id='wrong'
        with self.assertRaisesRegex(c.Rejected,'wrong_cluster'): self.r.metadata(1)
    def test_wrong_listener(self):
        self.r.client.meta.brokers[1].port=9092
        with self.assertRaisesRegex(c.Rejected,'wrong_listener'): self.r.metadata(1)
    def test_live_signature(self):
        self.r.client.meta.topics['bluefield-events']=N()
        with self.assertRaisesRegex(c.Rejected,'live_topics_detected'): self.r.metadata(1)
    def test_missing_replay_signature(self):
        self.r.client.meta.topics.pop(next(iter(k.REPLAY_TOPICS)))
        with self.assertRaisesRegex(c.Rejected,'replay_signature_missing'): self.r.metadata(1)
    def test_missing_topic_no_named_metadata_request(self):
        self.r.client.meta.topics.pop(self.topic)
        self.assertIsNone(self.r.partitions(self.topic,1))
        self.assertEqual(self.r.client.calls,[('metadata',{'timeout':1})])
    def test_live_source_rejected_before_io(self):
        with self.assertRaises(c.Rejected): self.r.partitions('bluefield-events',1)
        self.assertEqual(self.r.client.calls,[])
    def test_read_before_verification_denied(self):
        with self.assertRaises(c.Rejected): self.r.fetch_exact(self.topic,0,1,1)
    def test_extra_partition_denied(self):
        self.r.client.meta.topics[self.topic].partitions[1]=N(error=None)
        with self.assertRaises(c.Rejected): self.r.partitions(self.topic,1)
    def test_wrong_returned_offset(self):
        self.r.partitions(self.topic,1)
        self.r.client.message=N(error=lambda:None,topic=lambda:self.topic,partition=lambda:0,offset=lambda:2)
        with self.assertRaisesRegex(c.Rejected,'source_position_mismatch'): self.r.fetch_exact(self.topic,0,1,1)
    def test_exact_read_integration_with_core(self):
        self.r.client.message=N(error=lambda:None,topic=lambda:self.topic,partition=lambda:0,
                                offset=lambda:1,value=lambda:self.f.raw)
        result=inspect_source(self.f.plan,self.f.envelope,self.f.id,self.r)
        self.assertEqual(result['status'],'verified_at_read')
        self.assertFalse(result['replay_authorized'])
        self.assertIn(('assign',[(self.topic,0,1)]),self.r.client.calls)
        self.assertTrue(self.r.closed)
    def test_client_version_rejected(self):
        self.api.version=lambda:('2.7.0',0)
        with self.assertRaises(c.Rejected): k.KafkaReader(self.api)
    def test_close_idempotent(self):
        self.r.close(); self.r.close()
        self.assertEqual(self.r.client.calls,[('close',)])
    def test_message_error_fails_closed(self):
        self.r.partitions(self.topic,1)
        self.r.client.message=N(error=lambda:True)
        with self.assertRaisesRegex(c.Rejected,'source_fetch_error'): self.r.fetch_exact(self.topic,0,1,1)


if __name__ == '__main__': unittest.main(verbosity=2)
