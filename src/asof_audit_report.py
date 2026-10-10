"""T30 aggregate-only Markdown/CSV/JSON/HTML; no sample identifiers are published."""

import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


def _number(value):return 'unavailable' if value is None else f'{value:.6f}'


def write_report(result,directory,root):
    root,directory=Path(root),Path(directory);public=root/'reports/asof_audit';public.mkdir(parents=True,exist_ok=True)
    summary=result['summary'];metrics=sorted(summary['metrics'],key=lambda r:(r['scope'],r['window_days'],r['model']))
    (public/'T30_PROTOCOL.json').write_text(json.dumps(result['protocol'],ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (public/'T30_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    for filename,rows in [('T30_METRICS.csv',metrics),('T30_DAILY.csv',summary['daily_funnel']),('T30_GROUPS.csv',summary['subgroups']),
                          ('T30_ERRORS.csv',summary['errors']),('T30_SELECTION_BIAS.csv',summary['population_distributions'])]:
        pd.DataFrame(rows).to_csv(public/filename,index=False)
    text=f'''# T30 — As-of预测质量与选择偏差审计

Run:`{result['run_id']}`。来源:`{result['source_kind']}`。日期:2026-10-10 (Asia/Kuala_Lumpur)。

本报告是已公开时期的事后描述性审计，不是全新独立测试。冻结模型、参数、分类阈值未重选；未重新训练。**可靠标签子集上的指标不能直接代表全部候选配对的无偏性能。Unknown从未当作负例，也未进入二分类指标。**

## 先预测，再揭晓

候选只由[t-1d,t)接触生成；1/3/7d特征通过T28有界接口从原始过去记录计算。核实模型的数据集/原点/窗口/标签信息截止时间及共同覆盖策略后，使用原冻结分类阈值。各窗口共享完全相同候选键和共同可预测/可评估子集。所有预测先保存并SHA256冻结，再独立读取(t,t+24h]接触/扫描；旧T22队列只在预测冻结后用于对账和分布比较。

全部候选:{summary['candidates']:,}；共同可预测:{summary['prediction_available']:,}；可可靠揭晓:{summary['reliable_labels']:,}；Unknown:{summary['unknown_labels']:,}；实际预测日期:{summary['distinct_prediction_days']}。可预测性仅依赖过去输入，与未来可评价性分开记录。

可靠揭晓定义遵守T28：观察到正接触即Contact；没有接触记录时，完整未来窗口和两端足够扫描才是No Contact，否则Unknown。这种可评价性本身依赖正事件是否被检测以及未来观测，可能产生强选择偏差。严格未来覆盖子集另行报告，保留与旧T22的可比性。

## 每日筛选漏斗

| Study Day | 候选 | 可预测 | 正例 | 负例 | Unknown | Unknown比例 | 旧T22 | 新增候选 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
'''
    for r in summary['daily_funnel']:
        text+=f"|{r['study_day']}|{r['rows']}|{r['prediction_available']}|{r['positive']}|{r['negative']}|{r['unknown']}|{_number(r['unknown_rate'])}|{r['old_t22_rows']}|{r['added_rows']}|\n"
    evaluable=next(r['rows'] for r in metrics if r['scope']=='reliable_predicted')
    rejected=summary['candidates']-summary['prediction_available']
    known_rejected=summary['reliable_labels']-evaluable
    text+=f"\n缺少可核实的过去扫描输入而拒绝推理:{rejected}；其中{known_rejected}有可揭晓标签、{rejected-known_rejected}为Unknown。共同指标因此使用{evaluable:,}行，而非全部{summary['reliable_labels']:,}个已知标签。标签能揭晓不等于当时能合法生成预测。\n"
    text+='\n## 相同可靠标签子集上的冻结模型表现\n\n'
    text+='| 模型 | 窗口 | N | 正例率 | AP | ROC-AUC | Brier | Log Loss | Precision | Recall | F1 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n'
    for r in metrics:
        if r['scope']=='reliable_predicted':
            text+=f"|{r['model']}|{r['window_days']}d|{r['rows']}|"+'|'.join(_number(r[k]) for k in ['positive_rate','pr_auc_average_precision','roc_auc','brier_score','log_loss','precision','recall','f1'])+'|\n'
    text+='''
全部指标条件于“可预测且可靠揭晓”。常数排序AP等于该范围正例率；不能将不同范围的原始AP直接解释为纯模型改善。完整CSV还分别列出strict_covered_predicted、old_t22_overlap和added_reliable_predicted。单类范围ROC-AUC为空；新增可评价范围可能只有观察到的正例，AP=1只是该选择规则的退化结果，不是完美预测证明。无可评价样本时指标为空，禁止制造分数。

## 新旧人群分布与选择偏差

| 人群 | N | 正例 | 负例 | Unknown | Unknown比例 | 可靠标签正例率 | 过去1d bins均值 | 过去扫描均值 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
'''
    for r in summary['population_distributions']:
        text+=f"|{r['population']}|{r['rows']}|{r['positive']}|{r['negative']}|{r['unknown']}|"+'|'.join(_number(r[k]) for k in ['unknown_rate','positive_rate_reliable_only','past_contact_bins_mean','past_scan_mean'])+'|\n'
    added=next(r for r in summary['population_distributions'] if r['population']=='added_asof')
    unknown_rate='unavailable' if added['unknown_rate'] is None else f"{added['unknown_rate']:.2%}"
    text+=f"\n新增{added['rows']:,}个候选中，{added['unknown']:,}个Unknown（{unknown_rate}）；可揭晓的{added['positive']:,}个正例、{added['negative']:,}个负例，说明新增可见标签并非代表性随机样本。\n"
    new=next((r for r in metrics if r['scope']=='reliable_predicted' and r['model']=='xgboost' and r['window_days']==7),None)
    old=next((r for r in metrics if r['scope']=='old_t22_overlap' and r['model']=='xgboost' and r['window_days']==7),None)
    if new and old and all(r[k] is not None for r in (new,old) for k in ('positive_rate','pr_auc_average_precision','brier_score','log_loss')):
        text+=f"\nXGBoost7d从旧队列到新可靠子集，正例率{old['positive_rate']:.2%}→{new['positive_rate']:.2%}，AP{old['pr_auc_average_precision']:.6f}→{new['pr_auc_average_precision']:.6f}，但Brier{old['brier_score']:.6f}→{new['brier_score']:.6f}、Log Loss{old['log_loss']:.6f}→{new['log_loss']:.6f}。排名指标与概率损失变化必须连同人群/可见性变化解释，不能宣布全体预测改善。\n"
    text+=f"\n旧T22标签对账:{result['old_t22_label_reconciliation']}；旧队列上逐样本冻结概率对账:{result['old_t22_probability_reconciliation']}。严格覆盖与旧队列匹配时，同队列模型指标应重现；新可靠范围的变化来自标签可见性/人群差异，不能称为独立验证提升。\n"
    text+='''
过去接触频率组(1、2–5、>5个bins)、过去两端最小扫描覆盖组(未知、<0.5、0.5–0.75、>=0.75)和预测日均固定自1d历史，对所有窗口相同。T30_GROUPS.csv同时给候选数、Unknown率和可靠子集指标；不能只看分组AP而忽略不同正例率/可见率。全体观察正例占比仅是下界，不是未知标签被补成0的真实正例率。

概率可靠性曲线和10-bin计数来自可靠可预测子集；Unknown预测概率分布另外汇总。错误统计使用原验证阈值，包括FP/FN/TP/TN及预先固定0.2/0.8的高置信错误。每个实际错误案例只保存在本地忽略的error_cases.parquet；公开报告只有统计，不含配对ID。没有利用这些错误重新调参、校准或选阈值。

## 配对日期敏感性（非显著性结论）

'''
    for row in summary['paired_descriptive_contrasts']:
        text+=f"- {row['model']}:7d−1d AP={_number(row['pooled_delta_AP_7d_minus_1d'])}；删除整日敏感性范围={row['descriptive_leave_one_day_out_range']}；状态={row['status']}；CI={row['confidence_interval']}。\n"
    text+='''
初始协议只包含旧T22已报告的Study Days24–27；只有4个实际预测日，少于预先固定8日的区间门槛，不给p值、显著性或貌似精确的独立试验结论。用户/配对/日期有依赖，删除整日范围不是置信区间。

## 复现、私有输出与限制

```bash
.venv/bin/python -m src.asof_audit
.venv/bin/python -m src.asof_audit --verify-only
```

完整概率和标签位于data/processed/asof_audit/<run_id>/下的predictions.parquet、samples.parquet、error_cases.parquet，均忽略于Git。PROTOCOL_FROZEN/PREDICTIONS_FROZEN记录模型/源码/来源/日期/规则及预测阶段摘要；RESULTS记录产物校验值。verify-only从私有样本重算全部指标、漏斗、分组、可靠性与错误统计。完成的同协议run直接校验复用；不拟合或下载。HTML交互报告位于该私有run目录，公开CSV/JSON只含聚合结果。

未来扫描是观测代理而非绝对负例真值；正事件可见性、在线状态、过去输入可用性及仅4日期共同限制推广。当前审计无法识别Unknown配对的真实事件率，因此没有全候选总体无偏AP、ROC或校准保证。事件时间并不证明数据当时已上传，静态归档不是真实时流。所有T17–T27冻结实验和T28/T29推理契约保持原样。T31多数据集探索尚未开始。
'''
    (root/'ASOF_AUDIT.md').write_text(text)
    figures=[]
    for metric in ('pr_auc_average_precision','roc_auc','brier_score','log_loss'):
        figure=go.Figure()
        for scope in ('reliable_predicted','old_t22_overlap'):
            for model in sorted({r['model'] for r in metrics}):
                rows=sorted((r for r in metrics if r['scope']==scope and r['model']==model),key=lambda r:r['window_days'])
                figure.add_scatter(x=[r['window_days'] for r in rows],y=[r[metric] for r in rows],mode='lines+markers',name=f'{scope}/{model}')
        figure.update_layout(title=metric+' · conditional populations',xaxis_title='History days')
        figures.append(figure)
    calibration=go.Figure()
    for tag in sorted({r['tag'] for r in summary['reliability']}):
        rows=[r for r in summary['reliability'] if r['tag']==tag]
        calibration.add_scatter(x=[r['mean_probability'] for r in rows],y=[r['observed_fraction'] for r in rows],mode='lines+markers',name=tag)
    calibration.add_scatter(x=[0,1],y=[0,1],mode='lines',name='ideal')
    calibration.update_layout(title='Reliability on reliable predicted labels only',xaxis_title='Mean probability',yaxis_title='Observed positive fraction')
    figures.append(calibration)
    daily=summary['daily_funnel']
    funnel=go.Figure()
    for key in ('positive','negative','unknown'):
        funnel.add_bar(x=[r['study_day'] for r in daily],y=[r[key] for r in daily],name=key)
    funnel.update_layout(title='As-of candidates by revealed observability',barmode='stack',xaxis_title='Study Day')
    figures.append(funnel)
    fragments=["<!doctype html><html><head><meta charset='utf-8'><title>T30 as-of audit</title></head><body>",'<pre>'+html.escape(text)+'</pre>']
    for i,figure in enumerate(figures):fragments.append(figure.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    fragments.append('</body></html>');(directory/'T30_REPORT.html').write_text(''.join(fragments))
    return public
