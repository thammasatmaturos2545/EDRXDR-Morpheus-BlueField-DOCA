from pathlib import Path
from datetime import datetime
import faulthandler, hashlib, json, os, pickle, sys
import numpy as np
import pandas as pd
import torch

os.umask(0o077)
faulthandler.dump_traceback_later(90, exit=True)
root = Path('/experiment')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected_model = 'ecacecb3128f9ac6987315e2a1861fb02ac873f9fc42ddc11798a9fc0c25157e'
expected_input = 'cfa27c706f1d33c85628329f79cb23a764d032d5149f91f9388ccbd07fbd4cff'
columns = [
    'record_count', 'rows_with_structured_user',
    'rows_with_structured_source_ip', 'rows_with_fim_path',
    'full_log_bytes_total', 'distinct_decoder_names', 'full_log_bytes_mean'
]
manifest_path = Path('/code/source-manifest.json')
assert sha(manifest_path) == \
    'a32c517170fbf364581d65277ed9dc13ce497d1a1bd06b6b5a91c90e21183cc0'
manifest = json.loads(manifest_path.read_bytes())
for name, digest in manifest['adapted_sha256'].items():
    assert sha(Path('/code/dfencoder_cpu')/name) == digest

sys.path.insert(0, '/code')
from dfencoder_cpu import AutoEncoder
torch.set_num_threads(2)

model_path = root/'model-private.pkl'
input_path = root/'input-private.jsonl'
assert sha(model_path) == expected_model
assert sha(input_path) == expected_input
rows = [json.loads(line) for line in input_path.read_bytes().splitlines()]
assert len(rows) == 12
times = []
for row in rows:
    assert set(row) == {'window_start_utc', 'features'}
    assert set(row['features']) == set(columns)
    stamp = datetime.fromisoformat(row['window_start_utc'])
    assert stamp.utcoffset() is not None
    assert stamp.utcoffset().total_seconds() == 0
    assert stamp.timestamp() % 300 == 0
    times.append(stamp)
    assert all(type(row['features'][k]) in (int, float) for k in columns)
assert times == sorted(set(times))
frame = pd.DataFrame(
    [[r['features'][k] for k in columns] for r in rows],
    columns=columns, dtype=np.float64)
assert np.isfinite(frame.to_numpy()).all()
assert (frame.to_numpy() >= 0).all()

# Only load the locally created, hash-bound prototype.
with model_path.open('rb') as f:
    model = pickle.load(f)
assert isinstance(model, AutoEncoder)
assert str(model.device) == 'cpu'
assert set(model.numeric_fts) == set(columns)
values = np.asarray(model.get_anomaly_score(frame), dtype=np.float64)
assert values.shape == (12,)
assert np.isfinite(values).all() and (values >= 0).all()

prior = [json.loads(line) for line in
         (root/'scores-private.jsonl').read_bytes().splitlines()]
assert [r['window_start_utc'] for r in prior] == [
    r['window_start_utc'] for r in rows]
assert np.allclose(values, [r['reconstruction_score'] for r in prior],
                   rtol=1e-6, atol=1e-8)

out = root/'adapter-observations-private.jsonl'
with out.open('x') as f:
    for i, (row, score) in enumerate(zip(rows, values), 1):
        observation = {
            'schema_version': 'dfp-archive-prototype-observation-1',
            'feature_contract': 'wazuh-archive-cpu-prototype-1',
            'model_sha256': expected_model,
            'source_artifact_sha256': expected_input,
            'source_record_ref': f'json-row:{i}',
            'window_start_utc': row['window_start_utc'],
            'reconstruction_score': float(score),
            'processing_mode': 'development_replay',
            'scoring_scope': 'in_sample_diagnostic',
            'production_ready': False,
            'automated_response_allowed': False,
            'quality_metrics_evaluated': False,
        }
        f.write(json.dumps(observation, sort_keys=True, allow_nan=False)+'\n')
summary = {
    'status': 'DFP_CPU_INFERENCE_ADAPTER_PASS',
    'observations': len(values),
    'training_score_parity': True,
    'output_sha256': sha(out),
    'adapter_sha256': sha(Path(__file__)),
    'training_performed': False,
    'network_writes': 0,
    'live_deployed': False,
    'bert_replaced': False,
}
with (root/'adapter-summary.json').open('x') as f:
    json.dump(summary, f, indent=2)
    f.write('\n')
print(json.dumps(summary, indent=2))
faulthandler.cancel_dump_traceback_later()
