"""Offline tests: no GPU or broker calls."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace as N
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'shadow'))
import worker as w
import test_shadow as fixtures
import common


class Tests(unittest.TestCase):
    def test_resource_names_are_run_scoped(self):
        r=w.resources('d20261013t103000-1234abcd')
        self.assertEqual(len(set(r.values())),6)
        for bad in ['../other','bluefield-events','d20261013t103000-1234abcD','']:
            with self.assertRaises(ValueError): w.resources(bad)
    def test_delivery_before_commit(self):
        seen=[]; p=fixtures.Producer()
        w.send(p,'test',b'key',{}, {'test'},lambda:seen.append('commit'))
        self.assertEqual(seen,['commit'])
    def test_failed_delivery_never_commits(self):
        for p in [fixtures.Producer(error=True),fixtures.Producer(remaining=1),fixtures.Producer(callback=False),fixtures.Producer(crash=True)]:
            seen=[]
            with self.assertRaises(RuntimeError): w.send(p,'test',b'k',{}, {'test'},lambda:seen.append(1))
            self.assertEqual(seen,[])
    def test_live_output_denied(self):
        p=fixtures.Producer()
        with self.assertRaises(ValueError): w.send(p,'morpheus-output',b'k',{}, {'demo'},lambda:None)
        self.assertEqual(p.sent,[])
    def test_index_partial_ack_rejected(self):
        for result in [{}, {'_index':'demo','_id':'id','_shards':{'failed':1,'successful':1}}]:
            with patch.object(w,'request',return_value=(201,result)):
                with self.assertRaises(RuntimeError): w.index_ack('demo','id',{})
    def test_index_valid_ack(self):
        with patch.object(w,'request',return_value=(201,{'_index':'demo','_id':'id','_shards':{'failed':0,'successful':1}})):
            w.index_ack('demo','id',{})
    def test_alignment_mismatch_rejected(self):
        env,raw,_=fixtures.sample(); msg=N(key=lambda:env['event_uid'].encode(),value=lambda:common.encode(env))
        with self.assertRaises(ValueError): w.map_score([env],[msg],lambda *_:[])
    def test_source_hash_mismatch_rejected(self):
        env,raw,_=fixtures.sample(); msg=N(key=lambda:env['event_uid'].encode(),value=lambda:common.encode(env))
        out=fixtures.severity(); out['captured_at_utc']=env['captured_at_utc']; out['raw_sha256']='f'*64
        with patch.object(w,'validate',return_value='id'):
            with self.assertRaises(ValueError): w.map_score([env],[msg],lambda *_:[out])
    def test_resume_preserves_committed_offset(self):
        part=N(partition=0,offset=7,error=None)
        client=N(committed=lambda *_args,**_kw:[part],get_watermark_offsets=lambda *_a,**_k:(0,10),
                 assign=lambda saved:None,close=lambda:None)
        api=N(Consumer=lambda cfg:client,TopicPartition=lambda t,p:N(topic=t,partition=p),OFFSET_INVALID=-1001)
        meta=N(topics={'topic':N(partitions={0:None})})
        with patch.object(w.rt,'metadata',return_value=meta),patch.object(w,'audit'):
            w.consumer(api,'broker','topic','group',{'0':9})
        self.assertEqual(part.offset,7)
    def test_retention_gap_does_not_reset(self):
        part=N(partition=0,offset=2,error=None)
        client=N(committed=lambda *_args,**_kw:[part],get_watermark_offsets=lambda *_a,**_k:(5,10),close=lambda:None)
        api=N(Consumer=lambda cfg:client,TopicPartition=lambda t,p:N(topic=t,partition=p),OFFSET_INVALID=-1001)
        meta=N(topics={'topic':N(partitions={0:None})})
        with patch.object(w.rt,'metadata',return_value=meta),patch.object(w,'audit'):
            with self.assertRaises(RuntimeError): w.consumer(api,'broker','topic','group',{'0':9})
    def test_new_group_uses_recorded_boundary(self):
        part=N(partition=0,offset=-1001,error=None)
        client=N(committed=lambda *_args,**_kw:[part],get_watermark_offsets=lambda *_a,**_k:(0,10),assign=lambda saved:None,close=lambda:None)
        api=N(Consumer=lambda cfg:client,TopicPartition=lambda t,p:N(topic=t,partition=p),OFFSET_INVALID=-1001)
        meta=N(topics={'topic':N(partitions={0:None})})
        with patch.object(w.rt,'metadata',return_value=meta),patch.object(w,'audit'):
            w.consumer(api,'broker','topic','group',{'0':9})
        self.assertEqual(part.offset,9)


if __name__=='__main__': unittest.main(verbosity=2)
