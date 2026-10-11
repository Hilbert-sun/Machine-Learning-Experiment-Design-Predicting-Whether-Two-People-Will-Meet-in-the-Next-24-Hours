"""No private data/model needed; server dialog tests do not impersonate browser JS."""
import ast
from pathlib import Path
import subprocess

import pytest
from streamlit.testing.v1 import AppTest

from src.chance_encounter import OPTIONS
from src.ui import PAGES

ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'pages/12_Chance_Encounter.py'
VALID={'relationship':'friend','distance':'walkable','frequency':'three_five','recency':'week','area':'sometimes','timing':'sometimes','arrangement':'no'}


@pytest.fixture(autouse=True)
def isolate_app_from_private_research(monkeypatch,tmp_path):
    import yaml
    config=yaml.safe_load((ROOT/'configs/default.yaml').read_text())
    config['paths']={name:str(tmp_path/name) for name in config['paths']}
    monkeypatch.setattr(yaml,'safe_load',lambda _:config)


def fill(app,values):
    for field,value in values.items():
        app.selectbox(key='chance_input_'+field).select(value)
    next(b for b in app.button if b.label=='计算趣味偶遇指数').click().run()
    assert not app.exception
    return app


def test_standalone_page_never_opens_research_artifacts(monkeypatch):
    import pandas as pd
    from src.model_registry import ModelRegistry
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('Play read a research dataset.'))
    monkeypatch.setattr(ModelRegistry,'load',lambda *a,**k:pytest.fail('Play loaded a research model.'))
    app=AppTest.from_file(str(PAGE)).run()
    assert not app.exception and len(app.selectbox)==7 and not app.metric
    fill(app,VALID)
    assert app.metric[0].value=='66 / 100'
    assert len([s for s in app.subheader if s.value in {'历史偶遇','距离因素','活动区域','时间规律','最近一次偶遇'}])==5
    assert not app.selectbox


def test_edit_recomputes_and_reset_clears_only_play_state():
    app=AppTest.from_file(str(PAGE)).run()
    app.session_state['_welcome_acknowledged']=True
    app.session_state['selected_dataset']='Copenhagen'
    fill(app,VALID)
    next(b for b in app.button if b.label=='修改信息').click().run()
    assert not app.metric and app.selectbox(key='chance_input_distance').value=='walkable'
    fill(app,{'distance':'same_area'})
    assert app.metric[0].value=='71 / 100'
    next(b for b in app.button if b.label=='重新开始').click().run()
    assert not app.exception and not app.metric
    assert all(s.value is None for s in app.selectbox)
    assert app.session_state['_welcome_acknowledged'] is True
    assert app.session_state['selected_dataset']=='Copenhagen'


@pytest.mark.parametrize('changes,status',[
    ({'arrangement':'yes'},'out_of_scope'),({'arrangement':'unknown'},'needs_confirmation'),
    ({'frequency':'six_plus','recency':'older'},'inconsistent'),
    ({'distance':'unknown','recency':'unknown','area':'unknown'},'insufficient'),
])
def test_no_score_for_excluded_unconfirmed_conflicting_or_sparse_input(changes,status):
    app=fill(AppTest.from_file(str(PAGE)).run(),{**VALID,**changes})
    assert not app.metric and app.info
    assert app.session_state['_chance_result'].status==status


def test_unknown_keywords_not_fabricated():
    app=fill(AppTest.from_file(str(PAGE)).run(),{**VALID,'distance':'unknown','recency':'unknown'})
    names={s.value for s in app.subheader}
    assert not names&{'距离因素','最近一次偶遇'}
    assert {'历史偶遇','活动区域','时间规律'}<=names
    assert app.metric[0].value=='60 / 100'


def test_original_router_preserved_and_play_registered():
    code=subprocess.check_output(['git','-C',str(ROOT),'show','13192b741f5f81dae9af3563ad27e81767072d57:src/ui.py'],text=True)
    tree=ast.parse(code)
    original=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PAGES' for t in n.targets))
    assert PAGES[:-1]==original and len(original)==12 and len(PAGES)==13
    assert PAGES[-1][0]=='pages/12_Chance_Encounter.py'


def test_native_welcome_confirm_and_navigation_once(monkeypatch,tmp_path):
    import yaml
    import src.welcome as welcome
    config=yaml.safe_load((ROOT/'configs/default.yaml').read_text())
    config['paths']={name:str(tmp_path/name) for name in config['paths']}
    monkeypatch.setattr(yaml,'safe_load',lambda _:config)
    # Explicitly test the Python dialog gate with an unacknowledged browser response.
    monkeypatch.setattr(welcome,'browser_acknowledgement',lambda confirmed:confirmed)
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not app.exception
    assert any(b.label=='我知道了，开始探索' for b in app.button)
    next(b for b in app.button if b.label=='我知道了，开始探索').click().run()
    assert not app.exception and not any(b.label=='我知道了，开始探索' for b in app.button)
    app.switch_page('pages/12_Chance_Encounter.py').run()
    assert not app.exception and len(app.selectbox)==7
    assert not any(b.label=='我知道了，开始探索' for b in app.button)
    app.switch_page('pages/7_Data_Sources.py').run()
    assert not app.exception and not any(b.label=='我知道了，开始探索' for b in app.button)


def test_browser_restore_and_hydration_are_distinct(monkeypatch):
    import src.welcome as welcome
    monkeypatch.setattr(welcome,'browser_acknowledgement',lambda confirmed:True)
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not app.exception and app.session_state['_welcome_acknowledged'] is True
    assert not any(b.label=='我知道了，开始探索' for b in app.button)


def test_pending_browser_hydration_is_not_claimed_as_acknowledgement(monkeypatch):
    import src.welcome as welcome
    monkeypatch.setattr(welcome,'browser_acknowledgement',lambda confirmed:None)
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not app.exception
    assert not any(b.label=='我知道了，开始探索' for b in app.button)
    with pytest.raises(KeyError):
        _=app.session_state['_welcome_acknowledged']


def test_storage_bridge_transmits_only_acknowledgement(monkeypatch):
    from types import SimpleNamespace
    import src.welcome as welcome
    calls=[]
    def render(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(acknowledged=True)
    monkeypatch.setattr(welcome,'component',lambda name,**kwargs:render)
    assert welcome.browser_acknowledgement(True) is True
    assert calls[0]['data']=={'confirmed':True}
    assert set(calls[0]['default'])=={'acknowledged','storage_available'}
