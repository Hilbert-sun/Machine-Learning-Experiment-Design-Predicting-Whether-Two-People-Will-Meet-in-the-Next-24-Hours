"""P02 session validation and read-only public aggregates; never fit or export."""
from dataclasses import dataclass
import csv
import json
import math
from pathlib import Path

import plotly.graph_objects as go

from src.chance_encounter import EntertainmentResult, FACTOR_NAMES, Questionnaire, evaluate_questionnaire
from src.multisource_report import load_public_results


@dataclass(frozen=True)
class PersonalAnalysis:
    status: str
    message: str
    result: EntertainmentResult | None = None


def submitted_analysis(state):
    answers=state.get('_chance_answers')
    saved=state.get('_chance_result')
    if not isinstance(answers,dict) or not isinstance(saved,EntertainmentResult):
        return PersonalAnalysis('missing','你还没有完成偶遇实验。先填写几个简单问题，我们再一起看看哪些线索影响了结果。')
    try:
        actual=evaluate_questionnaire(Questionnaire.from_mapping(answers))
    except (TypeError,ValueError):
        return PersonalAnalysis('invalid','请返回 Play 检查问卷。')
    if actual != saved:
        return PersonalAnalysis('stale','问卷已经改变，请返回 Play 重新提交，旧结果不会继续用于分析。')
    if actual.status!='ready':
        return PersonalAnalysis(actual.status,actual.message)
    strong=[c.name for c in actual.keywords if c.points>=70]
    weaker=[c.name for c in actual.keywords if c.points<30]
    message=f'从你填写的信息来看，你们的偶遇线索整体{actual.level}。'
    if strong: message+='按固定规则，较强线索包括'+'、'.join(strong)+'。'
    if weaker: message+='仍需留意'+ '、'.join(weaker)+'这些较弱线索。'
    return PersonalAnalysis('ready',message,actual)


def factor_figure(result):
    if result.status!='ready': raise ValueError('未通过校验的问卷不能生成因素图。')
    cards=result.keywords
    figure=go.Figure(go.Bar(x=[c.points for c in cards],y=[c.name for c in cards],orientation='h',
        marker_color=['#63C7B2' if c.points>=70 else '#E4AE63' if c.points>=30 else '#8593A4' for c in cards],
        customdata=[[c.direction,c.source] for c in cards],
        hovertemplate='%{y}<br>娱乐规则分值：%{x}/100<br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>'))
    unknown='、'.join(FACTOR_NAMES[f] for f in result.unknown_fields)
    figure.update_layout(title='哪些因素影响了你的偶遇指数？',xaxis={'title':'固定娱乐规则分值（不是模型重要性）','range':[0,100]},
        yaxis={'autorange':'reversed','automargin':True},height=340,margin={'l':15,'r':15,'t':60,'b':65})
    if unknown:figure.add_annotation(text='未提供 / 不确定：'+unknown,x=0,y=-.22,xref='paper',yref='paper',showarrow=False,xanchor='left')
    return figure


def load_window_comparison(root):
    folder=Path(root)/'reports/window_study'
    record=json.loads((folder/'T22_ROBUSTNESS.json').read_text())
    with (folder/'T22_METRICS.csv').open() as handle: csv_rows=list(csv.DictReader(handle))
    rows=sorted((dict(r) for r in record['main_metrics'] if r['model']=='xgboost'),key=lambda r:r['window_days'])
    if record['source_kind']!='real_public_dataset' or [r['window_days'] for r in rows]!=[1,3,7]:
        raise ValueError('T22 来源或窗口不匹配。')
    if len({(r['rows'],r['positive_rate'],r['distinct_prediction_days']) for r in rows})!=1:
        raise ValueError('T22 窗口必须属于同一测试总体。')
    if record['protocol']['candidate_policy']!='shared [t-1d,t) contacts' or record['test_used_for_selection']:
        raise ValueError('T22 共同候选或测试使用契约不匹配。')
    for row in rows:
        other=[r for r in csv_rows if r['model']=='xgboost' and int(r['window_days'])==row['window_days']]
        if len(other)!=1:raise ValueError('T22 CSV 窗口记录不完整。')
        for field in ('rows','positive_rate','distinct_prediction_days','pr_auc_average_precision'):
            if not math.isclose(float(other[0][field]),float(row[field]),rel_tol=1e-12,abs_tol=1e-12):
                raise ValueError('T22 JSON/CSV 指标不一致。')
        if not 0<=row['pr_auc_average_precision']<=1:raise ValueError('T22 排序指标无效。')
    best=max(rows,key=lambda r:r['pr_auc_average_precision'])
    ties=sum(r['pr_auc_average_precision']==best['pr_auc_average_precision'] for r in rows)
    story=(f'在这组历史实验中，使用过去{best["window_days"]}天信息的模型排序表现最好。' if ties==1 else '这组实验有多个窗口的排序表现并列。')
    return {'rows':rows,'story':story,'run_id':record['run_id'],'source':'reports/window_study/T22_ROBUSTNESS.json + T22_METRICS.csv'}


def window_figure(comparison):
    rows=comparison['rows']
    figure=go.Figure(go.Bar(x=[str(r['window_days'])+'天历史' for r in rows],y=[r['pr_auc_average_precision'] for r in rows],
        marker_color=['#8593A4','#63C7B2','#A994E6'],hovertemplate='%{x}<br>排序表现（平均精确率）：%{y:.4f}<extra></extra>'))
    figure.update_layout(title='过去看得越久，系统预测得越好吗？',yaxis={'title':'排序表现（平均精确率，0–1）','range':[0,1]},
                          height=330,margin={'l':10,'r':10,'t':65,'b':35})
    return figure


def load_group_insights(root):
    public=load_public_results(root)
    if public is None:return None
    with (Path(root)/'reports/multisource/T31_NETWORK_METRICS.csv').open() as handle: rows=list(csv.DictReader(handle))
    if public['source_kind']!='real_public_dataset':raise ValueError('T31 不是已核验的真实公开汇总。')
    for network in public['networks']:
        matches=[r for r in rows if r['dataset_id']==network['dataset_id']]
        if len(matches)!=1:raise ValueError('T31 网络来源不匹配。')
        for field in ('nodes','edges','unique_contact_records','density','mean_degree'):
            if not math.isclose(float(matches[0][field]),float(network[field]),rel_tol=1e-12,abs_tol=1e-12):
                raise ValueError('T31 网络汇总不一致。')
    return public


def source_insights(public,dataset_id):
    source=next(s for s in public['sources'] if s['dataset_id']==dataset_id)
    network=next((n for n in public['networks'] if n['dataset_id']==dataset_id),None)
    daily=[]
    if network is not None and source.get('timestamp_unit')=='seconds' and network.get('time_activity_status')=='relative_study_days':
        daily=[{k:r.get(k) for k in ('study_day','records','active_pairs')} for r in network.get('activity',[])]
    visible=[r for r in daily if r['records'] is not None]
    if visible:
        largest=max(visible,key=lambda r:r['records'])
        daily_story=f'已公开的研究日中，第{largest["study_day"]}研究日记录最多，共{largest["records"]:,}条接触记录。'
    else:daily_story='没有可核验的日级记录，不能生成日级趋势。'
    bins=network.get('degree_histogram',{}).get('bins',[]) if network else []
    if not network or network.get('degree_histogram',{}).get('status')!='aggregate':bins=[]
    if bins and any(b.get('count') is None or 0<b['count']<network['degree_histogram'].get('minimum_group_size',5) for b in bins):bins=[]
    degree_story=('已公开分组中，人数最多的是接触过'+max(bins,key=lambda b:b['count'])['bin']+'个邻居这一组。' if bins else '该来源的邻居分组未公开，不能据此推断个体差异。')
    return {'source':source,'network':network,'daily':daily,'daily_story':daily_story,'bins':bins,'degree_story':degree_story,
            'provenance':'reports/multisource/T31_SOURCE_SUMMARY.json + T31_NETWORK_METRICS.csv'}


def activity_figure(view):
    rows=view['daily']
    if not rows:raise ValueError('没有经过核验的日级数据。')
    figure=go.Figure()
    for field,name in [('records','已记录的接触事件'),('active_pairs','有记录的活跃配对')]:
        figure.add_scatter(x=[r['study_day'] for r in rows],y=[r[field] for r in rows],mode='lines+markers',
                          name=name,connectgaps=False,hovertemplate='Study Day %{x}<br>'+name+'：%{y}<extra></extra>')
    figure.update_layout(title='人们每天的接触活动一样多吗？',xaxis_title='相对研究日（Study Day）',yaxis_title='记录数量 / 配对数量',
                          height=360,legend={'orientation':'h','y':-.22},margin={'l':10,'r':10,'t':65,'b':80})
    return figure


def degree_figure(view):
    if not view['bins']:raise ValueError('邻居分组未公开。')
    figure=go.Figure(go.Bar(x=[r['bin'] for r in view['bins']],y=[r['count'] for r in view['bins']],marker_color='#A994E6',
                           hovertemplate='接触邻居：%{x}<br>匿名参与者：%{y}人<extra></extra>'))
    figure.update_layout(title='有些人会接触更多不同的人吗？',xaxis_title='有记录的接触邻居数量分组',yaxis_title='匿名参与者人数',
                          height=330,margin={'l':10,'r':10,'t':65,'b':45})
    return figure
