import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.asof_inference import as_of_features, predict_as_of, InferenceError
from src.safe_cache import cache_stats
from src.window_features import snapshot_features
from src.time_machine import context_key, make_prediction, TimeMachineSession
from test_asof_inference import processed, models, append_contacts, modify_contacts, modify_observations, T, mutate_contract
from test_time_machine import model_rows


def test_frozen_feature_computation_matches_cached_multiwindow(processed):
    from src.asof_inference import as_of_candidates
    keys = as_of_candidates(processed,T,dataset_id='copenhagen')
    actual = as_of_features(processed,T,dataset_id='copenhagen')
    again = as_of_features(processed,T,dataset_id='copenhagen')
    for window in (1,3,7):
        expected=snapshot_features(processed,keys,T,window,.5).to_pandas()
        expected.attrs['history_window_days']=window
        pd.testing.assert_frame_equal(expected,actual[window],rtol=1e-12,atol=1e-12)
        pd.testing.assert_frame_equal(actual[window],again[window])
    assert cache_stats()['hits'] >= 1


def test_history_future_and_coverage_version_invalidation(processed,models):
    def predict():
        return predict_as_of(processed,models[1],T,1,2,dataset_id='copenhagen',history_window_days=1)
    before=predict();misses=cache_stats()['misses']
    append_contacts(processed,[(T,1,9),(T+1,1,9)])
    modify_observations(processed,lambda f:f.assign(scan_observed=f.scan_observed.where(f.timestamp.lt(T),False)))
    after=predict()
    assert before==after and cache_stats()['misses']>misses
    append_contacts(processed,[(T-1,1,2)])
    changed=predict()
    assert changed['historical_features']['pair_contact_count']>before['historical_features']['pair_contact_count']
    low=as_of_features(processed,T,dataset_id='copenhagen',windows=(1,),min_scan_coverage=.25)
    count=cache_stats()['misses']
    high=as_of_features(processed,T,dataset_id='copenhagen',windows=(1,),min_scan_coverage=.75)
    assert cache_stats()['misses']>count


def test_warm_cache_never_bypasses_model_time_or_weight_check(processed,models):
    args=dict(dataset_id='copenhagen',history_window_days=1)
    predict_as_of(processed,models[1],T,1,2,**args)
    mutate_contract(models[1],lambda m:m['metadata']['as_of_inference']['label_information_ends'].update(threshold_labels_end=T))
    with pytest.raises(InferenceError,match='model_information_conflict'):
        predict_as_of(processed,models[1],T,1,2,**args)
    mutate_contract(models[1],lambda m:m['metadata']['as_of_inference']['label_information_ends'].update(threshold_labels_end=1))
    (models[1]/'model.joblib').write_bytes(b'changed-weights')
    with pytest.raises(InferenceError,match='checksum'):
        predict_as_of(processed,models[1],T,1,2,**args)


def test_time_machine_source_change_during_inference_does_not_expose_result(processed,model_rows,monkeypatch):
    import src.time_machine as module
    original=module.predict_as_of
    mutated=[]
    def predict(*a,**kw):
        result=original(*a,**kw)
        if not mutated:
            append_contacts(processed,[(T-2,1,2)]);mutated.append(True)
        return result
    monkeypatch.setattr(module,'predict_as_of',predict)
    state=TimeMachineSession();state.select('one')
    from src.snapshot_manager import SnapshotChanged
    with pytest.raises(SnapshotChanged,match='source_snapshot_changed'):
        state.predict('one',lambda:make_prediction(processed,model_rows,T,1,2))
    assert state.prediction() is None and state.stage=='select'
    from src.snapshot_manager import cache_root
    assert not list((cache_root()/'objects').glob('*.json'))


def test_public_aggregate_cache_same_mtime_edits_invalidate(tmp_path):
    from src.multisource_report import load_public_results
    import os
    folder=tmp_path/'reports/multisource';folder.mkdir(parents=True)
    summary=folder/'T31_SOURCE_SUMMARY.json'
    summary.write_text(json.dumps({'run_id':'aaa','sources':[],'networks':[]}))
    (folder/'T31_FEASIBILITY.json').write_text('[]')
    (folder/'T31_RETRIEVAL_METRICS.csv').write_text('dataset_id\n')
    assert load_public_results(tmp_path)['run_id']=='aaa'
    old=summary.stat();summary.write_text(summary.read_text().replace('aaa','bbb'));os.utime(summary,ns=(old.st_atime_ns,old.st_mtime_ns))
    assert load_public_results(tmp_path)['run_id']=='bbb'


def test_valid_weight_replacement_cannot_reuse_old_model(processed,models):
    import hashlib
    import joblib
    from src.model_registry import ModelRegistry
    args=dict(dataset_id='copenhagen',history_window_days=1)
    first=predict_as_of(processed,models[1],T,1,2,**args)
    changed=ModelRegistry.load(models[1])
    changed.estimator.named_steps['classifier'].coef_ *= -1
    path=models[1]/'model.joblib';joblib.dump(changed,path,compress=3)
    manifest=models[1]/'manifest.json';record=json.loads(manifest.read_text())
    record['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();manifest.write_text(json.dumps(record))
    second=predict_as_of(processed,models[1],T,1,2,**args)
    assert second['probability'] != first['probability']


def test_model_cache_clones_and_rechecks_dependency_versions(models,monkeypatch):
    import src.readonly_models as module
    first=module.load_model(models[1]);threshold=first.threshold
    first.threshold=.98765
    assert module.load_model(models[1]).threshold==threshold
    monkeypatch.setattr(module,'package_version',lambda _: 'wrong-version')
    with pytest.raises(ValueError,match='dependencies'):
        module.load_model(models[1])
