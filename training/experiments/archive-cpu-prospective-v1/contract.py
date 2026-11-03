"""Candidate-only input and aggregate checks; no model imports or IO."""
from datetime import datetime, timezone
import math
import statistics

FEATURES = ('record_count','rows_with_structured_user','rows_with_structured_source_ip',
            'rows_with_fim_path','full_log_bytes_total','distinct_decoder_names','full_log_bytes_mean')
CAPTURE = '6e8478a917eebe277e725b746c08b481f34f4b805f7a7d6e24a096ed1c68510f'
MODEL = 'ecacecb3128f9ac6987315e2a1861fb02ac873f9fc42ddc11798a9fc0c25157e'
SOURCE = 'a32c517170fbf364581d65277ed9dc13ce497d1a1bd06b6b5a91c90e21183cc0'
PYTHON = '/opt/conda/envs/morpheus/bin/python'


def require(ok,message):
    if not ok: raise ValueError(message)


def validate_runtime(executable):
    require(type(executable) is str and executable.startswith('/opt/conda/envs/morpheus/bin/python'),
            'Morpheus Python environment required')


def validate(features,sidecars,expected_windows=12,expected_records=845):
    require(type(features) is list and type(sidecars) is list and len(features)==len(sidecars)==expected_windows,
            'input/window sidecar count')
    sides={}
    for row in sidecars:
        time=row.get('window_start_utc')
        require(type(time) is str and time not in sides,'sidecar timestamp duplicate')
        require(row.get('window_complete') is False and row.get('coverage_status')=='unknown' and
                row.get('quality_evaluation_eligible') is False,'coverage/evaluation status must remain unaccepted')
        require(type(row.get('nominally_inside_observation_interval')) is bool and
                type(row.get('syscollector_record_count')) is int and row['syscollector_record_count']>=0,
                'sidecar context')
        sides[time]=row
    previous=None; total=0
    for row in features:
        require(row.get('source_capture_sha256')==CAPTURE and row.get('window_seconds')==300 and
                row.get('window_complete') is False and row.get('production_ready') is False and
                row.get('automated_response_allowed') is False,'source/window flags')
        time=row.get('window_start_utc');require(type(time) is str and time in sides,'feature sidecar alignment')
        stamp=datetime.fromisoformat(time)
        require(stamp.utcoffset() is not None and stamp.utcoffset().total_seconds()==0 and
                stamp.timestamp()%300==0 and (previous is None or stamp>previous),'aligned ordered UTC windows')
        previous=stamp
        f=row.get('features');require(type(f) is dict and set(f)==set(FEATURES),'exact feature schema')
        require(all(type(f[k]) in (int,float) and math.isfinite(f[k]) and f[k]>=0 for k in FEATURES),'numeric features')
        require(all(type(f[k]) is int for k in FEATURES[:-1]),'integer feature counts')
        n=f['record_count'];require(n>0,'no empty fabricated windows')
        require(all(f[k]<=n for k in FEATURES[1:4]+('distinct_decoder_names',)),'count feature bounds')
        require(math.isclose(f['full_log_bytes_mean'],f['full_log_bytes_total']/n,rel_tol=1e-9,abs_tol=1e-9),'byte mean')
        require(sides[time]['syscollector_record_count']<=n,'nuisance count exceeds records')
        total+=n
    require(total==expected_records,'record totals')
    return sides


def aggregate(values):
    require(type(values) is list and all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in values),'score values')
    return dict(rows=len(values),minimum=min(values) if values else None,
                median=statistics.median(values) if values else None,maximum=max(values) if values else None)
