"""Synthetic session cases and immutable public aggregates; no private sources."""
from dataclasses import replace
import csv
import json
from pathlib import Path
import shutil

import pytest

from src.chance_encounter import Questionnaire,evaluate_questionnaire
from src.encounter_insights import (submitted_analysis,factor_figure,load_window_comparison,window_figure,
    load_group_insights,source_insights,activity_figure,degree_figure)

ROOT=Path(__file__).resolve().parents[1]
ANSWERS=Questionnaire('friend','walkable','three_five','week','sometimes','sometimes','no')


def state(answers=ANSWERS):
    return {'_chance_answers':dict(answers.__dict__),'_chance_result':evaluate_questionnaire(answers)}


@pytest.fixture
def public_root(tmp_path):
    names=['window_study/T22_ROBUSTNESS.json','window_study/T22_METRICS.csv','multisource/T31_SOURCE_SUMMARY.json',
           'multisource/T31_NETWORK_METRICS.csv','multisource/T31_RETRIEVAL_METRICS.csv','multisource/T31_FEASIBILITY.json']
    for name in names:
        dest=tmp_path/'reports'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'reports'/name,dest)
    return tmp_path


def test_personal_analysis_only_from_current_valid_submission():
    assert submitted_analysis({}).status=='missing'
    session=state();actual=submitted_analysis(session)
    assert actual.result==session['_chance_result'] and actual.result.score==66
    session['_chance_answers']['distance']='same_area'
    assert submitted_analysis(session).status=='stale'
    session.pop('_chance_result')
    assert submitted_analysis(session).status=='missing'
    session.clear();assert submitted_analysis(session).result is None


@pytest.mark.parametrize('updates,status',[
    ({'arrangement':'yes'},'out_of_scope'),({'arrangement':'unknown'},'needs_confirmation'),
    ({'frequency':'six_plus','recency':'older'},'inconsistent'),
    ({'frequency':'unknown','recency':'unknown','distance':'unknown'},'insufficient'),({'relationship':None},'invalid'),
])
def test_ineligible_submission_never_gets_analysis_index(updates,status):
    analysis=submitted_analysis(state(replace(ANSWERS,**updates)))
    assert analysis.status==status and analysis.result is None


def test_factor_chart_exactly_reuses_keywords_and_keeps_unknowns_out():
    answers=replace(ANSWERS,distance='unknown',recency='unknown')
    result=evaluate_questionnaire(answers);figure=factor_figure(result)
    assert list(figure.data[0].x)==[c.points for c in result.keywords]
    assert list(figure.data[0].y)==[c.name for c in result.keywords]
    assert len(figure.data[0].x)==3 and sum(figure.data[0].x)/3==result.score
    assert '未提供 / 不确定' in figure.layout.annotations[0].text
    assert '不是模型重要性' in figure.layout.xaxis.title.text
    with pytest.raises(ValueError):factor_figure(evaluate_questionnaire(Questionnaire()))


@pytest.mark.parametrize('relationship',['friend','classmate','coworker','acquaintance','stranger','other'])
def test_relationship_not_reweighted_in_explore(relationship):
    analysis=submitted_analysis(state(replace(ANSWERS,relationship=relationship)))
    assert analysis.result.score==66
    assert list(factor_figure(analysis.result).data[0].x)==[70,75,55,55,75]


def test_real_window_comparison_is_read_not_hardcoded(public_root):
    comparison=load_window_comparison(public_root)
    frozen=json.loads((public_root/'reports/window_study/T22_ROBUSTNESS.json').read_text())
    original=sorted((r for r in frozen['main_metrics'] if r['model']=='xgboost'),key=lambda r:r['window_days'])
    assert comparison['rows']==original
    assert list(window_figure(comparison).data[0].y)==[r['pr_auc_average_precision'] for r in original]
    assert len({r['rows'] for r in comparison['rows']})==1
    assert '偶遇概率' not in window_figure(comparison).layout.yaxis.title.text
    path=public_root/'reports/window_study/T22_ROBUSTNESS.json'
    next(r for r in frozen['main_metrics'] if r['model']=='xgboost' and r['window_days']==1)['pr_auc_average_precision']=.9
    path.write_text(json.dumps(frozen))
    csv_path=public_root/'reports/window_study/T22_METRICS.csv'
    with csv_path.open() as f:rows=list(csv.DictReader(f))
    next(r for r in rows if r['model']=='xgboost' and r['window_days']=='1')['pr_auc_average_precision']='.9'
    with csv_path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    assert '过去1天' in load_window_comparison(public_root)['story']


def test_mixed_cohorts_or_csv_conflicts_refused(public_root):
    path=public_root/'reports/window_study/T22_ROBUSTNESS.json';record=json.loads(path.read_text())
    row=next(r for r in record['main_metrics'] if r['model']=='xgboost' and r['window_days']==3)
    row['rows']+=1;path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='同一测试总体'):load_window_comparison(public_root)
    row['rows']-=1;row['pr_auc_average_precision']+=.01;path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='不一致'):load_window_comparison(public_root)


def test_real_daily_counts_and_histogram_preserve_public_data(public_root):
    public=load_group_insights(public_root);view=source_insights(public,'workplace2013')
    original=next(n for n in public['networks'] if n['dataset_id']=='workplace2013')
    assert [r['records'] for r in view['daily']]==[r['records'] for r in original['activity']]
    assert sum(b['count'] for b in view['bins'])==view['network']['nodes']
    assert list(degree_figure(view).data[0].y)==[b['count'] for b in view['bins']]
    view['daily'][1]['records']=None;view['daily'][1]['active_pairs']=None
    figure=activity_figure(view)
    assert figure.data[0].y[1] is None and figure.data[1].y[1] is None
    assert figure.data[0].y[5]==0 and figure.data[0].connectgaps is False
    assert '相对研究日' in figure.layout.xaxis.title.text


def test_unverified_or_unavailable_source_never_gets_daily_curve(public_root):
    public=load_group_insights(public_root)
    mit=source_insights(public,'reality_mining_mendeley')
    assert mit['daily']==[] and mit['network'] is not None
    with pytest.raises(ValueError):activity_figure(mit)
    unavailable=source_insights(public,'social_evolution')
    assert unavailable['network'] is None and unavailable['daily']==[] and unavailable['bins']==[]
    highschool=source_insights(public,'highschool2013')
    assert highschool['source']['status']=='insufficient_history' and len(highschool['daily'])==5


def test_suppression_and_missing_histogram_never_become_zero(public_root):
    public=load_group_insights(public_root)
    assert not source_insights(public,'workplace2015')['bins']
    with pytest.raises(ValueError):degree_figure(source_insights(public,'workplace2015'))
    network=next(n for n in public['networks'] if n['dataset_id']=='workplace2013')
    network['degree_histogram']['bins'][0]['count']=None
    assert source_insights(public,'workplace2013')['bins']==[]
