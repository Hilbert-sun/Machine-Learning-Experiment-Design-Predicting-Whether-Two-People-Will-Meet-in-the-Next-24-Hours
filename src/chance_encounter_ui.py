"""Session-only P01 questionnaire; no dataset/model/cache/network dependencies."""
import streamlit as st

from src.chance_encounter import OPTIONS, QUESTIONS, Questionnaire, evaluate_questionnaire
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
