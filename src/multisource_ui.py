"""Read aggregate T31 evidence only; page reruns never scan raw data or run experiments."""

import pandas as pd
import streamlit as st

from src.multisource_report import load_public_results, study_figures


def render(root):
    st.title('多数据集探索 · Multi-Dataset Exploration')
    st.warning('Descriptive Network Analysis / Observed Positive Retrieval。未记录接触保持 Unknown；检索捕获率不代表全部真实接触召回率。')
    result = load_public_results(root)
    st.caption('聚合报告缓存按文件内容版本隔离；不缓存或显示其他会话的私人预测。')
    if result is None:
        st.info('尚无真实 T31 聚合报告。请在合法本地数据准备好后运行 python -m src.multisource_exploration。')
        return
    st.caption('真实聚合报告 · run ' + result['run_id'] + '。Copenhagen 主二分类实验保持冻结，不与这里的检索指标混排。')
    columns = ['dataset_id', 'status', 'participants', 'event_rows', 'valid_pairs', 'span_days']
    st.dataframe(pd.DataFrame([{k: s.get(k) for k in columns} for s in result['sources']]), hide_index=True)
    source = st.selectbox('Dataset Source', result['sources'], format_func=lambda s: s['name'])
    st.markdown(f"[来源]({source['source_url']}) · {source['licence']}")
    st.write(source.get('reason', ''))
    network = next((n for n in result['networks'] if n['dataset_id'] == source['dataset_id']), None)
    retrieval = [r for r in result['retrieval'] if r['dataset_id'] == source['dataset_id']]
    if network is None:
        st.info('source_unavailable / blocked：没有经过核验的真实文件，不展示占位指标。')
        return
    st.subheader('Descriptive Network Analysis')
    for col, key, label in zip(st.columns(3), ['nodes', 'edges', 'unique_contact_records'], ['Contact IDs', 'Observed pairs', 'Unique contact records']):
        col.metric(label, f'{network[key]:,}')
    st.caption('按源独立的全档案描述网络；接触记录次数不是会面次数。小分组被抑制时不显示分布。')
    st.dataframe(pd.DataFrame([{k: network[k] for k in ['components', 'largest_component_nodes', 'density', 'mean_degree']}]), hide_index=True)
    for figure in study_figures(source, network, retrieval):
        st.plotly_chart(figure, width='stretch')
    st.subheader('Observed Positive Retrieval')
    feasibility = next(f for f in result['feasibility'] if f['dataset_id'] == source['dataset_id'])
    st.json(feasibility)
    if not retrieval:
        st.info('time_unit_unverified 或 insufficient_history：不支持 24 小时检索。')
    else:
        st.caption('common_7d 共享日期与候选；per_window 的日期不同。空分母不可用；小样本抑制为空。无显著性结论，不能跨源比较模型强弱。')
        st.dataframe(pd.DataFrame(retrieval), hide_index=True)
