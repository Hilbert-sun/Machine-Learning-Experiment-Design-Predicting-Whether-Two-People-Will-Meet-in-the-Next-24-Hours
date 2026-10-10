"""T29 offline lifecycle/invalidation tests using small T28 model/source fixtures."""

import copy
import json
from pathlib import Path

import pytest

from src.asof_inference import InferenceError
from src.asof_ui import available_models
from src.time_machine import TimeMachineSession,context_key,make_prediction,reveal_prediction
from test_asof_inference import processed,models,legacy_evidence,append_contacts,modify_observations,T


@pytest.fixture
def model_rows(tmp_path,models):
    combined=None
    for window,path in models.items():
        evidence,record=legacy_evidence(tmp_path,path,window=window)
        if combined is None:combined=record
        else:
            combined['model_artifacts'].update(record['model_artifacts'])
            combined['validation_and_runtime'].update(record['validation_and_runtime'])
    evidence.write_text(json.dumps(combined))
    rows=available_models(tmp_path,{'paths':{'reports':'reports'}},'Copenhagen')
    return {row['window']:row for row in rows}


def test_lifecycle_requires_predict_and_freeze_and_frozen_payload_is_immutable():
    state=TimeMachineSession();state.select('selection')
    reads=[]
    with pytest.raises(InferenceError,match='prediction_required'):state.freeze('selection')
    with pytest.raises(InferenceError,match='freeze_required'):state.reveal('selection',lambda:reads.append('future'))
    payload={'cases':{'1':{'probability':0.42,'historical_features':{'unknown':float('nan')}}}}
    state.predict('selection',lambda:payload)
    assert not reads and state.stage=='predicted'
    with pytest.raises(InferenceError,match='freeze_required'):state.reveal('selection',lambda:reads.append('future'))
    digest=state.freeze('selection');frozen=state.frozen_json
    payload['cases']['1']['probability']=0.99
    view=state.prediction();view['cases']['1']['probability']=0.88
    assert state.prediction()['cases']['1']['probability']==0.42
    assert state.prediction()['cases']['1']['historical_features']['unknown'] is None
    state.reveal('selection',lambda:reads.append('future') or {'outcome':'Unknown','reason':'low_scan_coverage'})
    state.reveal('selection',lambda:pytest.fail('A revealed snapshot was queried twice.'))
    assert reads==['future'] and state.frozen_sha256==digest and state.frozen_json==frozen
    state.select('changed');assert state.stage=='select' and state.prediction() is None and state.outcome() is None


def test_selection_change_during_action_and_frozen_integrity_are_rejected():
    state=TimeMachineSession();state.select('one')
    with pytest.raises(InferenceError,match='selection_changed'):
        state.predict('one',lambda:state.select('two') or {'value':1})
    state.predict('two',lambda:{'value':1});state.freeze('two')
    state.frozen_json='{"modified":true}'
    with pytest.raises(InferenceError,match='integrity'):state.reveal('two',lambda:pytest.fail('Corrupt freeze read future evidence.'))


def test_context_covers_date_pair_mode_windows_models_and_processed_version(processed,model_rows):
    source=processed.directory/'contacts.parquet'
    baseline=context_key(processed,source,model_rows,T,1,2,'historical_blind_replay')
    for t,a,b,mode,rows in [(T+86400,1,2,'historical_blind_replay',model_rows),(T,2,3,'historical_blind_replay',model_rows),
                         (T,1,2,'prospective_inference',model_rows),(T,1,2,'historical_blind_replay',{1:model_rows[1]})]:
        assert context_key(processed,source,rows,t,a,b,mode)!=baseline
    changed=copy.deepcopy(model_rows);changed[1]['run_id']='changed-model'
    assert context_key(processed,source,changed,T,1,2,'historical_blind_replay')!=baseline
    modify_observations(processed,lambda frame:frame.loc[frame.timestamp.lt(T)])
    assert context_key(processed,source,model_rows,T,1,2,'historical_blind_replay')!=baseline


def test_future_edits_invalidate_active_version_without_changing_reprediction_or_old_freeze(processed,model_rows):
    source=processed.directory/'contacts.parquet'
    state=TimeMachineSession();key=context_key(processed,source,model_rows,T,1,2,'historical_blind_replay');state.select(key)
    before=state.predict(key,lambda:make_prediction(processed,model_rows,T,1,2))
    digest=state.freeze(key);old_frozen=state.frozen_json
    append_contacts(processed,[(T,1,9),(T+1,1,9),(T+86400,1,2)])
    modify_observations(processed,lambda f:f.assign(scan_observed=f.scan_observed.where(f.timestamp.lt(T),False)))
    updated=context_key(processed,source,model_rows,T,1,2,'historical_blind_replay')
    assert updated!=key and state.frozen_json==old_frozen and state.frozen_sha256==digest
    state.select(updated)
    assert state.prediction() is None and state.outcome() is None
    with pytest.raises(InferenceError,match='freeze_required'):state.reveal(updated,lambda:pytest.fail('Stale outcome read.'))
    after=state.predict(updated,lambda:make_prediction(processed,model_rows,T,1,2))
    assert before['cases']==after['cases']
    assert before['selection_version']!=after['selection_version']


def test_prediction_never_reveals_and_absent_future_scans_reveal_unknown(processed,model_rows,monkeypatch):
    import src.time_machine as module
    original=module.reveal_outcome;calls=[]
    monkeypatch.setattr(module,'reveal_outcome',lambda *a,**k:pytest.fail('Predict read future outcomes.'))
    prediction=make_prediction(processed,model_rows,T,1,2)
    assert len(prediction['cases'])==3 and all('label_24h' not in c for c in prediction['cases'].values())
    from test_asof_inference import no_future_pair_contacts
    no_future_pair_contacts(processed)
    modify_observations(processed,lambda f:f.loc[f.timestamp.le(T)])
    monkeypatch.setattr(module,'reveal_outcome',lambda *a,**k:calls.append(k.get('backtest')) or original(*a,**k))
    state=TimeMachineSession();state.select('current');state.predict('current',lambda:prediction);state.freeze('current')
    outcome=state.reveal('current',lambda:reveal_prediction(processed,state.prediction()))
    assert calls==[True] and outcome['outcome']=='Unknown' and outcome['reason']=='low_scan_coverage'
