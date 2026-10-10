"""Streamlit T29 UI test: no offline study, no future read until separate frozen Reveal."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from test_time_machine import processed,models,model_rows
from test_asof_inference import no_future_pair_contacts,modify_observations

APP=str(Path(__file__).resolve().parents[1]/'app.py')
PAGE='pages/10_Time_Machine.py'


@pytest.fixture
def app_setup(tmp_path,monkeypatch,processed,model_rows):
    config={'paths':{n:str(tmp_path/n) for n in ('reports','models','features','processed','raw_copenhagen','raw_sociopatterns')}}
    monkeypatch.setattr('yaml.safe_load',lambda _:config)
    import src.time_machine_ui as view
    monkeypatch.setattr(view,'source_path',lambda *a:processed.directory/'contacts.parquet')
    monkeypatch.setattr(view,'cached_dataset',lambda *a:processed)
    monkeypatch.setattr(view,'available_models',lambda *a:list(model_rows.values()))
    monkeypatch.setattr('src.window_ui.case_keys',lambda *a:pytest.fail('Old future-filtered candidates used.'))
    monkeypatch.setattr('src.window_ui.predict_case',lambda *a,**k:pytest.fail('Old evaluation bank used.'))
    monkeypatch.setattr('src.window_ui.run_study',lambda *a,**k:pytest.fail('Offline study required.'))
    return config


def button(app,label):return next(b for b in app.button if b.label==label)


def test_predict_freeze_reveal_order_history_display_and_unknown(app_setup,processed,monkeypatch):
    no_future_pair_contacts(processed)
    # Default UI time follows the6-day model deadline: Study Day8,08:00.
    t=7*86400+28800
    from test_asof_inference import modify_contacts
    modify_contacts(processed,lambda f:f.loc[~(f.user_min.eq(1)&f.user_max.eq(2)&f.timestamp.gt(t)&f.timestamp.le(t+86400))])
    modify_observations(processed,lambda f:f.loc[f.timestamp.le(t)])
    import src.time_machine as service
    original=service.reveal_outcome;calls=[]
    monkeypatch.setattr(service,'reveal_outcome',lambda *a,**k:calls.append(k.get('backtest')) or original(*a,**k))
    app=AppTest.from_file(APP,default_timeout=15).run().switch_page(PAGE).run()
    assert not app.exception and not app.metric
    assert button(app,'Freeze Prediction').disabled and button(app,'Reveal Next24h').disabled
    button(app,'Predict').click().run()
    assert not app.exception and len(app.metric)==3 and not calls
    assert not button(app,'Freeze Prediction').disabled and button(app,'Reveal Next24h').disabled
    assert any('label_information_deadline_seconds' in table.value for table in app.dataframe)
    button(app,'Freeze Prediction').click().run()
    assert not app.exception and not calls and app.success and not button(app,'Reveal Next24h').disabled
    before=[m.value for m in app.metric]
    button(app,'Reveal Next24h').click().run()
    assert not app.exception and calls==[True] and before==[m.value for m in app.metric]
    assert any('Unknown' in h.value for h in app.subheader)
    assert any('覆盖不足' in m.value for m in app.markdown)
    next(n for n in app.number_input if n.label=='Prediction Study Day').set_value(9).run()
    assert not app.exception and not app.metric and button(app,'Reveal Next24h').disabled
    assert not any('Actual Outcome:' in h.value for h in app.subheader)


def test_pair_window_model_version_and_data_edits_clear_active_outputs(app_setup,processed,model_rows):
    app=AppTest.from_file(APP,default_timeout=15).run().switch_page(PAGE).run()
    def frozen():
        button(app,'Predict').click().run();button(app,'Freeze Prediction').click().run()
        assert app.metric and app.success and not app.exception
    frozen()
    next(s for s in app.selectbox if s.label=='Anonymous Person A').select(2).run()
    assert not app.metric and button(app,'Reveal Next24h').disabled
    frozen()
    next(s for s in app.multiselect if s.label=='History Windows').set_value([1]).run()
    assert not app.metric and button(app,'Reveal Next24h').disabled
    frozen()
    model_rows[1]['run_id']='new-version'
    app.run()
    assert not app.metric and button(app,'Reveal Next24h').disabled
    frozen()
    # A file replacement is a new opaque version even if the as-of prefix is identical.
    modify_observations(processed,lambda f:f.copy())
    app.run()
    assert not app.metric and button(app,'Reveal Next24h').disabled


def test_static_archive_realtime_block_and_dataset_switch(app_setup):
    app=AppTest.from_file(APP,default_timeout=15).run().switch_page(PAGE).run()
    next(r for r in app.radio if r.label=='Time Machine Mode').set_value('prospective_inference').run()
    button(app,'Predict').click().run()
    assert not app.exception and not app.metric and button(app,'Freeze Prediction').disabled
    assert any('verified_clock_required' in m.value for m in app.error)
    assert button(app,'Reveal Next24h').disabled
    next(s for s in app.selectbox if s.label=='Time Machine Dataset').select('SocioPatterns Workplace2015').run()
    assert not app.exception and not app.metric
    assert any('尚无' in m.value for m in app.info)


@pytest.mark.parametrize('expected',['Contact','No Contact'])
def test_reveal_displays_observed_or_adequately_covered_outcome(app_setup,processed,expected):
    if expected=='No Contact':
        from test_asof_inference import modify_contacts
        t=7*86400+28800
        modify_contacts(processed,lambda f:f.loc[~(f.user_min.eq(1)&f.user_max.eq(2)&f.timestamp.gt(t)&f.timestamp.le(t+86400))])
    app=AppTest.from_file(APP,default_timeout=15).run().switch_page(PAGE).run()
    button(app,'Predict').click().run();button(app,'Freeze Prediction').click().run();button(app,'Reveal Next24h').click().run()
    assert not app.exception and any(h.value=='Actual Outcome: '+expected for h in app.subheader)
    assert any('实际记录' in m.value or '窗口完整' in m.value for m in app.markdown)
