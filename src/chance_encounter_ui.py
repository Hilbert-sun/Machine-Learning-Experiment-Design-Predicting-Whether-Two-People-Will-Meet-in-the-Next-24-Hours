"""Session-only P01 questionnaire; no dataset/model/cache/network dependencies.

The research-reference card reads only the reviewed public aggregate studies/play_reference/PLAY_REFERENCE.json.
"""
import streamlit as st

from src.chance_encounter import OPTIONS, QUESTIONS, Questionnaire, evaluate_questionnaire
from src.play_reference import reference
from src.product_ui import keyword_cards


def _clear_explore():
    for key in list(st.session_state):
        if key.startswith('_explore_'):
            del st.session_state[key]


def _edit():
    _clear_explore()
    st.session_state['_chance_view']='form'
    st.session_state.pop('_chance_result',None)


def _restart():
    _clear_explore()
    for key in list(st.session_state):
        if key.startswith(('_chance_','chance_input_')):
            del st.session_state[key]


def research_reference_card(answers):
    """Study re-contact share for similar pairs, read from the reviewed public aggregate only."""
    ref = reference(answers.get('recency'), answers.get('frequency'))
    with st.container(border=True):
        st.markdown('**研究参照 · 来自 Copenhagen 研究，不是你们的概率**')
        if ref['status'] == 'ready':
            st.write(f"在 Copenhagen 研究的学生中，最近一次接触在{ref['recency_text']}、过去 14 天里有{ref['frequency_text']}有接触的配对，"
                     f"第二天再次被蓝牙记录到接触的比例约为 **{ref['rate']*100:.0f}%**"
                     f"（{ref['samples']:,} 个样本；全部配对平均 {ref['overall_rate']*100:.0f}%）。")
        else:
            st.write(ref['reason'])
        st.caption('数据是丹麦一所大学学生约一个月的蓝牙接近记录；问卷选项只能粗略对应研究分组（用过去 14 天的接触天数近似"过去 30 天的次数"），'
                   '这个比例不能当作你们真实的相遇概率。上面的趣味指数仍按固定规则计算，与这里无关。')


def render():
    st.title('趣味偶遇预测 · Chance Encounter')
    st.caption('Play · 用自述的历史与日常线索，探索未来24小时未提前约定的偶然相遇倾向。')
    st.write('无需登录、数据集或模型。这里只计算固定规则的趣味偶遇指数，不是真实相遇概率。')
    if st.session_state.get('_chance_view')=='result':
        result=st.session_state['_chance_result']
        st.metric('趣味偶遇指数',f'{result.score} / 100')
        st.subheader('趣味倾向：'+result.level)
        st.write(result.message)
        if result.unknown_fields:
            st.caption(f'{len(result.unknown_fields)}项不确定或未填写的信息未参与计分，也未被当作负面证据。')
        keyword_cards(result.keywords)
        research_reference_card(st.session_state.get('_chance_answers', {}))
        if st.button('查看我的偶遇分析', type='primary', width='stretch'):
            st.switch_page('pages/13_Encounter_Insights.py')
        left,right=st.columns(2)
        left.button('修改信息',on_click=_edit,width='stretch')
        right.button('重新开始',on_click=_restart,width='stretch')
        return
    saved=st.session_state.get('_chance_answers',{})
    with st.form('chance_questionnaire'):
        st.caption('过去30天的次数与最近一次时间都只填写未提前安排的偶遇；至少提供3项有效历史或日常线索。不确定可以如实选择。')
        st.caption('关系类型与见面约定需明确；其余5项线索至少回答3项。约定见面不属于偶遇。')
        values={}
        for field,choices in OPTIONS.items():
            if field=='relationship': st.subheader('1 · 你和TA')
            elif field=='frequency': st.subheader('2 · 过去的偶遇与日常')
            elif field=='arrangement': st.subheader('3 · 确认未来约定')
            key='chance_input_'+field
            if key not in st.session_state:
                st.session_state[key]=saved.get(field)
            values[field]=st.selectbox(QUESTIONS[field],tuple(choices),index=None,format_func=choices.get,
                                       key=key,placeholder='请选择',help=('只选择粗略范围，无需提供身份或具体地点。' if field=='distance' else '按实际情况选择；不确定时请如实选择，不会自动记为0。'))
        submitted=st.form_submit_button('计算趣味偶遇指数',type='primary',width='stretch')
    if submitted:
        result=evaluate_questionnaire(Questionnaire.from_mapping(values))
        st.session_state['_chance_answers']=values
        st.session_state['_chance_result']=result
        if result.status=='ready':
            st.session_state['_chance_view']='result'
            st.rerun()
    result=st.session_state.get('_chance_result')
    if result is not None and result.status!='ready':
        st.info(result.message)
        for issue in result.issues:
            st.caption(QUESTIONS[issue.field]+' '+issue.message)
