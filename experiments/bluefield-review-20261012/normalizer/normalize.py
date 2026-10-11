"""Offline-only normalization of bluefield-monitor-review-1 JSONL; stdlib only."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

COUNTERS = ('rx_packets', 'tx_packets', 'rx_bytes', 'tx_bytes', 'rx_errors', 'tx_errors')
STATES = {'unknown', 'notpresent', 'down', 'lowerlayerdown', 'testing', 'dormant', 'up'}


def validate(event):
    if not isinstance(event, dict) or event.get('schema_version') != 'bluefield-monitor-review-1':
        raise ValueError('Expected bluefield-monitor-review-1 object')
    if event.get('source') != 'bluefield' or event.get('measurement_scope') != 'host_interface_counters':
        raise ValueError('Unexpected source or measurement scope')
    for field in ('ibdev', 'interface'):
        value = event.get(field)
        if field == 'interface' and value is None:
            continue
        if not isinstance(value, str) or not value or len(value) > 255 or '/' in value:
            raise ValueError(f'Invalid {field}')
    timestamp = event.get('timestamp')
    if not isinstance(timestamp, str):
        raise ValueError('Timestamp required')
    time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if time.tzinfo is None:
        raise ValueError('Timestamp must contain timezone')
    errors = event.get('read_errors')
    if not isinstance(errors, dict) or any(not isinstance(v, str) or not v for v in errors.values()):
        raise ValueError('Invalid read_errors')
    allowed = {'interface', 'operstate', 'carrier', *COUNTERS}
    if set(errors) - allowed:
        raise ValueError('Unexpected error fields')
    for field in allowed:
        if field not in event:
            raise ValueError(f'Missing field {field}')
        if (event[field] is None) != (field in errors):
            raise ValueError(f'Inconsistent error/value for {field}')
    for field in COUNTERS:
        value = event[field]
        if value is not None and (type(value) is not int or not 0 <= value <= 2**64 - 1):
            raise ValueError(f'Invalid unsigned counter {field}')
    if event['carrier'] is not None and (type(event['carrier']) is not int or event['carrier'] not in (0, 1)):
        raise ValueError('Invalid carrier')
    if event['operstate'] is not None and event['operstate'] not in STATES:
        raise ValueError('Invalid operstate')
    if event['interface'] is None and any(event[k] is not None for k in ('operstate', 'carrier', *COUNTERS)):
        raise ValueError('Unmapped interface cannot have readings')
    return time


class Normalizer:
    def __init__(self, capture_scope, max_gap_seconds=10):
        if not isinstance(capture_scope, str) or not capture_scope.strip():
            raise ValueError('Explicit capture scope required')
        if max_gap_seconds <= 0:
            raise ValueError('Positive maximum gap required')
        self.scope = capture_scope
        self.max_gap = max_gap_seconds
        self.previous = {}

    def normalize(self, event):
        time = validate(event)
        key = event['ibdev']
        old = self.previous.get(key)
        if old and time <= old['time']:
            raise ValueError('Duplicate or out-of-order sample; state not changed')
        if old is None and len(self.previous) >= 128:
            raise ValueError('Offline device limit exceeded')
        interval = (time - old['time']).total_seconds() if old else None
        reason = ('first_sample' if not old else
                  'interface_changed' if event['interface'] != old['event']['interface'] else
                  'sample_gap' if interval > self.max_gap else None)
        deltas, reasons = {}, {}
        for field in COUNTERS:
            value = event[field]
            prior = old['event'][field] if old else None
            why = ('unavailable' if value is None else reason or
                   ('baseline_unavailable' if prior is None else
                    'counter_decreased' if value < prior else None))
            deltas['delta_' + field] = None if why else value - prior
            reasons[field] = why or 'computed'
        out = {
            'schema_version': 'bluefield-normalized-review-1',
            'processing_mode': 'offline_review',
            'production_ready': False,
            'capture_scope': self.scope,
            'timestamp': event['timestamp'],
            'event_type': 'network_telemetry',
            'source_type': 'bluefield',
            'measurement_scope': event['measurement_scope'],
            'ibdev': key, 'interface': event['interface'],
            'operstate': event['operstate'], 'carrier': event['carrier'],
            'read_errors': deepcopy(event['read_errors']),
            **{field: event[field] for field in COUNTERS}, **deltas,
            'delta_status': reasons,
            'sample_interval_seconds': interval,
            'raw_event': deepcopy(event),
        }
        self.previous[key] = {'time': time, 'event': deepcopy(event)}
        return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--capture-scope', required=True, help='One host/capture session only')
    args = parser.parse_args()
    # Validate the whole bounded input before creating an output; never overwrite.
    if args.input.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Input exceeds 8 MiB offline limit')
    normalizer = Normalizer(args.capture_scope)
    rows = []
    for line_number, line in enumerate(args.input.read_text(encoding='utf-8').splitlines(), 1):
        if len(rows) >= 10000:
            raise ValueError('Input exceeds 10000 records')
        try:
            rows.append(normalizer.normalize(json.loads(line)))
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Line {line_number}: {exc}') from exc
    if not rows:
        raise ValueError('Empty input')
    with args.output.open('x', encoding='utf-8', newline='\n') as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    print(f'PASS: normalized {len(rows)} file records to {args.output}; no broker access')


if __name__ == '__main__':
    main()
