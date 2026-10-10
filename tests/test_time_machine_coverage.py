"""T29-FIX: verified/frozen label policy, never a free UI threshold or0.5 fallback."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.asof_inference import InferenceError,read_model_contract
from src.time_machine import TimeMachineSession,context_key,make_prediction,reveal_prediction
from test_time_machine import processed,models,model_rows
from test_asof_inference import DAY,T,no_future_pair_contacts,modify_contacts,modify_observations
from test_time_machine_ui import app_setup,APP,PAGE,button


def verified_coverage(model_rows,threshold):
    """Edit only synthetic fixture time-policy evidence; never production models/weights."""
    for path in {row['evidence_path'] for row in model_rows.values()}:
        evidence=Path(path);record=json.loads(evidence.read_text())
        record['protocol']['coverage_threshold']=threshold
        evidence.write_text(json.dumps(record))
    # Deliberately untrusted descriptor/UI values must not determine the label policy.
    for row in model_rows.values():row['min_scan_coverage']=0.99


def future_scan_fraction(processed,timestamp,first,second=None):
    rates={1:first,2:first if second is None else second}
    def filter_scans(frame):
        keep=~(frame.user_id.isin(rates)&frame.timestamp.gt(timestamp)&frame.timestamp.le(timestamp+DAY))
        for user,rate in rates.items():
            bins=round(rate*288)
            keep|=frame.user_id.eq(user)&frame.timestamp.gt(timestamp)&frame.timestamp.le(timestamp+bins*300)
        return frame.loc[keep]
    modify_observations(processed,filter_scans)


@pytest.mark.parametrize('threshold',[0.25,0.5,0.75])
@pytest.mark.parametrize('fraction',[0.4,0.6])
def test_verified_frozen_coverage_matrix_with_no_future_contacts(processed,model_rows,threshold,fraction,monkeypatch):
    verified_coverage(model_rows,threshold)
    no_future_pair_contacts(processed)
    future_scan_fraction(processed,T,fraction)
    import src.time_machine as service
    actual=service.reveal_outcome;calls=[]
    monkeypatch.setattr(service,'reveal_outcome',lambda *a,**k:calls.append(k) or actual(*a,**k))
    state=TimeMachineSession();state.select('fixture')
    prediction=state.predict('fixture',lambda:make_prediction(processed,model_rows,T,1,2))
    assert calls==[]
    assert prediction['future_label_policy']['min_scan_coverage']==threshold
    assert {r['verified_min_scan_coverage'] for r in prediction['models'].values()}=={threshold}
    digest=state.freeze('fixture');frozen=state.frozen_json
    assert json.loads(frozen)['future_label_policy']['min_scan_coverage']==threshold
    assert hashlib.sha256(frozen.encode()).hexdigest()==digest
    result=state.reveal('fixture',lambda:reveal_prediction(processed,state.prediction()))
    expected='No Contact' if fraction>=threshold else 'Unknown'
    assert result['outcome']==expected
    assert calls==[{'backtest':True,'min_scan_coverage':threshold}]
    #288 discrete scan bins cannot represent0.4/0.6 exactly: nearest115/173 bins.
    assert all(value==pytest.approx(fraction,abs=1/288) for value in result['coverage'].values())
    assert state.frozen_json==frozen and state.frozen_sha256==digest


def test_both_endpoints_must_meet_frozen_policy(processed,model_rows):
    verified_coverage(model_rows,0.5);no_future_pair_contacts(processed)
    future_scan_fraction(processed,T,0.4,0.6)
    prediction=make_prediction(processed,model_rows,T,1,2)
    assert reveal_prediction(processed,prediction)['outcome']=='Unknown'


def test_mixed_verified_window_policies_fail_before_prediction_or_reveal(processed,model_rows,monkeypatch):
    verified_coverage(model_rows,0.25)
    row=model_rows[3];contract=read_model_contract(row['directory'],evidence_path=row['evidence_path'])
    manifest_path=Path(row['directory'])/'manifest.json';manifest=json.loads(manifest_path.read_text())
    manifest['metadata']['as_of_inference']={'schema_version':1,'feature_contract':'bounded_window_v1','feature_version':1,
        'dataset_id':contract.dataset_id,'history_window_days':3,'prediction_horizon_hours':24,'min_scan_coverage':0.75,
        'time_origin_seconds':contract.time_origin_seconds,'label_information_ends':contract.label_information_ends}
    manifest_path.write_text(json.dumps(manifest))
    import src.time_machine as service
    monkeypatch.setattr(service,'predict_as_of',lambda *a,**k:pytest.fail('Mixed-policy selection produced a prediction.'))
    monkeypatch.setattr(service,'reveal_outcome',lambda *a,**k:pytest.fail('Mixed policy read future evidence.'))
    with pytest.raises(InferenceError,match='label_coverage_policy_mismatch'):
        make_prediction(processed,model_rows,T,1,2)


def test_frozen_policy_tampering_or_missing_legacy_policy_cannot_read_future(processed,model_rows,monkeypatch):
    verified_coverage(model_rows,0.25)
    prediction=make_prediction(processed,model_rows,T,1,2)
    state=TimeMachineSession();state.select('key');state.predict('key',lambda:prediction);state.freeze('key')
    import src.time_machine as service
    monkeypatch.setattr(service,'reveal_outcome',lambda *a,**k:pytest.fail('Invalid frozen policy read future evidence.'))
    modified=json.loads(state.frozen_json);modified['future_label_policy']['min_scan_coverage']=0.75
    state.frozen_json=json.dumps(modified)
    with pytest.raises(InferenceError,match='integrity'):
        state.reveal('key',lambda:reveal_prediction(processed,state.prediction()))
    with pytest.raises(InferenceError,match='label_coverage_policy_mismatch'):
        reveal_prediction(processed,modified)
    legacy=copy.deepcopy(prediction);legacy.pop('future_label_policy')
    old=TimeMachineSession();old.select('old');old.predict('old',lambda:legacy);old.freeze('old')
    with pytest.raises(InferenceError,match='frozen_label_policy_missing'):
        old.reveal('old',lambda:reveal_prediction(processed,old.prediction()))


@pytest.mark.parametrize('threshold',[0.25,0.5,0.75])
@pytest.mark.parametrize('fraction',[0.4,0.6])
def test_ui_uses_verified_frozen_policy_for_reveal(app_setup,processed,model_rows,threshold,fraction):
    verified_coverage(model_rows,threshold)
    t=7*DAY+28800
    modify_contacts(processed,lambda f:f.loc[~(f.user_min.eq(1)&f.user_max.eq(2)&f.timestamp.gt(t)&f.timestamp.le(t+DAY))])
    future_scan_fraction(processed,t,fraction)
    app=AppTest.from_file(APP,default_timeout=15).run().switch_page(PAGE).run()
    button(app,'Predict').click().run();button(app,'Freeze Prediction').click().run()
    assert not app.exception
    state=app.session_state['time_machine_session']
    assert state.prediction()['future_label_policy']['min_scan_coverage']==threshold
    assert any(f'{threshold:.0%}' in m.value and '标签策略' in m.value for m in app.caption)
    button(app,'Reveal Next24h').click().run()
    expected='No Contact' if fraction>=threshold else 'Unknown'
    assert not app.exception and any(h.value=='Actual Outcome: '+expected for h in app.subheader)


def test_workflow_upgrade_clears_cached_legacy_reveal(app_setup,processed,model_rows,monkeypatch):
    import src.time_machine as service
    app=AppTest.from_file(APP,default_timeout=15).run().switch_page(PAGE).run()
    with monkeypatch.context() as patch:
        patch.setattr(service,'PREDICTION_SCHEMA_VERSION',1)
        old_key=context_key(processed,processed.directory/'contacts.parquet',model_rows,7*DAY+28800,1,2,'historical_blind_replay')
    legacy=TimeMachineSession();legacy.select(old_key);legacy.predict(old_key,lambda:{'mode':'historical_blind_replay','cases':{}})
    legacy.freeze(old_key);legacy.reveal(old_key,lambda:{'outcome':'No Contact'})
    app.session_state['time_machine_session']=legacy
    app.run()
    assert not app.exception and not app.metric
    assert not any('Actual Outcome' in h.value for h in app.subheader)
    assert button(app,'Freeze Prediction').disabled and button(app,'Reveal Next24h').disabled
