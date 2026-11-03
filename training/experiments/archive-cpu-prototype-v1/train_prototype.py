from pathlib import Path
import faulthandler, hashlib, json, os, pickle, subprocess, sys
import numpy as np
import pandas as pd
import torch

os.umask(0o077)
faulthandler.dump_traceback_later(240, exit=True)
ROOT = Path('/experiment')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

# Verify the CPU adaptation before importing it.
manifest = json.loads(Path('/code/source-manifest.json').read_bytes())
for name, digest in manifest['adapted_sha256'].items():
    assert sha(Path('/code/dfencoder_cpu')/name) == digest
sys.path.insert(0, '/code')
from dfencoder_cpu import AutoEncoder

torch.set_num_threads(2)
torch.manual_seed(42)
np.random.seed(42)
plan = json.loads((ROOT/'plan.json').read_bytes())
assert plan['status'] == 'FROZEN_DEVELOPMENT_PROTOTYPE_PLAN'
assert plan['device'] == 'cpu' and plan['epochs'] == 5
assert plan['live_deployment_allowed'] is False
assert plan['threshold_selection_allowed'] is False
assert plan['independent_evaluation_windows'] == 0
assert sha(ROOT/'input-private.jsonl') == plan['input_sha256'] == \
    'cfa27c706f1d33c85628329f79cb23a764d032d5149f91f9388ccbd07fbd4cff'
rows = [json.loads(line) for line in
        (ROOT/'input-private.jsonl').read_bytes().splitlines()]
columns = plan['feature_order']
assert len(rows) == plan['fit_windows'] == 12 and len(columns) == 7
frame = pd.DataFrame(
    [[r['features'][k] for k in columns] for r in rows],
    columns=columns, dtype=np.float64)
assert np.isfinite(frame.to_numpy()).all()

def score(model):
    values = np.asarray(model.get_anomaly_score(frame.copy()), dtype=np.float64)
    assert values.shape == (12,)
    assert np.isfinite(values).all() and (values >= 0).all()
    return values

model_path = ROOT/'model-private.pkl'
if len(sys.argv) == 3 and sys.argv[1] == '--reload':
    assert sha(model_path) == sys.argv[2]
    # Load only the artifact just created by this local experiment.
    with model_path.open('rb') as f:
        model = pickle.load(f)
    assert str(model.device) == 'cpu'
    with (ROOT/'reload-scores-private.npy').open('xb') as f:
        np.save(f, score(model), allow_pickle=False)
    print('FRESH_PROCESS_RELOAD_SCORE_PASS')
else:
    assert len(sys.argv) == 1
    assert not model_path.exists()
    model = AutoEncoder(
        encoder_layers=[16, 8], decoder_layers=[16],
        device='cpu', batch_size=4, eval_batch_size=16,
        progress_bar=False, verbose=False,
    )
    model.fit(frame.copy(), epochs=5)
    before = score(model)
    with model_path.open('xb') as f:
        pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)
    model_sha = sha(model_path)
    subprocess.run(
        [sys.executable, '-B', __file__, '--reload', model_sha],
        check=True, timeout=120)
    after = np.load(ROOT/'reload-scores-private.npy', allow_pickle=False)
    assert np.allclose(before, after, rtol=1e-6, atol=1e-8)
    assert not any(n in sys.modules for n in ('cudf', 'cupy'))

    with (ROOT/'scores-private.jsonl').open('x') as f:
        for row, value in zip(rows, after):
            f.write(json.dumps({
                'window_start_utc': row['window_start_utc'],
                'reconstruction_score': float(value),
                'scoring_scope': 'in_sample_diagnostic',
            }, allow_nan=False)+'\n')

    summary = {
        'status': 'DFP_CPU_PROTOTYPE_FIT_RELOAD_SCORE_PASS',
        'model_name': 'EDRXDR-ARCHIVE-CPU-PROTOTYPE',
        'feature_contract': plan['feature_contract'],
        'fit_windows': 12, 'scored_windows': 12, 'epochs': 5,
        'device': 'cpu',
        'fresh_process_reload_parity': True,
        'model_sha256': model_sha,
        'cpu_source_manifest_sha256': sha(Path('/code/source-manifest.json')),
        'runner_sha256': sha(Path(__file__)),
        'input_sha256': plan['input_sha256'],
        'scoring_scope': 'in_sample_diagnostic',
        'independent_evaluation_windows': 0,
        'quality_metrics_evaluated': False,
        'protected_datasets_accessed': False,
        'live_deployed': False,
        'production_ready': False,
        'automated_response_allowed': False,
        'bert_replaced': False,
    }
    with (ROOT/'training-summary.json').open('x') as f:
        json.dump(summary, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps(summary, indent=2))
faulthandler.cancel_dump_traceback_later()
