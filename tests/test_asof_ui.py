"""Independent Case Explorer without offline Run Study or evaluation-cohort reads."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.asof_ui import available_models
from test_asof_inference import processed,models,legacy_evidence,T


def test_case_explorer_accessible_without_run_study_and_no_live_archive_claim(tmp_path,monkeypatch,processed,models):
    evidence,record=legacy_evidence(tmp_path,models[1])
    config={'paths':{n:str(tmp_path/n) for n in ('reports','models','features','processed','raw_copenhagen','raw_sociopatterns')}}
    monkeypatch.setattr('yaml.safe_load',lambda _:config)
    import src.asof_ui as view
    monkeypatch.setattr(view,'source_path',lambda *a:processed.directory/'contacts.parquet')
    monkeypatch.setattr(view,'cached_dataset',lambda *a:processed)
    actual_candidates=view.as_of_candidates
    seen=[]
    def record_candidates(*args,**kwargs):
        result=actual_candidates(*args,**kwargs);seen.append(result.copy());return result
    monkeypatch.setattr(view,'as_of_candidates',record_candidates)
    monkeypatch.setattr('src.window_ui.case_keys',lambda *a:pytest.fail('Filtered evaluation keys were used.'))
    monkeypatch.setattr('src.window_ui.predict_case',lambda *a,**k:pytest.fail('Legacy evaluation-bank inference was used.'))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run().switch_page('pages/8_History_Window_Study.py').run()
    assert not app.exception and seen and not app.metric
    assert any('独立' in m.value for m in app.info)
    next(b for b in app.button if b.label=='Compare Case').click().run()
    assert not app.exception and len(app.metric)==1
    assert not any('Actual Outcome' in str(m.value) for m in app.markdown)
    next(c for c in app.checkbox if c.label.startswith('历史回测')).check().run()
    next(b for b in app.button if b.label=='Compare Case').click().run()
    assert not app.exception and any('Actual Outcome' in str(m.value) for m in app.markdown)
    next(r for r in app.radio if r.label=='Inference Mode').set_value('prospective_inference').run()
    next(b for b in app.button if b.label=='Compare Case').click().run()
    assert not app.exception and not app.metric
    assert any('verified_clock_required' in m.value for m in app.error)


def test_model_catalog_reads_only_model_time_metadata(tmp_path,models,monkeypatch):
    legacy_evidence(tmp_path,models[1])
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('Catalog read cohort/bank rows.'))
    rows=available_models(tmp_path,{'paths':{'reports':'reports'}},'Copenhagen')
    assert len(rows)==1 and rows[0]['deadline']==6*86400 and rows[0]['window']==1
    assert available_models(tmp_path,{'paths':{'reports':'reports'}},'SocioPatterns')==[]


# T34 acceptance regression: reuse T29's verified policy/snapshot service.
from test_time_machine import model_rows
from test_time_machine_coverage import verified_coverage, future_scan_fraction
from test_asof_inference import DAY, modify_contacts, mutate_contract


@pytest.fixture
def policy_case_ui(tmp_path, monkeypatch, processed, model_rows):
    config={'paths':{n:str(tmp_path/n) for n in ('reports','models','features','processed','raw_copenhagen','raw_sociopatterns')}}
    monkeypatch.setattr('yaml.safe_load',lambda _:config)
    import src.asof_ui as view
    monkeypatch.setattr(view,'source_path',lambda *a:processed.directory/'contacts.parquet')
    monkeypatch.setattr(view,'cached_dataset',lambda *a:processed)
    monkeypatch.setattr(view,'available_models',lambda *a:list(model_rows.values()))
    return view


def case_app():
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run().switch_page('pages/8_History_Window_Study.py').run()


@pytest.mark.parametrize('threshold',[0.25,0.5,0.75])
@pytest.mark.parametrize('fraction',[0.4,0.6])
def test_case_reveal_uses_verified_model_policy_only(policy_case_ui,processed,model_rows,threshold,fraction,monkeypatch):
    verified_coverage(model_rows,threshold)  # descriptors deliberately claim0.99
    timestamp=7*DAY+28800
    modify_contacts(processed,lambda f:f.loc[~(f.user_min.eq(1)&f.user_max.eq(2)&f.timestamp.gt(timestamp)&f.timestamp.le(timestamp+DAY))])
    future_scan_fraction(processed,timestamp,fraction)
    import src.time_machine as service
    actual=service.reveal_outcome;calls=[]
    monkeypatch.setattr(service,'reveal_outcome',lambda *a,**k:calls.append(k) or actual(*a,**k))
    app=case_app()
    next(b for b in app.button if b.label=='Compare Case').click().run()
    assert not app.exception and not app.error and len(app.metric)==3 and not calls
    before=[m.value for m in app.metric]
    next(c for c in app.checkbox if c.label.startswith('历史回测')).check().run()
    next(b for b in app.button if b.label=='Compare Case').click().run()
    assert not app.exception and not app.error and [m.value for m in app.metric]==before
    expected='No Contact' if fraction>=threshold else 'Unknown'
    assert any('Actual Outcome: '+expected in str(m.value) for m in app.markdown)
    assert calls==[{'backtest':True,'min_scan_coverage':threshold}]


def test_case_mixed_verified_policies_reject_before_prediction_or_future_read(policy_case_ui,model_rows,monkeypatch):
    verified_coverage(model_rows,0.25)
    from src.asof_inference import read_model_contract
    row=model_rows[3]
    contract=read_model_contract(row['directory'],evidence_path=row['evidence_path'])
    mutate_contract(Path(row['directory']),lambda m:m['metadata'].update(as_of_inference={
        'schema_version':1,'feature_contract':'bounded_window_v1','feature_version':1,'dataset_id':contract.dataset_id,
        'history_window_days':3,'prediction_horizon_hours':24,'min_scan_coverage':0.75,
        'time_origin_seconds':contract.time_origin_seconds,'label_information_ends':contract.label_information_ends}))
    import src.time_machine as service
    monkeypatch.setattr(service,'predict_as_of',lambda *a,**k:pytest.fail('Mixed policy produced a prediction.'))
    monkeypatch.setattr(service,'reveal_outcome',lambda *a,**k:pytest.fail('Mixed policy read future evidence.'))
    app=case_app()
    next(c for c in app.checkbox if c.label.startswith('历史回测')).check().run()
    next(b for b in app.button if b.label=='Compare Case').click().run()
    assert not app.exception and not app.metric
    assert any('label_coverage_policy_mismatch' in m.value for m in app.error)
