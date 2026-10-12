"""Bounded replay of six archived records; no live telemetry or GPU claim."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

PINS = {
    'normalizer/normalize.py': 'b771262172115730113c50a75cc01aa21bf252da661f22f03ce20988f0daad2d',
    'evidence/monitor/monitor.jsonl': 'dae332d54ffc04bdccf9dbd0b21deefbda26edf3343e8098da9d820cb6861714',
    'evidence/normalizer/normalized.jsonl': '868fb94d8cbf982084b99a3794622d801af15dd92110dd2109782c158e14d3f1',
}
BROKER = 'edrxdr-replay-kafka-1'

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def inputs(base):
    for name, expected in PINS.items():
        require(hashlib.sha256((base / name).read_bytes()).hexdigest() == expected,
                'Source/evidence changed: ' + name)
    spec = importlib.util.spec_from_file_location('review_normalize', base / 'normalizer/normalize.py')
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    raw = (base / 'evidence/monitor/monitor.jsonl').read_bytes()
    expected = [json.loads(x) for x in (base / 'evidence/normalizer/normalized.jsonl').read_bytes().splitlines()]
    require(len(raw.splitlines()) == len(expected) == 6, 'Expected exactly six records')
    return module, raw, expected

def verify(module, raw, received, expected):
    require(received.splitlines() == raw.splitlines(), 'Kafka record bytes/order mismatch')
    normalizer = module.Normalizer(expected[0]['capture_scope'])
    rows = [normalizer.normalize(json.loads(line)) for line in received.splitlines()]
    require(rows == expected, 'Normalized output differs from archived evidence')
    require(all(r['carrier'] is None for r in rows), 'Carrier null lost')
    for field in module.COUNTERS:
        require(all(r[field] == 0 for r in rows), 'Zero counter changed')
        require(sum(r['delta_status'][field] == 'first_sample' and r['delta_' + field] is None for r in rows) == 2,
                'First-sample null mismatch')
        require(sum(r['delta_status'][field] == 'computed' and r['delta_' + field] == 0 for r in rows) == 4,
                'Computed zero mismatch')
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.home() / 'EDRXDR-Morpheus')
    parser.add_argument('--local-check', action='store_true', help='No Docker or broker access')
    args = parser.parse_args()
    base = args.repo / 'experiments/bluefield-review-20261012'
    module, raw, expected = inputs(base)
    verify(module, raw, raw, expected)
    if args.local_check:
        for corrupted in (raw.replace(b'"carrier":null', b'"carrier":0', 1),
                          b'\n'.join(raw.splitlines()[::-1]) + b'\n',
                          b'\n'.join(raw.splitlines()[:-1]) + b'\n'):
            try:
                verify(module, raw, corrupted, expected)
            except RuntimeError:
                pass
            else:
                raise RuntimeError('Negative verification check failed')
        print('PASS local: pinned evidence, six normalized records, null/zero/delta and three rejection checks; Kafka not tested')
        return
    require(sys.platform.startswith('linux'), 'Run broker test on Linux VM')
    os.umask(0o077)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:10]
    topic = 'review-bluefield-' + run_id.lower()
    out = args.repo / 'experiments/bluefield-kafka-runs' / run_id
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'RUNNING', 'topic': topic, 'broker': BROKER,
              'runner_version': '20261012-stdin-fix-1',
              'scope': 'Archived six-record Kafka transport and offline normalization only; shared replay broker, isolated topic. No live sampling, GPU, OpenSearch or model-quality claim.',
              'hashes': PINS, 'consumer_mode': 'explicit partition 0; no group commits',
              'topic_cleanup': 'New topic retained for review; retention.ms=86400000. Topic itself is not auto-deleted.'}
    (out / 'report.json').write_text(json.dumps(report, indent=2))
    print('Evidence directory:', out, flush=True)
    sequence = 0

    def run(argv, data=None, seconds=40):
        nonlocal sequence
        sequence += 1
        stem = out / f'command-{sequence:02d}'
        stem.with_suffix('.json').write_text(json.dumps(argv))
        started = time.monotonic()
        print(f'Command {sequence}: starting', flush=True)
        try:
            # Never inherit the terminal through timeout/docker. Only the producer
            # receives bytes; all other commands receive immediate EOF.
            result = subprocess.run(argv, input=b'' if data is None else data,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds)
        except subprocess.TimeoutExpired as exc:
            stem.with_suffix('.stdout').write_bytes(exc.stdout or b'')
            stem.with_suffix('.stderr').write_bytes(exc.stderr or b'')
            raise
        finally:
            stem.with_suffix('.timing.json').write_text(json.dumps({'elapsed_seconds': time.monotonic() - started}))
        stem.with_suffix('.stdout').write_bytes(result.stdout)
        stem.with_suffix('.stderr').write_bytes(result.stderr)
        require(result.returncode == 0, f'Command {sequence} failed ({result.returncode}); see {stem}.stderr')
        return result.stdout

    def kafka(tool, *options, data=None):
        interactive = ['-i'] if data is not None else []
        return run(['timeout', '--kill-after=3s', '35s', 'docker', 'exec', *interactive, BROKER,
                    'timeout', '--kill-after=2s', '25s', '/opt/kafka/bin/' + tool,
                    '--bootstrap-server', 'localhost:29092', *options], data=data)

    try:
        info = json.loads(run(['docker', 'inspect', BROKER]))[0]
        require(info['State']['Running'], 'Replay broker not running')
        env = dict(x.split('=', 1) for x in info['Config']['Env'] if '=' in x)
        require(env.get('KAFKA_ADVERTISED_LISTENERS') == 'INTERNAL://kafka:29092', 'Unexpected replay listener')
        require(set(info['NetworkSettings']['Networks']) == {'edrxdr-replay_replay-net'}, 'Unexpected broker networks')
        report['commit'] = run(['git', '-C', str(args.repo), 'rev-parse', 'HEAD']).decode().strip()
        topics = kafka('kafka-topics.sh', '--list').decode().splitlines()
        require('replay-wazuh-alerts' in topics and 'wazuh-alerts' not in topics and 'bluefield-events' not in topics,
                'Replay topic signature mismatch')
        require(topic not in topics, 'Topic already exists')
        kafka('kafka-topics.sh', '--create', '--topic', topic, '--partitions', '1', '--replication-factor', '1',
              '--config', 'retention.ms=86400000', '--config', 'cleanup.policy=delete')
        kafka('kafka-console-producer.sh', '--topic', topic,
              '--producer-property', 'acks=all', '--producer-property', 'enable.idempotence=true',
              '--producer-property', 'request.timeout.ms=10000',
              '--producer-property', 'delivery.timeout.ms=20000', data=raw)
        offsets = kafka('kafka-get-offsets.sh', '--topic', topic, '--time', '-1').decode().strip()
        require(offsets == topic + ':0:6', 'Expected exactly six records in new partition: ' + offsets)
        received = kafka('kafka-console-consumer.sh', '--topic', topic, '--partition', '0', '--offset', 'earliest',
                         '--max-messages', '6', '--timeout-ms', '15000',
                         '--consumer-property', 'enable.auto.commit=false')
        (out / 'received.jsonl').write_bytes(received)
        rows = verify(module, raw, received, expected)
        (out / 'normalized.jsonl').write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in rows))
        report.update(status='PASS', records=6, carrier_null=6, first_sample_null=2, computed_zero=4,
                      record_bytes_equal=True, normalized_equals_archived=True,
                      input_sha256=hashlib.sha256(raw).hexdigest(),
                      received_sha256=hashlib.sha256(received).hexdigest())
    except Exception as exc:
        report.update(status='FAIL', error=str(exc), error_type=type(exc).__name__)
        raise
    finally:
        (out / 'report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)
        print('Saved:', out / 'report.json', flush=True)

if __name__ == '__main__':
    main()
