import json
from pathlib import Path

import pandas as pd
import pytest

from src.safe_cache import SafeCache, cache_stats
from src.snapshot_manager import SnapshotChanged


def test_hits_namespace_window_coverage_model_and_version_keys(tmp_path):
    cache = SafeCache(tmp_path/'cache')
    frame = pd.DataFrame({'count': [2, 3], 'value': [float('nan'), .6]})
    calls = []
    def produce():
        calls.append(1)
        return {'features': frame.copy()}
    key = {'dataset': 'workplace2013', 'source_sha': 'old', 'window': 1, 'coverage': .25, 'model_sha': 'model1', 'timestamp': 100}
    first = cache.get(key, produce)
    second = cache.get(key, produce)
    pd.testing.assert_frame_equal(first['features'], second['features'])
    second['features'].loc[0, 'count'] = 99
    assert cache.get(key, produce)['features'].iloc[0]['count'] == 2
    assert len(calls) == 1
    for field, value in [('dataset', 'workplace2015'), ('source_sha', 'new'), ('window', 7), ('coverage', .75), ('model_sha', 'model2'), ('timestamp', 200)]:
        cache.get({**key, field: value}, produce)
    assert len(calls) == 7


@pytest.mark.parametrize('damage', ['payload', 'manifest', 'pointer', 'incomplete'])
def test_corruption_recomputes_and_pending_files_never_count(tmp_path, damage):
    cache = SafeCache(tmp_path)
    calls = []
    def produce():
        calls.append(1)
        return {'x': pd.DataFrame({'n': [1, 2]})}
    cache.get({'k': 1}, produce)
    pointer = next(tmp_path.glob('*.json'))
    bundle = tmp_path/json.loads(pointer.read_text())['version']
    if damage=='payload':
        (bundle/'0.parquet').write_bytes(b'broken')
    elif damage=='manifest':
        (bundle/'COMMITTED.json').write_text('{}')
    elif damage=='pointer':
        pointer.write_text('not JSON')
    else:
        pointer.unlink()
        (tmp_path/'.pending-crash').mkdir()
    result = cache.get({'k': 1}, produce)
    assert len(calls) == 2 and result['x'].n.tolist() == [1, 2]


def test_interrupted_publish_preserves_prior_valid_pointer(tmp_path, monkeypatch):
    from src import safe_cache
    cache = SafeCache(tmp_path)
    producer = lambda: {'x': pd.DataFrame({'n': [3]})}
    cache.get({'k': 'old'}, producer)
    pointers = {p.name: p.read_bytes() for p in tmp_path.glob('*.json')}
    monkeypatch.setattr(safe_cache.os, 'replace', lambda *a: (_ for _ in ()).throw(OSError('simulated interrupt')))
    with pytest.raises(OSError, match='interrupt'):
        cache.get({'k': 'new'}, producer)
    assert all((tmp_path/name).read_bytes() == data for name, data in pointers.items())
    assert cache.get({'k': 'old'}, producer)['x'].n.tolist() == [3]


def test_source_change_guard_does_not_retry_or_publish(tmp_path):
    cache = SafeCache(tmp_path)
    calls = []
    def producer():
        calls.append(1)
        return {'x': pd.DataFrame({'n': [1]})}
    def guard():
        raise SnapshotChanged('source_snapshot_changed')
    with pytest.raises(SnapshotChanged):
        cache.get({'k': 1}, producer, guard=guard)
    assert calls == [1] and not list(tmp_path.glob('*.json'))
