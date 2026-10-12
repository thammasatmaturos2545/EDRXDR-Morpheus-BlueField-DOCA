"""Six archived Kafka records to a new replay OpenSearch index; stdlib only."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

CONTAINER = 'edrxdr-replay-opensearch-1'
RUN = '20261012T141233Z-beaccd98dc'
RAW_HASH = 'dae332d54ffc04bdccf9dbd0b21deefbda26edf3343e8098da9d820cb6861714'
CODE_HASH = 'b771262172115730113c50a75cc01aa21bf252da661f22f03ce20988f0daad2d'
COUNTERS = ('rx_packets', 'tx_packets', 'rx_bytes', 'tx_bytes', 'rx_errors', 'tx_errors')

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def mapping():
    keywords = ('schema_version', 'processing_mode', 'capture_scope', 'event_type',
                'source_type', 'measurement_scope', 'ibdev', 'interface', 'operstate')
    properties = {k: {'type': 'keyword'} for k in keywords}
    properties.update({k: {'type': 'unsigned_long'} for k in (*COUNTERS, *('delta_' + c for c in COUNTERS))})
    properties.update({
        'timestamp': {'type': 'date'}, 'production_ready': {'type': 'boolean'},
        'carrier': {'type': 'byte', 'coerce': False},
        'sample_interval_seconds': {'type': 'double', 'coerce': False},
        'read_errors': {'type': 'object', 'enabled': False},
        'raw_event': {'type': 'object', 'enabled': False},
        'delta_status': {'type': 'object', 'dynamic': 'strict',
                         'properties': {c: {'type': 'keyword'} for c in COUNTERS}},
    })
    return {'settings': {'number_of_shards': 1, 'number_of_replicas': 0},
            'mappings': {'dynamic': 'strict', 'properties': properties}}

def validate_result(result, expected):
    require(result.get('timed_out') is False and result['_shards']['failed'] == 0, 'Incomplete search')
    require(result['hits']['total'] == {'value': 6, 'relation': 'eq'}, 'Expected exactly six indexed records')
    hits = result['hits']['hits']
    require(len(hits) == 6 and len({h['_id'] for h in hits}) == 6, 'Missing or duplicate results')
    require({h['_id']: h['_source'] for h in hits} == expected, 'Stored source differs from Kafka normalization')
    rows = [h['_source'] for h in hits]
    require(all(r['carrier'] is None and r['production_ready'] is False for r in rows), 'Null/flag mismatch')
    for c in COUNTERS:
        require(all(type(r[c]) is int and r[c] == 0 for r in rows), 'Counter zero mismatch')
        require(sum(r['delta_' + c] is None for r in rows) == 2, 'First-sample null mismatch')
        require(sum(type(r['delta_' + c]) is int and r['delta_' + c] == 0 for r in rows) == 4, 'Delta zero mismatch')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.home() / 'EDRXDR-Morpheus')
    args = parser.parse_args()
    require(sys.platform.startswith('linux'), 'Run this script on the VM')
    sys.dont_write_bytecode = True
    os.umask(0o077)
    base = args.repo / 'experiments/bluefield-review-20261012'
    source_run = args.repo / 'experiments/bluefield-kafka-runs' / RUN
    evidence = json.loads((source_run / 'report.json').read_text())
    require(evidence.get('status') == 'PASS' and evidence.get('records') == 6
            and evidence.get('record_bytes_equal') is True and evidence.get('normalized_equals_archived') is True,
            'Kafka PASS evidence missing')
    require(digest(source_run / 'received.jsonl') == RAW_HASH, 'Kafka input hash changed')
    require(digest(base / 'normalizer/normalize.py') == CODE_HASH, 'Normalizer source changed')
    spec = importlib.util.spec_from_file_location('review_normalizer', base / 'normalizer/normalize.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = [json.loads(x) for x in (source_run / 'normalized.jsonl').read_bytes().splitlines()]
    require(len(rows) == 6, 'Expected six normalized records')
    normalizer = module.Normalizer(rows[0]['capture_scope'])
    recomputed = [normalizer.normalize(json.loads(x)) for x in (source_run / 'received.jsonl').read_bytes().splitlines()]
    require(rows == recomputed, 'Saved normalization does not match recomputed source')
    expected = {f'{RUN}-{i}': r for i, r in enumerate(rows)}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    index = 'review-bluefield-' + stamp.lower()
    out = args.repo / 'experiments/bluefield-opensearch-runs' / stamp
    out.mkdir(parents=True, exist_ok=False)
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    report = {'status': 'RUNNING', 'index': index, 'container': CONTAINER,
              'kafka_report': str(source_run / 'report.json'), 'input_sha256': RAW_HASH,
              'normalized_sha256': digest(source_run / 'normalized.jsonl'),
              'scope': 'Archived six-record file-to-OpenSearch persistence check after Kafka replay; no continuous consumer, live sampling, GPU, dashboard or production-readiness claim.',
              'cleanup': 'Dedicated index retained for review; no automatic deletion configured.'}
    seq = 0

    def request(method, path, body=None):
        nonlocal seq
        seq += 1
        require(path.startswith('/' + index) or (method == 'GET' and path in ('/_cluster/health', '/_cat/indices?format=json&h=index')), 'Endpoint outside review scope')
        payload = b'' if body is None else (body if isinstance(body, bytes) else json.dumps(body, allow_nan=False).encode())
        argv = ['docker', 'exec', *(['-i'] if body is not None else []), CONTAINER,
                'curl', '-fsS', '--connect-timeout', '5', '--max-time', '20', '-X', method,
                'http://localhost:9200' + path]
        if body is not None:
            argv += ['-H', 'Content-Type: application/x-ndjson' if isinstance(body, bytes) else 'Content-Type: application/json', '--data-binary', '@-']
        print(f'Request {seq}: {method} {path}', flush=True)
        result = subprocess.run(argv, input=payload, capture_output=True, timeout=25)
        (out / f'{seq:02d}-response.json').write_bytes(result.stdout)
        (out / f'{seq:02d}-stderr.txt').write_bytes(result.stderr)
        require(result.returncode == 0, f'Request {seq} failed; see evidence directory')
        return json.loads(result.stdout)

    try:
        print('Evidence directory:', out, flush=True)
        info = json.loads(subprocess.check_output(['docker', 'inspect', CONTAINER], stdin=subprocess.DEVNULL, timeout=15))[0]
        require(info['State']['Running'] and set(info['NetworkSettings']['Networks']) == {'edrxdr-replay_replay-net'}, 'Unexpected replay container/network')
        health = request('GET', '/_cluster/health')
        require(health.get('status') in ('green', 'yellow') and health.get('timed_out') is False, 'Cluster unavailable')
        names = {r['index'] for r in request('GET', '/_cat/indices?format=json&h=index')}
        require({'shadow-severity-v1', 'shadow-behavioral-v1', 'replay-severity-v1'} <= names and index not in names, 'Replay index signature mismatch')
        configuration = mapping()
        (out / 'mapping-request.json').write_text(json.dumps(configuration, indent=2))
        created = request('PUT', '/' + index, configuration)
        require(created.get('acknowledged') is True and created.get('shards_acknowledged') is True, 'Index creation incomplete')
        bulk = ''.join(json.dumps({'create': {'_id': ident}}) + '\n' + json.dumps(row, allow_nan=False) + '\n' for ident, row in expected.items()).encode()
        written = request('POST', '/' + index + '/_bulk?refresh=wait_for', bulk)
        require(written.get('errors') is False and len(written['items']) == 6
                and all(item['create']['status'] == 201 for item in written['items']), 'Bulk write partial/failed')
        result = request('POST', '/' + index + '/_search', {'size': 10, 'track_total_hits': True, 'query': {'match_all': {}}})
        validate_result(result, expected)
        # Verify searchable missing values stay distinct from actual zero.
        filters = {'carrier_exists': {'exists': {'field': 'carrier'}},
                   'rx_zero': {'term': {'rx_bytes': 0}},
                   'delta_exists': {'exists': {'field': 'delta_rx_bytes'}},
                   'delta_zero': {'term': {'delta_rx_bytes': 0}}}
        counts = request('POST', '/' + index + '/_search', {'size': 0, 'aggs': {'checks': {'filters': {'filters': filters}}}})
        require(counts.get('timed_out') is False and counts['_shards']['failed'] == 0, 'Incomplete aggregation')
        actual = {k: v['doc_count'] for k, v in counts['aggregations']['checks']['buckets'].items()}
        require(actual == {'carrier_exists': 0, 'rx_zero': 6, 'delta_exists': 4, 'delta_zero': 4}, 'Null/zero indexing mismatch')
        report.update(status='PASS', records=6, source_equal=True, carrier_null=6, first_sample_null=2, computed_zero=4, query_counts=actual)
    except Exception as exc:
        report.update(status='FAIL', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        (out / 'report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)
        print('Saved:', out / 'report.json', flush=True)

if __name__ == '__main__':
    main()
