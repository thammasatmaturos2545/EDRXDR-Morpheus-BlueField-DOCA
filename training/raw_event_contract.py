"""Raw event bridge: reuse the frozen v2 text builder, never serialize other fields."""
import gzip
import hashlib
import json
from pathlib import Path
from build_context_dataset import context_text


def event_text(event):
    if not isinstance(event, dict):
        raise ValueError('Event must be an object')
    rule = event.get('rule')
    if rule is None:
        rule = {}
    if not isinstance(rule, dict):
        raise ValueError('rule must be an object or null')
    # Preserve the existing builder exactly, including its falsy-value handling.
    return context_text(dict(event, rule=rule))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reconstruct(snapshot, manifest, data):
    """Select ONLY train/validation pointers; do not transform/score held-out rows."""
    snapshot = Path(snapshot).resolve()
    wanted = {}
    for split, rows in data.items():
        if split not in ('train', 'validation'):
            raise ValueError('Held-out split forbidden')
        for row in rows:
            key = (row['source_file'], row['source_line'])
            if key in wanted:
                raise ValueError('Duplicate source pointer')
            wanted[key] = (split, row)
    found = {}
    source_hashes = {}
    for relative in sorted({key[0] for key in wanted}):
        path = (snapshot / relative).resolve()
        if not path.is_relative_to(snapshot):
            raise ValueError('Unsafe source path')
        actual = sha(path)
        if actual != manifest['source_sha256'][relative]:
            raise ValueError('Snapshot hash mismatch')
        source_hashes[relative] = actual
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for number, line in enumerate(stream, 1):
                key = (relative, number)
                if key not in wanted:
                    continue
                split, row = wanted[key]
                event = json.loads(line)
                identity = [str(event['manager']['name']), str(event['agent']['id']), str(event['id'])]
                event_id = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
                if event_id != row['event_id'] or str(event['rule']['id']) != row['rule_id']:
                    raise ValueError('Raw event identity mismatch')
                text = event_text(event)
                if text != row['text_input']:
                    raise ValueError('Raw-to-training-text mismatch')
                level = event['rule']['level']
                if type(level) is not int or not 0 <= level <= 15:
                    raise ValueError('Invalid raw severity')
                expected = 'high_severity' if level >= 7 else 'low_severity'
                if expected != row['weak_label']:
                    raise ValueError('Raw weak-label mismatch')
                found[key] = text
    if found.keys() != wanted.keys():
        raise ValueError('Missing source rows')
    # Keep original ordering; raw-derived text is what enters the existing pipeline.
    for rows in data.values():
        for row in rows:
            row['text_input'] = found[(row['source_file'], row['source_line'])]
    return dict(status='PASS', reconstructed_rows=len(found), source_sha256=source_hashes,
                contract='wazuh-context-v2-raw-1', held_out_data_used=False)


def missing_field_samples():
    return [event_text(e) for e in (
        {'rule': {'description': ' package updated '}, 'full_log': ' pkg=x '},
        {'rule': {'description': 'package updated'}},
        {'full_log': 'package installed'},
        {'rule': None, 'full_log': 'package removed'},
        {'rule': {'description': None}, 'full_log': 'package installed'},
        {'rule': {'description': 'package updated'}, 'full_log': '   '},
    )]
