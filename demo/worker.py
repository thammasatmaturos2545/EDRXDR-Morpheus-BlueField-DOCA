"""Bounded near-real-time Severity demo. Existing pipelines remain unchanged."""
import argparse
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import common
import runtime as rt
from validation import validate

RUN = re.compile(r'd[0-9]{8}t[0-9]{6}-[0-9a-f]{8}')
STOP = False


def resources(run):
    if not isinstance(run, str) or not RUN.fullmatch(run): raise ValueError('Invalid demo run')
    prefix = 'demo-severity-' + run
    return {'raw': prefix+'-raw', 'output':prefix+'-output', 'index':prefix,
            'capture':prefix+'-capture', 'score':prefix+'-score', 'indexer':prefix+'-indexer'}


def stamp(): return datetime.now(timezone.utc).isoformat()


def audit(kind, **fields):
    row = {'kind':kind,'time_utc':stamp(),**fields}
    encoded = json.dumps(row,allow_nan=False)
    with Path('/demo-state/audit.jsonl').open('a') as stream:
        stream.write(encoded+'\n'); stream.flush(); os.fsync(stream.fileno())
    print(encoded,flush=True)


def request(index, suffix='', body=None, method='GET'):
    if not re.fullmatch(r'demo-severity-d[0-9]{8}t[0-9]{6}-[0-9a-f]{8}',index):
        raise ValueError('Index not isolated')
    req=Request('http://opensearch:9200/'+index+suffix,
                data=None if body is None else common.encode(body),
                headers={'Content-Type':'application/json'},method=method)
    with urlopen(req,timeout=10) as reply: return reply.status,json.load(reply)


def index_ack(index, docid, document):
    status, result=request(index,'/_doc/'+docid+'?refresh=wait_for',document,'PUT')
    shards=result.get('_shards',{})
    if status not in (200,201) or result.get('_index')!=index or result.get('_id')!=docid or        shards.get('failed')!=0 or shards.get('successful',0)<1:
        raise RuntimeError('Index acknowledgement failed')


def send(producer, topic, key, value, allowed, commit):
    if topic not in allowed: raise ValueError('Destination not isolated')
    replies=[]
    producer.produce(topic,key=key,value=common.encode(value),
                     on_delivery=lambda error,message:replies.append(error))
    remaining=producer.flush(12)
    if remaining or len(replies)!=1 or replies[0] is not None:
        raise RuntimeError('Delivery uncertain; no input commit')
    commit()


def map_score(envelopes, messages, scorer):
    raws=[common.unpack(item,msg.key()) for item,msg in zip(envelopes,messages)]
    if len(envelopes)!=len(messages): raise ValueError('Input alignment')
    outputs=scorer(envelopes,raws)
    if len(outputs)!=len(messages): raise ValueError('Output alignment')
    for row,msg in zip(outputs,messages):
        validate('severity',row,msg.key())
        original=common.strict_json(msg.value())
        for name in ('event_uid','source','raw_sha256','captured_at_utc'):
            if row[name]!=original[name]: raise ValueError('Output occurrence mismatch')
    return outputs


def collect(client, seconds, limit=8):
    end=time.monotonic()+seconds; rows=[]
    while not STOP and len(rows)<limit and time.monotonic()<end:
        msg=client.poll(max(0,min(0.25,end-time.monotonic())))
        if msg is None: continue
        if msg.error(): raise RuntimeError('Kafka read failed')
        if not msg.value() or len(msg.value())>1024*1024: raise ValueError('Invalid event size')
        rows.append(msg)
    return rows


def consumer(api, broker, topic, group, initial=None):
    meta=rt.metadata(broker,[topic])
    client=api.Consumer({'bootstrap.servers':broker,'group.id':group,
        'enable.auto.commit':False,'enable.auto.offset.store':False,
        'allow.auto.create.topics':False,'auto.offset.reset':'error','socket.timeout.ms':5000})
    try:
        parts=[api.TopicPartition(topic,p) for p in sorted(meta.topics[topic].partitions)]
        saved=client.committed(parts,timeout=5)
        for part in saved:
            if part.error: raise RuntimeError('Offset unavailable')
            low,high=client.get_watermark_offsets(part,timeout=5,cached=False)
            if part.offset==api.OFFSET_INVALID:
                part.offset=initial[str(part.partition)] if initial is not None else 0
            if not low<=part.offset<=high: raise RuntimeError('Retention gap; no reset allowed')
        client.assign(saved)
        audit('consumer_boundary',topic=topic,group=group,
              offsets=[{'partition':p.partition,'offset':p.offset} for p in saved])
        return client
    except BaseException:
        client.close(); raise


def initialize(api, admin, run, r):
    statepath=Path('/demo-state/run.json')
    source,target=rt.check_clusters()
    if statepath.exists():
        state=common.strict_json(statepath.read_bytes())
        if state['run_id']!=run or state['resources']!=r: raise ValueError('State/resource mismatch')
        if state['source_cluster_id']!=source.cluster_id: raise ValueError('Source changed')
        if set(state['starts'])!={str(p) for p in source.topics[common.SOURCE_TOPIC].partitions}:
            raise ValueError('Source partitions changed')
    else:
        if {r['raw'],r['output']} & set(target.topics): raise ValueError('Topic collision')
        try: request(r['index'])
        except HTTPError as exc:
            if exc.code!=404: raise
        else: raise ValueError('Index collision')
        probe=api.Consumer({'bootstrap.servers':rt.SOURCE,'group.id':r['capture'],
            'enable.auto.commit':False,'enable.auto.offset.store':False,'allow.auto.create.topics':False})
        try:
            starts={str(p):probe.get_watermark_offsets(api.TopicPartition(common.SOURCE_TOPIC,p),
                                                      timeout=5,cached=False)[1]
                    for p in source.topics[common.SOURCE_TOPIC].partitions}
        finally: probe.close()
        state={'run_id':run,'resources':r,'source_cluster_id':source.cluster_id,
               'starts':starts,'boundary_recorded_at_utc':stamp()}
        with statepath.open('x') as file:
            json.dump(state,file); file.flush(); os.fsync(file.fileno())
        audit('new_event_boundary',**state)
    from confluent_kafka.admin import NewTopic
    for topic in (r['raw'],r['output']):
        meta=rt.metadata(rt.TARGET)
        if topic not in meta.topics:
            admin.create_topics([NewTopic(topic,num_partitions=1,replication_factor=1,
                config={'retention.ms':'86400000','retention.bytes':'67108864'})],
                request_timeout=10,operation_timeout=8)[topic].result(timeout=12)
        else:
            if meta.topics[topic].error or set(meta.topics[topic].partitions)!={0}:
                raise ValueError('Unexpected demo partition count')
    try: request(r['index'])
    except HTTPError as exc:
        if exc.code!=404: raise
        _,reply=request(r['index'],body={'settings':{'number_of_shards':1,'number_of_replicas':0},
            'mappings':{'properties':{
                'doc_type':{'type':'keyword'},'run_id':{'type':'keyword'},
                'indexed_at_utc':{'type':'date'},'observed_at_utc':{'type':'date'},
                'result':{'properties':{'event_uid':{'type':'keyword'},'raw_sha256':{'type':'keyword'},
                    'scored_at_utc':{'type':'date'},'captured_at_utc':{'type':'date'}}}}}},method='PUT')
        if reply.get('acknowledged') is not True: raise RuntimeError('Index creation uncertain')
    return state


def run(args):
    global STOP
    if os.environ.get('DEMO_GPU_ALLOWED')!='1': raise RuntimeError('GPU reservation required')
    if datetime.now(timezone.utc).timestamp()>=args.stop_epoch-45: raise RuntimeError('Reservation expired')
    r=resources(args.run)
    rt.verify_sources()
    import confluent_kafka as api
    from confluent_kafka.admin import AdminClient
    from scoring import severity
    if api.version()[0]!='2.6.1': raise RuntimeError('Client version changed')
    admin=AdminClient({'bootstrap.servers':rt.TARGET,'socket.timeout.ms':5000})
    state=initialize(api,admin,args.run,r)
    clients=[]; counts={'captured':0,'scored':0,'indexed':0}
    def lag(client, topic):
        try:
            assigned=client.assignment()
            saved=client.committed(assigned,timeout=3)
            total=0
            for part in saved:
                if part.error or part.offset<0: return None
                low,high=client.get_watermark_offsets(part,timeout=3,cached=False)
                if not low<=part.offset<=high: return None
                total+=high-part.offset
            return total
        except Exception: return None
    def status(phase):
        index_ack(r['index'],'worker',{'doc_type':'worker','run_id':args.run,
            'worker':'bounded-morpheus-severity-demo','phase':phase,'observed_at_utc':stamp(),
            'session_counts':counts,'queue_lag':{name:lag(client,topic) for name,client,topic in zip(('capture','score','index'),clients,(common.SOURCE_TOPIC,r['raw'],r['output']))},'source_boundary':state['starts'],
            'boundary_recorded_at_utc':state['boundary_recorded_at_utc'],
            'production_ready':False,'automated_response_allowed':False})
    try:
        capture=consumer(api,rt.SOURCE,common.SOURCE_TOPIC,r['capture'],state['starts']); clients.append(capture)
        score=consumer(api,rt.TARGET,r['raw'],r['score']); clients.append(score)
        index=consumer(api,rt.TARGET,r['output'],r['indexer']); clients.append(index)
        producer=api.Producer({'bootstrap.servers':rt.TARGET,'enable.idempotence':True,
                              'acks':'all','delivery.timeout.ms':10000,'request.timeout.ms':3000})
        audit('worker_ready',run_id=args.run,worker='bounded-morpheus-severity-demo',
              stop_epoch=args.stop_epoch,source_boundary=state['starts'])
        status('waiting')
        while not STOP and time.time()<args.stop_epoch-45 and counts['indexed']<100:
            for msg in (collect(capture,2,min(8,100-counts["captured"])) if counts["captured"]<100 else []):
                ts=msg.timestamp()[1]
                env=common.envelope(msg.value(),state['source_cluster_id'],msg.topic(),msg.partition(),msg.offset(),
                                    ts if ts>=0 else None)
                send(producer,r['raw'],env['event_uid'].encode(),env,{r['raw']},lambda:rt.commit(capture,msg))
                counts['captured']+=1
                audit('captured',run_id=args.run,event_uid=env['event_uid'],raw_sha256=env['raw_sha256'],source=env['source'])
            rows=collect(score,1)
            if rows and not STOP and time.time()<args.stop_epoch-45:
                status('scoring'); started=time.monotonic()
                outputs=map_score([common.strict_json(m.value()) for m in rows],rows,severity)
                for out,msg in zip(outputs,rows):
                    send(producer,r['output'],msg.key(),out,{r['output']},lambda:rt.commit(score,msg))
                    counts['scored']+=1
                    audit('scored',run_id=args.run,event_uid=out['event_uid'],raw_sha256=out['raw_sha256'],
                          source=out['source'],engine_sha256=out['engine_sha256'],
                          score=out['high_severity_score'],scored_at_utc=out['scored_at_utc'])
                audit('batch_complete',run_id=args.run,rows=len(rows),seconds=time.monotonic()-started)
            for msg in collect(index,1):
                out=common.strict_json(msg.value()); docid=validate('severity',out,msg.key())
                saved=stamp()
                index_ack(r['index'],docid,{'doc_type':'event','run_id':args.run,
                    'worker':'bounded-morpheus-severity-demo','result':out,'indexed_at_utc':saved,
                    'indexed_at_meaning':'index_request_started','production_ready':False,
                    'automated_response_allowed':False})
                rt.commit(index,msg); counts['indexed']+=1
                audit('indexed',run_id=args.run,event_uid=out['event_uid'],raw_sha256=out['raw_sha256'],
                      source=out['source'],document_id=docid,ack_at_utc=stamp())
            status('waiting')
        status('stopped'); audit('worker_stopped',run_id=args.run,session_counts=counts)
    except BaseException as exc:
        audit('worker_failed',run_id=args.run,error_type=type(exc).__name__)
        try: status('failed')
        except Exception: pass
        raise
    finally:
        close_consumers(clients)


def close_consumers(clients):
    # Diagnostic watchdog only: original outer timeouts still enforce the bound.
    faulthandler.dump_traceback_later(20, repeat=True, file=sys.stderr)
    audit('shutdown_begin', consumer_count=len(clients))
    failures=[]
    for role, client in zip(('capture', 'score', 'index'), clients):
        started=time.monotonic()
        audit('consumer_close_begin', role=role)
        try:
            client.close()
        except BaseException as exc:
            audit('consumer_close_failed', role=role, error_type=type(exc).__name__)
            failures.append(exc)
        else:
            audit('consumer_close_done', role=role, seconds=time.monotonic()-started)
    if failures:
        raise RuntimeError('Consumer shutdown failed') from failures[0]
    audit('consumer_cleanup_complete')
    # Keep the watchdog active through run() local-object destruction.


def main():
    import fcntl
    parser=argparse.ArgumentParser(); parser.add_argument('--run',required=True)
    parser.add_argument('--stop-epoch',required=True,type=int); args=parser.parse_args()
    if not 0<args.stop_epoch-time.time()<=600: raise ValueError('Runtime must be at most 600 seconds')
    def stop(*_):
        global STOP
        STOP=True
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    with Path('/demo-state/worker.lock').open('a') as handle:
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        run(args)


if __name__=='__main__':
    code=0
    try:
        main()
        audit('worker_main_returned')
    except BaseException as exc:
        print(json.dumps({'kind':'demo_exit_failed','error_type':type(exc).__name__}),flush=True); code=1
    # All inputs/outputs acknowledged explicitly and consumers closed above.
    # Avoid third-party background threads delaying a bounded worker's exit.
    print(json.dumps({'kind':'process_exit_requested','exit_code':code}),flush=True)
    sys.stdout.flush(); sys.stderr.flush()
    faulthandler.cancel_dump_traceback_later()
    os._exit(code)
