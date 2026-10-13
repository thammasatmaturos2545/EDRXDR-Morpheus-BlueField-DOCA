"""Read-only quarantine sink inspection. No approval, journal writes or sender.

Deployment checks establish a local Docker trust boundary, not signed provenance.
Callers must not turn the returned metadata into replay authorization.
"""
import argparse
from datetime import datetime, timezone
import json
import re
import subprocess
import time
import bluefield_operator_contract as c

CONTAINER = 'edrxdr-replay-opensearch-1'
NETWORK = 'edrxdr-replay_replay-net'
PREFIX = 'shadow-bluefield-quarantine-dlq-'
UUID = re.compile(r'[A-Za-z0-9_-]{10,64}')
LIMIT = 65536

def names(run_id, evidence_id=None):
    c.token(run_id, c.RUN, 'invalid_run_id')
    if evidence_id is not None:
        c.token(evidence_id, c.HASH, 'invalid_evidence_id')
    return PREFIX + run_id

def strict_json(raw):
    c.require(type(raw) is bytes and 0 < len(raw) <= LIMIT, 'sink_response_size')
    def pairs(items):
        obj = {}
        for key, value in items:
            c.require(key not in obj, 'sink_duplicate_json_key')
            obj[key] = value
        return obj
    def constant(_):
        raise c.Rejected('sink_nonfinite_json')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except c.Rejected:
        raise
    except (ValueError, UnicodeError):
        raise c.Rejected('sink_invalid_json') from None

def index_metadata(reply, index, expected_uuid):
    c.require(type(reply) is dict and set(reply) == {index}, 'sink_index_resolution')
    item = reply[index]
    c.require(type(item) is dict and item.get('aliases') == {}, 'sink_alias_rejected')
    settings = item.get('settings', {}).get('index', {})
    c.require(settings.get('uuid') == expected_uuid, 'sink_index_uuid_changed')

def inspect_sink(reader, run_id, evidence_id, expected_uuid, *, clock=time.monotonic):
    index = names(run_id, evidence_id)
    c.token(expected_uuid, UUID, 'invalid_index_uuid')
    deadline = clock() + 30
    def read(path):
        left = deadline - clock()
        c.require(left > 0, 'sink_deadline')
        result = reader.get(path, min(left, 8))
        c.require(clock() < deadline, 'sink_deadline')
        return result
    index_metadata(read('/' + index), index, expected_uuid)
    doc = read('/' + index + '/_doc/' + evidence_id)
    c.require(type(doc) is dict and doc.get('found') is True, 'sink_document_missing')
    c.require(doc.get('_index') == index and doc.get('_id') == evidence_id, 'sink_document_identity')
    for key in ('_seq_no', '_primary_term', '_version'):
        c.require(type(doc.get(key)) is int and doc[key] >= (0 if key == '_seq_no' else 1), 'sink_document_version')
    envelope = doc.get('_source')
    digest = c.evidence(envelope, evidence_id)
    c.require(envelope['run_id'] == run_id, 'sink_run_mismatch')
    c.require(c.timestamp(envelope['quarantined_at_utc']) <= datetime.now(timezone.utc), 'future_evidence')
    index_metadata(read('/' + index), index, expected_uuid)
    # Not a lock: a second read detects changes observed during this inspection.
    again = read('/' + index + '/_doc/' + evidence_id)
    c.require(again == doc, 'sink_document_changed')
    return {'schema_version': 'bluefield-sink-inspection-1', 'status': 'verified_at_read',
            'index': index, 'index_uuid': expected_uuid, 'evidence_id': evidence_id,
            'evidence_sha256': digest, 'envelope': envelope,
            'document_version': {k: doc[k] for k in ('_seq_no', '_primary_term', '_version')},
            'trust_scope': 'local_docker_deployment_checked_not_signed_provenance',
            'replay_authorized': False, 'transport_enabled': False, 'production_ready': False,
            'automated_response_allowed': False}

class HostReader:
    """Host-only fixed-container GET adapter. Requires normal Docker access."""
    def __init__(self):
        self.container_id = None

    @staticmethod
    def execute(args, seconds):
        try:
            result = subprocess.run(args, input=b'', capture_output=True, timeout=seconds)
        except (OSError, subprocess.TimeoutExpired):
            raise c.Rejected('sink_command_failed') from None
        c.require(result.returncode == 0, 'sink_command_failed')
        return result.stdout

    def check(self):
        state = self.execute(['systemctl', 'show', 'edrxdr-bluefield.service', '--no-pager',
                              '-p', 'ActiveState', '-p', 'SubState', '-p', 'UnitFileState'], 5)
        c.require(set(state.decode().splitlines()) == {'ActiveState=inactive', 'SubState=dead', 'UnitFileState=disabled'}, 'service_state_changed')
        info = json.loads(self.execute(['docker', 'inspect', CONTAINER], 5))[0]
        c.require(info['State']['Running'] is True and info['Config']['Image'] == 'opensearchproject/opensearch:2.11.0'
                  and set(info['NetworkSettings']['Networks']) == {NETWORK}, 'sink_deployment_changed')
        if self.container_id is None:
            self.container_id = info['Id']
        c.require(self.container_id == info['Id'], 'sink_container_replaced')

    def get(self, path, timeout):
        metadata = '/_cat/indices?format=json&h=index,uuid'
        c.require(path == metadata or re.fullmatch(r'/shadow-bluefield-quarantine-dlq-[a-z0-9][a-z0-9-]{7,39}(?:/_doc/[0-9a-f]{64})?', path), 'sink_path_rejected')
        c.require(self.container_id is not None, 'sink_preflight_required')
        # Fixed container ID and loopback endpoint; never follow redirects/proxies.
        raw = self.execute(['docker', 'exec', self.container_id, 'timeout', '--kill-after=1s', str(max(1, int(timeout)))+'s',
                            'curl', '-q', '-fsS', '--noproxy', '*', '--connect-timeout', '2',
                            '--max-time', str(timeout), '--max-filesize', str(LIMIT),
                            'http://localhost:9200' + path], timeout + 2)
        return strict_json(raw)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('preflight')
    p = sub.add_parser('inspect')
    p.add_argument('--run-id', required=True)
    p.add_argument('--evidence-id', required=True)
    p.add_argument('--index-uuid', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            names(args.run_id, args.evidence_id)
            c.token(args.index_uuid, UUID, 'invalid_index_uuid')
        reader = HostReader()
        reader.check()
        if args.command == 'preflight':
            rows = reader.get('/_cat/indices?format=json&h=index,uuid', 8)
            c.require(type(rows) is list, 'sink_metadata_invalid')
            found = []
            for row in rows:
                c.require(type(row) is dict and type(row.get('index')) is str, 'sink_metadata_invalid')
                if row['index'].startswith(PREFIX):
                    names(row['index'][len(PREFIX):])
                    c.token(row.get('uuid'), UUID, 'invalid_index_uuid')
                    found.append({'index': row['index'], 'uuid': row['uuid']})
            result = {'status': 'deployment_checked', 'quarantine_indices': found,
                      'replay_authorized': False, 'production_ready': False}
        else:
            result = inspect_sink(reader, args.run_id, args.evidence_id, args.index_uuid)
        reader.check()
        print(json.dumps(result, allow_nan=False))
        return 0
    except c.Rejected as exc:
        print(json.dumps({'status': 'rejected', 'reason': str(exc), 'replay_authorized': False}))
        return 1
    except Exception:
        print(json.dumps({'status': 'rejected', 'reason': 'sink_inspection_failed', 'replay_authorized': False}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
