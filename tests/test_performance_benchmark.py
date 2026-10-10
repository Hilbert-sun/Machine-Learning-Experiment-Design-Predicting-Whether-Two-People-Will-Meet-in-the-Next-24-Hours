import json

import pytest

from src.performance_benchmark import atomic_json, run, worker


def test_atomic_measurement_failure_keeps_old_file(tmp_path):
    path=tmp_path/'measurement.json'
    atomic_json(path,{'value':2})
    with pytest.raises(ValueError):
        atomic_json(path,{'value':float('nan')})
    assert json.loads(path.read_text())=={'value':2}


def test_benchmark_refuses_to_overwrite_immutable_baseline(tmp_path):
    folder=tmp_path/'data/processed/performance';folder.mkdir(parents=True)
    (folder/'T32_BASELINE.json').write_text('{}')
    with pytest.raises(ValueError,match='Immutable'):
        run(tmp_path,'baseline')


def test_worker_measures_native_process_rss_not_tracemalloc(tmp_path):
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/default.yaml').write_text('paths: {}')
    output,measurement=worker({'root':str(tmp_path),'sources':{}},'public_reports')
    assert output is None
    assert measurement['seconds']>=0 and measurement['peak_rss_mb']>0
