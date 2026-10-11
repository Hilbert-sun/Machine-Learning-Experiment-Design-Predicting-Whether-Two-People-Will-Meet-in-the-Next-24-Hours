"""P02 readable personal explanations and separate public research stories."""
import streamlit as st

from src.chance_encounter_ui import _edit
from src.encounter_graph import MUTUAL_OPTIONS, clue_graph, clue_figure, clicked_clue
from src.encounter_insights import (submitted_analysis, factor_figure, load_window_comparison, window_figure,
                                   load_group_insights, source_insights, activity_figure, degree_figure)

PLAY='pages/12_Chance_Encounter.py'
ICONS={'frequency':'🕰️','distance':'📍','area':'🧭','timing':'⏱️','recency':'🗓️'}


def _default_view():
    st.session_state['_explore_focus']='all'
    st.session_state['_explore_graph_epoch']=st.session_state.get('_explore_graph_epoch',0)+1


def render_personal():
    st.header('我的偶遇分析',anchor='my-clues')
    analysis=submitted_analysis(st.session_state)
    if analysis.status!='ready':
        st.info(analysis.message)
        if st.button('开始偶遇预测' if analysis.status=='missing' else '返回修改问卷'):
            _edit();st.switch_page(PLAY)
        return
    result=analysis.result
    st.metric('当前会话的趣味偶遇指数',f'{result.score} / 100')
    st.write(analysis.message)
    for offset in range(0,len(result.keywords),3):
        for column,card in zip(st.columns(3),result.keywords[offset:offset+3]):
            with column:
                with st.container(border=True):
                    st.subheader(ICONS.get(card.field,'🔎')+' '+card.name)
                    st.write(card.source)
                    st.caption(card.direction+' · '+card.explanation)
    st.plotly_chart(factor_figure(result),width='stretch',key='explore_factors')
    st.write('这些分值来自固定娱乐规则，并非机器学习模型测出的真实影响程度。')
    st.caption('为什么这样看：只比较你已填写的线索；不确定项不补0，也不参与平均。')
    with st.expander('了解个人线索与方法'):
        st.write('来源仅为当前会话已提交的 P01 问卷及其 Keyword。复用原评分引擎；没有 GPS、真实日程或额外朋友数据。')
    st.subheader('A 和 B 的偶遇线索图')
    st.caption('根据问卷生成的偶遇线索图，并非真实社交关系网络。连接线表示问卷字段关联，不证明双方拥有相同日程或共同好友。')
    mutual=st.selectbox('你们是否有共同认识的人？（可选，仅作示意）',tuple(MUTUAL_OPTIONS),index=None,
                        format_func=MUTUAL_OPTIONS.get,key='_explore_mutual',placeholder='不提供也可以')
    focus=st.radio('图谱焦点',('all','A','B'),format_func=lambda n:'全部线索' if n=='all' else n,key='_explore_focus',horizontal=True)
    st.button('恢复默认视图',on_click=_default_view)
    graph=clue_graph(result,mutual)
    event=st.plotly_chart(clue_figure(graph,focus),width='stretch',on_select='rerun',selection_mode='points',
                          key='explore_clues_'+str(st.session_state.get('_explore_graph_epoch',0)))
    selected=clicked_clue(event,graph)
    if selected:
        st.write('当前选中：'+graph.nodes[selected]['label'])
        st.caption(graph.nodes[selected]['description'])
    st.caption('颜色区分线索类别；线索节点大小表示该项娱乐规则分值；A/B 和共同熟人汇总节点均固定大小。灰淡节点位于当前焦点之外；悬停或点击可查看来源。共同熟人仅显示一个自述汇总节点，不参与指数。')
    if st.button('修改我的信息'):
        _edit();st.switch_page(PLAY)
    st.markdown('[看看真实研究中的相遇规律](#real-patterns)')


def render_public(root):
    st.header('真实数据中的相遇规律',anchor='real-patterns')
    st.write('这里描述研究群体的匿名设备接触记录，与上方 A/B 的个人问卷独立。研究记录不能当作你的生活经历。')
    try:
        comparison=load_window_comparison(root)
        st.caption('Copenhagen 固定实验 · 下方研究群体选择只影响接触活动与邻居分组图。')
        st.plotly_chart(window_figure(comparison),width='stretch',key='explore_windows')
        st.write(comparison['story'])
        st.caption('为什么这样看：让不同历史长度使用同一组测试样本，比较模型对记录中接触的排序表现；这不是个人偶遇概率。')
        with st.expander('了解窗口比较的数据与方法'):
            row=comparison['rows'][0]
            st.write(f'来源：{comparison["source"]}；run {comparison["run_id"]}。')
            st.write(f'同一候选总体，共{row["rows"]:,}条样本、{row["distinct_prediction_days"]}个主要测试日期。Average Precision 衡量正例排序表现，0–1；不能解释为用户偶遇概率。')
            st.write('只有少量已暴露的历史日期；没有独立长期验证，不能宣称统计显著或普遍适用。T30 的扩大总体与选择偏差保持独立，不混入此图。')
    except (OSError,ValueError,KeyError,TypeError):
        st.info('窗口研究的公开汇总缺失或不一致，暂不展示指标。')
    try:
        public=load_group_insights(root)
        if public is None:
            st.info('暂时没有可用的真实群体聚合报告。');return
        choices={s['dataset_id']:s['name'] for s in public['sources']}
        selected=st.selectbox('选择研究群体',tuple(choices),format_func=choices.get,key='_explore_source')
        view=source_insights(public,selected)
        source,network=view['source'],view['network']
        st.caption('数据来源：'+source['name']+' · 公开聚合报告')
        if network is None:
            st.info('该来源尚不可用，没有可核验记录，不生成占位曲线。')
        else:
            for column,key,label in zip(st.columns(3),('nodes','edges','unique_contact_records'),('有记录的匿名参与者','有记录的配对','去重后的接触记录')):
                column.metric(label,f'{network[key]:,}')
            if view['daily']:
                st.plotly_chart(activity_figure(view),width='stretch',key='explore_activity')
                st.write(view['daily_story'])
                st.caption('为什么这样看：比较各研究日实际公开的记录量。记录条数不等于见面次数；0只表示无记录，不证明无人接触。缺失或被抑制的值保留空白。')
            else:
                st.info('时间单位未经核实或没有日级汇总，不能生成日级趋势。')
            if view['bins']:
                st.plotly_chart(degree_figure(view),width='stretch',key='explore_degree')
                st.write(view['degree_story'])
            else:
                st.info('邻居分组未公开或被隐私规则抑制，不补0、不推断个体差异。')
            st.caption('为什么这样看：邻居分组反映这组记录里的连接范围；不能按节点数、密度或接触记录量比较哪个群体“更社交”。')
        with st.expander('了解群体数据与方法'):
            st.write('文件：'+view['provenance'])
            st.markdown('[数据来源]('+source['source_url']+')')
            st.write(source.get('reason',''))
            st.write('只使用已有公开聚合记录。Study Day 是相对研究日，不对应这里推断的公历日期；时间未知的 MIT 不生成日趋势，Social Evolution 不生成虚构曲线。接触不等于友谊。')
            st.write('High School 历史不足7天；Workplace 仅支持描述性正接触检索，未观测接触保持 Unknown。T32 快照/性能边界保持原样；本页不训练、下载或导出科研结果。')
            if network:st.write({'density':network['density'],'mean_degree':network['mean_degree'],'time_activity_status':network['time_activity_status']})
        st.info('目前没有足够的时间粒度信息，无法生成真实的活动时段图；不会从粗粒度问卷伪造小时热力图。')
    except (OSError,ValueError,KeyError,TypeError):
        st.info('群体公开汇总缺失或不一致，暂不展示对应图表。')


def render(root):
    st.title('偶遇分析 · Encounter Insights')
    st.caption('Explore · 先看自己的线索，再看研究群体的真实记录。')
    render_personal()
    st.divider()
    render_public(root)
    with st.expander('独立的科研接触网络入口'):
        st.write('公开聚合文件不含真实网络边列表，因此本页不会编造科研网络。若本地有合法、已验证的处理后记录，可主动进入原有历史接触网络；它不代表你和TA的人际关系。')
        st.page_link('pages/3_Encounter_Network.py',label='查看历史科研接触网络')
