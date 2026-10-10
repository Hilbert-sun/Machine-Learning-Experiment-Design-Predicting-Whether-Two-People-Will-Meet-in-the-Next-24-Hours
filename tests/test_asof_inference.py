"""Small offline T28 fixtures: no downloads, production models, labels or eval banks."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.asof_inference import (ClockAnchor, InferenceError, as_of_candidates, as_of_features,
                                predict_as_of, read_model_contract, reveal_outcome)
from src.model_registry import ModelRegistry
from src.window_features import WINDOW_FEATURES
from src.window_models import create_window_model
from test_window_cohort import DAY, fixture_processed

T = 12*DAY + 28800


@pytest.fixture
def processed(tmp_path):
    return fixture_processed(tmp_path)


@pytest.fixture
def models(tmp_path):
    result = {}
    rng = np.random.default_rng(11)
    X = pd.DataFrame(rng.normal(size=(24,len(WINDOW_FEATURES))), columns=WINDOW_FEATURES)
    X['pair_contact_count'] = rng.integers(0,13,len(X))
    X['pair_contact_bins'] = rng.integers(0,13,len(X))
    X['recency_seconds'] = rng.uniform(0,DAY,len(X))
    X['rssi_mean'] = rng.uniform(-90,-40,len(X))
    X['rssi_max'] = rng.uniform(-90,-40,len(X))
    for name in ('participant_a_activity','participant_b_activity'):
        X[name] = rng.uniform(0,50,len(X))
    for name in ('scan_coverage_a','scan_coverage_b','historical_contact_probability'):
        X[name] = rng.uniform(0,1,len(X))
    y = (X.pair_contact_count > X.pair_contact_count.median()).astype(int)
    for days in (1,3,7):
        X.attrs['history_window_days'] = days
        model = create_window_model('logistic_regression',days=days,seed=42).fit(X,y)
        contract = {'schema_version':1,'feature_contract':'bounded_window_v1','feature_version':1,'dataset_id':'copenhagen',
                    'history_window_days':days,'prediction_horizon_hours':24,'min_scan_coverage':0.5,'time_origin_seconds':0,
                    'label_information_ends':{'training_labels_end':2*DAY,'validation_labels_end':4*DAY,'threshold_labels_end':6*DAY}}
        result[days] = ModelRegistry.save(model,tmp_path/'synthetic_models',metadata={'as_of_inference':contract,'source_kind':'synthetic_test_fixture'})
    return result


def predict(processed, models, days=1, **options):
    return predict_as_of(processed,models[days],T,1,2,dataset_id='copenhagen',history_window_days=days,**options)


def modify_contacts(processed, transform):
    path=processed.directory/'contacts.parquet';table=pq.read_table(path)
    frame=transform(table.to_pandas()).sort_values('timestamp').reset_index(drop=True)
    pq.write_table(pa.Table.from_pandas(frame,schema=table.schema,preserve_index=False),path,row_group_size=17)


def append_contacts(processed, rows):
    def append(frame):
        extra=pd.DataFrame([{'timestamp':t,'source_timestamp':t,'user_min':a,'user_max':b,'rssi':-40.0} for t,a,b in rows])
        return pd.concat([frame,extra],ignore_index=True)
    modify_contacts(processed,append)


def modify_observations(processed, transform):
    path=processed.directory/'observations.parquet';table=pq.read_table(path)
    frame=transform(table.to_pandas()).sort_values('timestamp').reset_index(drop=True)
    pq.write_table(pa.Table.from_pandas(frame,schema=table.schema,preserve_index=False),path,row_group_size=113)


def mutate_contract(path, change):
    file=path/'manifest.json';manifest=json.loads(file.read_text())
    change(manifest)
    file.write_text(json.dumps(manifest))


def test_candidates_start_inclusive_end_exclusive_and_no_future_membership(processed):
    append_contacts(processed,[(T-DAY,5,6),(T-DAY-1,7,8),(T,8,9),(T+1,9,10)])
    keys=as_of_candidates(processed,T,dataset_id='copenhagen')
    pairs=set(keys[['user_min','user_max']].itertuples(index=False,name=None))
    assert (5,6) in pairs and not ({(7,8),(8,9),(9,10)} & pairs)
    assert not keys.duplicated().any() and set(keys.dataset_id)=={'copenhagen'}
    assert set(keys)=={'dataset_id','timestamp','user_min','user_max'}


def test_future_contacts_observations_and_future_span_never_change_keys_features_probabilities(processed,models):
    before_keys=as_of_candidates(processed,T,dataset_id='copenhagen')
    before_features=as_of_features(processed,T,dataset_id='copenhagen')
    before={w:predict(processed,models,w)['probability'] for w in (1,3,7)}
    append_contacts(processed,[(T,1,9),(T+1,1,9),(T+DAY,1,2),(T+10*DAY,2,9)])
    modify_observations(processed,lambda f:f.assign(scan_observed=f.scan_observed.where(f.timestamp.lt(T),False)))
    processed.report['source_timestamp_max'] = T+100*DAY
    pd.testing.assert_frame_equal(before_keys,as_of_candidates(processed,T,dataset_id='copenhagen'))
    after=as_of_features(processed,T,dataset_id='copenhagen')
    for w in (1,3,7):
        pd.testing.assert_frame_equal(before_features[w],after[w])
        assert predict(processed,models,w)['probability']==before[w]


def test_inference_works_with_no_future_data_and_no_evaluation_files(processed,models,monkeypatch):
    expected=predict(processed,models)['probability']
    modify_contacts(processed,lambda f:f.loc[f.timestamp.lt(T)])
    modify_observations(processed,lambda f:f.loc[f.timestamp.lt(T)])
    processed.report['source_timestamp_max']=T-300
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('Evaluation/feature-bank Parquet was opened.'))
    assert predict(processed,models)['probability']==expected
    assert not any('label' in c for f in as_of_features(processed,T,dataset_id='copenhagen').values() for c in f.columns)


def test_all_data_reads_for_prediction_have_pre_t_filter(processed,models,monkeypatch):
    import src.asof_inference as inference
    import src.window_cohort as cohort
    import src.window_features as features
    actual=cohort.parquet_frames
    calls=[]
    def guard(path,columns,expression=None):
        assert Path(path).name in {'contacts.parquet','observations.parquet'}
        assert expression is not None and f'timestamp < {T}' in str(expression)
        calls.append(Path(path).name)
        yield from actual(path,columns,expression)
    for module in (inference,cohort,features):monkeypatch.setattr(module,'parquet_frames',guard)
    predict(processed,models,7)
    assert 'contacts.parquet' in calls and 'observations.parquet' in calls


def test_past_changes_can_add_candidates_and_change_only_relevant_budgets(processed,models):
    old=as_of_features(processed,T,dataset_id='copenhagen')
    original_probability=predict(processed,models)['probability']
    append_contacts(processed,[(T-5*DAY,1,2)])
    changed=as_of_features(processed,T,dataset_id='copenhagen')
    pd.testing.assert_frame_equal(old[1],changed[1]);pd.testing.assert_frame_equal(old[3],changed[3])
    assert changed[7].pair_contact_count.iloc[0]>old[7].pair_contact_count.iloc[0]
    append_contacts(processed,[(T-100,1,9),(T-100,1,2)])
    assert predict(processed,models)['probability']!=original_probability
    assert as_of_candidates(processed,T,dataset_id='copenhagen').user_max.eq(9).any()
    assert predict_as_of(processed,models[1],T,1,9,dataset_id='copenhagen',history_window_days=1)['probability']>=0


@pytest.mark.parametrize('field',['training_labels_end','validation_labels_end','threshold_labels_end','calibration_labels_end'])
@pytest.mark.parametrize('offset',[0,1])
def test_every_label_information_deadline_at_or_after_t_rejects(processed,models,field,offset):
    mutate_contract(models[1],lambda m:m['metadata']['as_of_inference']['label_information_ends'].update({field:T+offset}))
    with pytest.raises(InferenceError,match='model_information_conflict'):predict(processed,models)


def test_missing_selection_provenance_and_calibration_deadline_reject(processed,models):
    mutate_contract(models[1],lambda m:m['metadata']['as_of_inference']['label_information_ends'].pop('threshold_labels_end'))
    with pytest.raises(InferenceError,match='model_information_unknown'):predict(processed,models)
    mutate_contract(models[3],lambda m:m.update(calibration_method='sigmoid'))
    with pytest.raises(InferenceError,match='Calibration label deadline'):predict(processed,models,3)


def test_wrong_dataset_window_origin_and_artifact_reject(processed,models):
    with pytest.raises(InferenceError,match='window_contract'):
        predict_as_of(processed,models[1],T,1,2,dataset_id='copenhagen',history_window_days=7)
    with pytest.raises(InferenceError,match='namespace'):
        predict_as_of(processed,models[1],T,1,2,dataset_id='highschool2013',history_window_days=1)
    mutate_contract(models[1],lambda m:m['metadata']['as_of_inference'].update(dataset_id='highschool2013'))
    with pytest.raises(InferenceError,match='window_contract'):predict(processed,models)
    changed=replace(processed,report={**processed.report,'time_origin_seconds':300})
    with pytest.raises(InferenceError,match='origins'):predict(changed,models,3)
    (models[7]/'model.joblib').write_bytes(b'tampered')
    with pytest.raises(InferenceError,match='checksum'):predict(processed,models,7)


def test_unknown_or_old_only_pair_invalid_keys_and_missing_scans(processed,models):
    for a,b in [(1,9),(40,50)]:
        with pytest.raises(InferenceError,match='unknown_historical_pair'):
            predict_as_of(processed,models[1],T,a,b,dataset_id='copenhagen',history_window_days=1)
    for a,b in [(-1,2),(1,1)]:
        with pytest.raises(InferenceError):predict_as_of(processed,models[1],T,a,b,dataset_id='copenhagen',history_window_days=1)
    append_contacts(processed,[(T-2*DAY,1,9)])
    with pytest.raises(InferenceError,match='unknown_historical_pair'):
        predict_as_of(processed,models[1],T,1,9,dataset_id='copenhagen',history_window_days=1)
    processed.report['scan_coverage_available']=False
    with pytest.raises(InferenceError,match='scan_evidence_missing'):predict(processed,models)
    assert as_of_features(processed,T,dataset_id='copenhagen')[1].scan_coverage_a.isna().all()
    processed.report['scan_coverage_available']=True
    modify_observations(processed,lambda f:f.loc[~(f.user_id.eq(2)&f.timestamp.lt(T))])
    with pytest.raises(InferenceError,match='scan_evidence_missing'):predict(processed,models)


def test_missing_observation_file_and_incomplete_past_fail(processed,models):
    changed=replace(processed,report={**processed.report,'source_timestamp_min':T-DAY+1})
    with pytest.raises(InferenceError,match='insufficient_past_history'):predict(changed,models)
    (processed.directory/'observations.parquet').unlink()
    with pytest.raises(InferenceError,match='evidence_missing'):predict(processed,models)


def test_prospective_requires_verified_current_clock_and_both_fresh_devices(processed,models):
    now=datetime(2026,10,10,tzinfo=timezone.utc)
    with pytest.raises(InferenceError,match='verified_clock_required'):
        predict(processed,models,mode='prospective_inference',now_utc=now)
    old=ClockAnchor(datetime(2013,1,1,tzinfo=timezone.utc),'known archival study origin')
    with pytest.raises(InferenceError,match='stale_or_noncurrent'):
        predict(processed,models,mode='prospective_inference',clock_anchor=old,now_utc=now)
    anchor=ClockAnchor(now-timedelta(seconds=T),'synthetic fresh-feed clock fixture')
    result=predict(processed,models,mode='prospective_inference',clock_anchor=anchor,now_utc=now)
    assert result['mode']=='prospective_inference' and 'actual_outcome' not in result
    with pytest.raises(InferenceError,match='archival-scale'):
        predict(processed,models,mode='prospective_inference',clock_anchor=old,now_utc=now,max_age_seconds=20*365*DAY)
    modify_observations(processed,lambda f:f.loc[~(f.user_id.eq(2)&f.timestamp.ge(T-3600)&f.timestamp.lt(T))])
    with pytest.raises(InferenceError,match='recent_observations_missing'):
        predict(processed,models,mode='prospective_inference',clock_anchor=anchor,now_utc=now)


def test_outcome_requires_explicit_backtest_before_any_read(processed,monkeypatch):
    import src.asof_inference as module
    monkeypatch.setattr(module,'parquet_frames',lambda *a,**k:pytest.fail('Reveal read data without backtest authorization.'))
    with pytest.raises(InferenceError,match='explicit_backtest_required'):reveal_outcome(processed,T,1,2)


def no_future_pair_contacts(processed):
    modify_contacts(processed,lambda f:f.loc[~(f.user_min.eq(1)&f.user_max.eq(2)&f.timestamp.gt(T)&f.timestamp.le(T+DAY))])


def test_reveal_boundaries_observed_positive_and_reliable_absence(processed):
    no_future_pair_contacts(processed)
    append_contacts(processed,[(T,1,2)])
    assert reveal_outcome(processed,T,1,2,backtest=True)['outcome']=='No Contact'
    append_contacts(processed,[(T+DAY,1,2)])
    processed.report['scan_coverage_available']=False
    assert reveal_outcome(processed,T,2,1,backtest=True)['outcome']=='Contact'


def test_unreliable_absence_incomplete_horizon_or_duplicate_scans_stay_unknown(processed):
    no_future_pair_contacts(processed)
    partial=replace(processed,report={**processed.report,'source_timestamp_max':T+100})
    assert reveal_outcome(partial,T,1,2,backtest=True)['reason']=='future_window_incomplete'
    processed.report['scan_coverage_available']=False
    assert reveal_outcome(processed,T,1,2,backtest=True)['outcome']=='Unknown'
    processed.report['scan_coverage_available']=True
    def duplicate_one_bin(f):
        past=f.loc[f.timestamp.le(T)|f.timestamp.gt(T+DAY)]
        sample=f.loc[f.timestamp.eq(T+300)&f.user_id.isin([1,2])]
        return pd.concat([past]+[sample]*300,ignore_index=True)
    modify_observations(processed,duplicate_one_bin)
    result=reveal_outcome(processed,T,1,2,backtest=True)
    assert result['outcome']=='Unknown' and max(result['coverage'].values())<0.01


def legacy_evidence(tmp_path,model_path,*,window=1):
    file=model_path/'manifest.json';manifest=json.loads(file.read_text())
    manifest['metadata']={'run_id':'synthetic_fixture','feature_contract':'bounded_window_v1'}
    file.write_text(json.dumps(manifest))
    record={'run_id':'synthetic_fixture','dataset_id':'copenhagen','source_kind':'synthetic_test_fixture','calibration_method':None,
            'protocol':{'coverage_threshold':0.5,'future_horizon_hours':24},'model_artifacts':{str(window):{'logistic_regression':str(model_path.relative_to(tmp_path))}},
            'validation_and_runtime':{str(window):{'logistic_regression':{'parameters':manifest['parameters'],'threshold':manifest['threshold'],
             'feature_columns':manifest['feature_columns'],'training_prediction_times':[DAY,2*DAY],
             'validation_prediction_times':[4*DAY,5*DAY]}}},
            'feature_paths':{'1':'FORBIDDEN_EVAL_BANK.parquet'},'prediction_paths':{'1':'FORBIDDEN_TARGETS.parquet'}}
    path=tmp_path/'reports/window_study/synthetic_fixture/T21_RESULTS.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record))
    return path,record


def test_legacy_metadata_bridge_binds_model_times_without_eval_io_or_cwd_assumptions(processed,models,tmp_path,monkeypatch):
    evidence,record=legacy_evidence(tmp_path,models[1])
    elsewhere=tmp_path/'elsewhere';elsewhere.mkdir();monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('Legacy eval bank or labels opened.'))
    contract=read_model_contract(models[1],evidence_path=evidence)
    assert contract.label_information_ends=={'training_labels_end':3*DAY,'validation_labels_end':6*DAY,'threshold_labels_end':6*DAY}
    assert predict(processed,models,evidence_path=evidence)['probability']>=0
    record['validation_and_runtime']['1']['logistic_regression']['validation_prediction_times']=[T]
    evidence.write_text(json.dumps(record))
    with pytest.raises(InferenceError,match='model_information_conflict'):predict(processed,models,evidence_path=evidence)


def test_legacy_missing_or_mismatched_training_and_threshold_evidence_rejects(processed,models,tmp_path):
    evidence,record=legacy_evidence(tmp_path,models[1])
    with pytest.raises(InferenceError,match='model_information_unknown'):predict(processed,models)
    record['validation_and_runtime']['1']['logistic_regression']['threshold']=0.123
    evidence.write_text(json.dumps(record))
    with pytest.raises(InferenceError,match='threshold'):predict(processed,models,evidence_path=evidence)
    record['validation_and_runtime']['1']['logistic_regression'].pop('training_prediction_times')
    record['validation_and_runtime']['1']['logistic_regression']['threshold']=0.5
    evidence.write_text(json.dumps(record))
    with pytest.raises(InferenceError,match='model_information_unknown'):predict(processed,models,evidence_path=evidence)


def test_unverified_horizon_and_unbounded_test_selection_never_guess_deadlines(processed,models,tmp_path):
    mutate_contract(models[1],lambda m:m['metadata']['as_of_inference'].update(prediction_horizon_hours=48))
    with pytest.raises(InferenceError,match='24h target'):predict(processed,models)
    evidence,record=legacy_evidence(tmp_path,models[3],window=3)
    record['test_used_for_selection']=True
    evidence.write_text(json.dumps(record))
    with pytest.raises(InferenceError,match='test-informed'):predict(processed,models,3,evidence_path=evidence)


def test_prospective_clock_uses_absolute_elapsed_utc_seconds(processed,models):
    now=datetime(2026,10,10,tzinfo=timezone.utc)
    origin=(now-timedelta(seconds=T)).astimezone(timezone(timedelta(hours=8)))
    anchor=ClockAnchor(origin,'synthetic verified timezone-aware fixture')
    assert predict(processed,models,mode='prospective_inference',clock_anchor=anchor,now_utc=now)['probability']>=0
