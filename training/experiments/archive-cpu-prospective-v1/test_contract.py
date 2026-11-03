import copy
import unittest
from contract import FEATURES,CAPTURE,aggregate,validate,validate_runtime,PYTHON


def fixture():
    features=[];sides=[]
    for i in range(12):
        n=70 if i<11 else 75;time=f'2030-01-01T00:{i*5:02}:00+00:00'
        features.append(dict(source_capture_sha256=CAPTURE,window_start_utc=time,window_seconds=300,
                             window_complete=False,production_ready=False,automated_response_allowed=False,
                             features=dict(zip(FEATURES,[n,0,0,0,n*10,1,10.0]))))
        sides.append(dict(window_start_utc=time,window_complete=False,coverage_status='unknown',
                          quality_evaluation_eligible=False,nominally_inside_observation_interval=i not in (0,11),
                          syscollector_record_count=0))
    return features,sides


class ContractTests(unittest.TestCase):
    def test_wrong_python_environment_rejected(self):
        validate_runtime(PYTHON)
        for path in ('/usr/bin/python3','/usr/local/bin/python','python'):
            with self.assertRaises(ValueError):validate_runtime(path)

    def test_new_twelve_windows_and_no_mutation(self):
        a,b=fixture();before=copy.deepcopy((a,b))
        self.assertEqual(len(validate(a,b)),12);self.assertEqual((a,b),before)

    def test_foreign_capture_and_incomplete_status_change_rejected(self):
        for field,value in [('source_capture_sha256','a'*64),('window_complete',True),('production_ready',True)]:
            a,b=fixture();a[0][field]=value
            with self.assertRaises(ValueError):validate(a,b)

    def test_nan_bool_and_negative_rejected(self):
        for value in (float('nan'),True,-1):
            a,b=fixture();a[0]['features']['record_count']=value
            with self.assertRaises(ValueError):validate(a,b)

    def test_duplicate_sidecars_and_time_rejected(self):
        a,b=fixture();b[1]=copy.deepcopy(b[0])
        with self.assertRaises(ValueError):validate(a,b)
        a,b=fixture();a[1]['window_start_utc']=a[0]['window_start_utc']
        with self.assertRaises(ValueError):validate(a,b)

    def test_missing_sidecar_or_feature_order_not_inferred(self):
        a,b=fixture();a[0]['features']['new_feature']=1
        with self.assertRaises(ValueError):validate(a,b)
        a,b=fixture();b.pop()
        with self.assertRaises(ValueError):validate(a,b)

    def test_mean_or_total_mismatch_rejected(self):
        a,b=fixture();a[0]['features']['full_log_bytes_mean']=9
        with self.assertRaises(ValueError):validate(a,b)
        a,b=fixture();a[-1]['features']['record_count']=74;a[-1]['features']['full_log_bytes_total']=740
        with self.assertRaises(ValueError):validate(a,b)

    def test_scores_preserve_zero_and_above_one_without_threshold(self):
        self.assertEqual(aggregate([0,14])['median'],7)
        self.assertEqual(aggregate([])['minimum'],None)
        for values in ([float('inf')],[True],[-1]):
            with self.assertRaises(ValueError):aggregate(values)


if __name__=='__main__':unittest.main()
