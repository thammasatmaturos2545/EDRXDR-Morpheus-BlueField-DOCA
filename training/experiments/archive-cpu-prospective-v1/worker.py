"""Explicit frozen-model CPU diagnostics; never calls fit or writes the model."""
from pathlib import Path
import faulthandler
import hashlib
import json
import os
import pickle
import re
import sys
import time
from contract import FEATURES,CAPTURE,MODEL,SOURCE,require,validate,aggregate,validate_runtime


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    os.umask(0o077);faulthandler.dump_traceback_later(180,exit=True)
    validate_runtime(sys.executable)
    require(os.environ.get('CUDA_VISIBLE_DEVICES')=='-1' and os.environ.get('NVIDIA_VISIBLE_DEVICES')=='void','CPU environment')
    p=json.loads(Path('/inputs/plan.json').read_bytes())
    require(p['mode']=='frozen_cpu_diagnostic_no_fit' and p['model_sha256']==MODEL and
            p['cpu_source_manifest_sha256']==SOURCE and p['source_capture_sha256']==CAPTURE,'diagnostic plan binding')
    def bound(path,expected):
        raw=Path(path).read_bytes();require(sha(raw)==expected,'artifact binding mismatch');return raw
    model_raw=bound('/model/model.pkl',MODEL)
    manifest=json.loads(bound('/code/source-manifest.json',SOURCE))
    code=Path('/code/dfencoder_cpu')
    for name,digest in manifest['adapted_sha256'].items():
        target=code/name
        require(not target.is_symlink() and target.resolve().is_relative_to(code),'adaptation source path')
        bound(target,digest)
    rows=[json.loads(line) for line in bound('/inputs/features.jsonl',p['features_sha256']).splitlines()]
    sidecars=[json.loads(line) for line in bound('/inputs/coverage.jsonl',p['coverage_sha256']).splitlines()]
    sides=validate(rows,sidecars)
    # Heavy imports occur only after every input/code/model binding check.
    sys.path.insert(0,'/code')
    import numpy as np
    import pandas as pd
    import torch
    from dfencoder_cpu import AutoEncoder
    torch.set_num_threads(2)
    frame=pd.DataFrame([[r['features'][k] for k in FEATURES] for r in rows],columns=list(FEATURES),dtype=np.float64)
    # Only the locally produced, previously verified model artifact is loaded.
    with Path('/model/model.pkl').open('rb') as stream:model=pickle.load(stream)
    require(type(model) is AutoEncoder and str(model.device)=='cpu','model type/device')
    require(list(model.numeric_fts)==list(FEATURES) and list(model.num_names)==list(FEATURES),'fitted numeric feature order')
    require(not model.binary_fts and not model.categorical_fts,'unexpected feature families')
    scaler_classes={}
    for feature in model.numeric_fts.values():
        name=type(feature['scaler']).__name__
        scaler_classes[name]=scaler_classes.get(name,0)+1
    started=time.monotonic()
    first=np.asarray(model.get_anomaly_score(frame.copy()),dtype=np.float64)
    second=np.asarray(model.get_anomaly_score(frame.copy()),dtype=np.float64)
    mse,bce,cce=model.get_anomaly_score_losses(frame.copy())
    require(first.shape==second.shape==(12,) and tuple(mse.shape)==(12,7) and bce.numel()==cce.numel()==0,'numeric score/loss shape')
    require(np.isfinite(first).all() and (first>=0).all() and np.allclose(first,second,rtol=1e-6,atol=1e-8),'finite repeatable scores')
    means=np.asarray(mse.mean(dim=1).cpu().numpy(),dtype=np.float64)
    require(np.allclose(first,means,rtol=1e-6,atol=1e-8),'transformed numeric squared-loss mean')
    require(not any(k in sys.modules for k in ('cudf','cupy')),'unexpected GPU module import')
    require(sha(Path('/model/model.pkl').read_bytes())==MODEL,'model artifact changed')
    values=[float(v) for v in first]
    indices_inside=[i for i,r in enumerate(rows) if sides[r['window_start_utc']]['nominally_inside_observation_interval']]
    indices_boundary=[i for i in range(12) if i not in indices_inside]
    indices_nuisance=[i for i,r in enumerate(rows) if sides[r['window_start_utc']]['syscollector_record_count']>0]
    report=dict(status='FROZEN_CPU_NEW_CAPTURE_DIAGNOSTIC_PASS_NOT_QUALITY_ACCEPTANCE',
                model_sha256=MODEL,cpu_source_manifest_sha256=SOURCE,source_capture_sha256=CAPTURE,
                features_sha256=p['features_sha256'],coverage_sha256=p['coverage_sha256'],
                feature_order=list(FEATURES),numeric_scaler_class_counts=scaler_classes,
                scored_windows=12,scored_records=845,scoring_passes=3,device='cpu',
                repeat_score_parity=True,numeric_loss_mean_parity=True,elapsed_seconds=time.monotonic()-started,
                score_semantics='mean_squared_reconstruction_error_transformed_numeric_features',
                all_windows=aggregate(values),nominally_inside_observation=aggregate([values[i] for i in indices_inside]),
                boundary_windows=aggregate([values[i] for i in indices_boundary]),
                syscollector_indicator_windows=aggregate([values[i] for i in indices_nuisance]),
                independent_quality_evaluation_windows=0,source_coverage_accepted=False,
                threshold_selected=False,quality_metrics_evaluated=False,training_performed=False,
                gpu_used=False,network_writes=0,production_ready=False,automated_response_allowed=False,
                live_deployed=False,bert_replaced=False)
    out=Path('/output');hashes={}
    payload=b''.join((json.dumps(dict(window_start_utc=row['window_start_utc'],reconstruction_score=value,
                       source_capture_sha256=CAPTURE,model_sha256=MODEL,processing_mode='offline_frozen_cpu_diagnostic',
                       coverage_status='unknown',window_complete=False,quality_evaluation_eligible=False,
                       production_ready=False,automated_response_allowed=False),sort_keys=True,allow_nan=False)+'\n').encode()
                     for row,value in zip(rows,values))
    with (out/'scores-private.jsonl').open('xb') as stream:stream.write(payload)
    hashes['scores-private.jsonl']=sha(payload)
    raw=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
    with (out/'aggregate-report.json').open('xb') as stream:stream.write(raw)
    hashes['aggregate-report.json']=sha(raw)
    with (out/'SHA256.json').open('x') as stream:json.dump(hashes,stream,indent=2);stream.write('\n')
    faulthandler.cancel_dump_traceback_later()


if __name__=='__main__':
    try:main()
    except ModuleNotFoundError as error:
        name=error.name or ''
        print('CPU_DIAGNOSTIC_STOP MISSING_MODULE',
              name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,100}',name) else 'DETAILS_WITHHELD')
        raise SystemExit(1)
    except Exception as error:
        print('CPU_DIAGNOSTIC_STOP',str(error) if type(error) is ValueError else type(error).__name__)
        raise SystemExit(1)
