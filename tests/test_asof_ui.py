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
