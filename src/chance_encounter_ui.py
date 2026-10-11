"""Session-only P01 questionnaire; no dataset/model/cache/network dependencies."""
import streamlit as st

from src.chance_encounter import OPTIONS, QUESTIONS, Questionnaire, evaluate_questionnaire


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
        for offset in range(0,len(result.keywords),3):
            for column,card in zip(st.columns(3),result.keywords[offset:offset+3]):
                with column:
                    with st.container(border=True):
                        st.subheader(card.name)
                        st.caption(card.direction)
                        st.write(card.explanation)
                        st.caption(card.source)
        left,right=st.columns(2)
        left.button('修改信息',on_click=_edit)
        right.button('重新开始',on_click=_restart)
        if st.button('查看我的偶遇分析'):
            st.switch_page('pages/13_Encounter_Insights.py')
        return
    saved=st.session_state.get('_chance_answers',{})
    with st.form('chance_questionnaire'):
        st.caption('过去30天的次数与最近一次时间都只填写未提前安排的偶遇；至少提供3项有效历史或日常线索。不确定可以如实选择。')
        values={}
        for field,choices in OPTIONS.items():
            key='chance_input_'+field
            if key not in st.session_state:
                st.session_state[key]=saved.get(field)
            values[field]=st.selectbox(QUESTIONS[field],tuple(choices),index=None,format_func=choices.get,
                                       key=key,placeholder='请选择')
        submitted=st.form_submit_button('计算趣味偶遇指数',type='primary')
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
