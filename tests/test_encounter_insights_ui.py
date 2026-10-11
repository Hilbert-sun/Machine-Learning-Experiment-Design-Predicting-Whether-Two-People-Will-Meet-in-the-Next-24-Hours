"""P02 public-only navigation, session isolation and explanation regressions."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.chance_encounter import evaluate_questionnaire
from test_encounter_insights import ANSWERS
from test_chance_encounter_ui import fill,VALID

ROOT=Path(__file__).resolve().parents[1]
APP=str(ROOT/'app.py');EXPLORE='pages/13_Encounter_Insights.py';PLAY='pages/12_Chance_Encounter.py'


@pytest.fixture(autouse=True)
def isolate_paths(monkeypatch,tmp_path):
    import yaml
    config=yaml.safe_load((ROOT/'configs/default.yaml').read_text())
    config['paths']={name:str(tmp_path/name) for name in config['paths']}
    monkeypatch.setattr(yaml,'safe_load',lambda _:config)


def app_at(page=EXPLORE):return AppTest.from_file(APP,default_timeout=15).run().switch_page(page).run()
def button(app,label):return next(b for b in app.button if b.label==label)
def personal_metrics(app):return [m for m in app.metric if m.label=='当前会话的趣味偶遇指数']


def test_public_default_explore_has_no_private_reads_or_personal_demo(monkeypatch):
    import pandas as pd
    from src.model_registry import ModelRegistry
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('Explore read private Parquet.'))
    monkeypatch.setattr(ModelRegistry,'load',lambda *a,**k:pytest.fail('Explore loaded a model.'))
    app=app_at()
    assert not app.exception and not personal_metrics(app)
    assert any('你还没有完成偶遇实验' in i.value for i in app.info)
    assert len(app.get('plotly_chart'))==3
    assert not any(r.label=='图谱焦点' for r in app.radio)
    button(app,'开始偶遇预测').click().run()
    assert not app.exception and len(app.selectbox)==7


def test_play_explore_edit_recompute_reset_and_isolated_session():
    app=fill(app_at(PLAY),VALID)
    button(app,'查看我的偶遇分析').click().run()
    assert not app.exception and personal_metrics(app)[0].value=='66 / 100'
    assert len(app.get('plotly_chart'))==5
    assert app.title[0].value=='偶遇分析 · Encounter Insights'
    # AppTest keeps its explicit page hash across runs; bind the observed switch_page target.
    app.switch_page(EXPLORE).run()
    app.selectbox(key='_explore_mutual').select('three_five').run()
    assert personal_metrics(app)[0].value=='66 / 100'
    app.radio(key='_explore_focus').set_value('A').run()
    button(app,'恢复默认视图').click().run()
    assert not app.exception and app.radio(key='_explore_focus').value=='all'
    fresh=app_at();assert not personal_metrics(fresh)
    button(app,'修改我的信息').click().run()
    assert not app.exception and not app.metric
    assert app.title[0].value=='趣味偶遇预测 · Chance Encounter'
    app.switch_page(PLAY).run()
    app.switch_page(EXPLORE).run()
    assert not personal_metrics(app) and any('你还没有完成' in i.value for i in app.info)
    app.switch_page(PLAY).run();fill(app,{'distance':'same_area'})
    button(app,'查看我的偶遇分析').click().run()
    assert personal_metrics(app)[0].value=='71 / 100'
    app.switch_page(EXPLORE).run()
    assert app.selectbox(key='_explore_mutual').value is None
    app.switch_page(PLAY).run();button(app,'重新开始').click().run()
    app.switch_page(EXPLORE).run()
    assert not app.exception and not personal_metrics(app)


@pytest.mark.parametrize('arrangement',['yes','unknown'])
def test_unconfirmed_or_planned_encounter_not_analyzed(arrangement):
    app=fill(app_at(PLAY),{**VALID,'arrangement':arrangement})
    app.switch_page(EXPLORE).run()
    assert not app.exception and not personal_metrics(app)
    assert any('约定' in i.value for i in app.info)


def test_external_answer_change_cannot_keep_old_result():
    app=app_at();app.session_state['_chance_answers']=dict(ANSWERS.__dict__)
    app.session_state['_chance_result']=evaluate_questionnaire(ANSWERS)
    app.run();assert personal_metrics(app)
    answers=dict(ANSWERS.__dict__);answers['distance']='same_area'
    app.session_state['_chance_answers']=answers;app.run()
    assert not personal_metrics(app) and any('问卷已经改变' in i.value for i in app.info)


def test_unknown_time_and_unavailable_sources_have_no_invented_curves():
    app=app_at()
    app.selectbox(key='_explore_source').select('reality_mining_mendeley').run()
    assert not app.exception and len(app.get('plotly_chart'))==1
    assert any('时间单位未经核实' in i.value for i in app.info)
    app.selectbox(key='_explore_source').select('social_evolution').run()
    assert not app.exception and len(app.get('plotly_chart'))==1
    assert any('该来源尚不可用' in i.value for i in app.info)


def test_home_three_entries_lazy_research_and_old_metrics_preserved(monkeypatch):
    import src.loader as loader
    calls=[]
    monkeypatch.setattr(loader,'supported_files',lambda *a:calls.append(True) or [])
    app=AppTest.from_file(APP).run()
    assert not app.exception and not calls and not app.metric
    labels=[p.proto.label for p in app.get('page_link')]
    assert '开始偶遇预测 · Play' in labels and '看看数据分析 · Explore' in labels
    button(app,'深入研究').click().run()
    assert not app.exception and calls and len(app.metric)==6
    assert all(m.value=='—' for m in app.metric)
    button(app,'收起科研概览').click().run()
    assert not app.exception and not app.metric


def test_p01_rule_and_welcome_sources_preserved():
    import subprocess
    baseline='ab4dc3f20e5bcd587a5d4caf5611f5bc3fb0afbb'
    for name in ('src/chance_encounter.py','src/welcome.py'):
        assert (ROOT/name).read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',baseline+':'+name])
