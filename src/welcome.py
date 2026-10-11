"""One native welcome dialog; browser sessionStorage contains ONLY an ack flag."""
import streamlit as st
from streamlit.components.v2 import component

# Trusted static JavaScript, no questionnaire values, HTML interpolation or HTTP.
# sessionStorage is tab-scoped, survives reload, and normally ends with the tab.
WELCOME_JS = """
export default function({data, setStateValue}) {
    let acknowledged = data.confirmed === true;
    let available = true;
    try {
        if (acknowledged) sessionStorage.setItem('encounter_lab_welcome_v1', '1');
        else acknowledged = sessionStorage.getItem('encounter_lab_welcome_v1') === '1';
    } catch (_) { available = false; }
    setStateValue('acknowledged', acknowledged);
    setStateValue('storage_available', available);
}
"""


def browser_acknowledgement(confirmed):
    # Register the identical definition in the current runtime (AppTest recreates it).
    ack_component=component('encounter_welcome_ack',js=WELCOME_JS)
    result=ack_component(data={'confirmed':confirmed},key='encounter_welcome_storage',height=0,
                          default={'acknowledged':None,'storage_available':None},
                          on_acknowledged_change=lambda:None,on_storage_available_change=lambda:None)
    return result.acknowledged


@st.dialog('欢迎来到 Encounter Lab · 相遇实验室',dismissible=False)
def _welcome_dialog():
    st.write('在这里，你可以用一些历史信息，探索两个人未来24小时偶然相遇的趣味倾向。')
    st.write('本项目纯属娱乐，请勿当真。')
    st.write('趣味指数不是经过验证的真实相遇概率，科研实验结果与娱乐评分彼此独立。')
    if st.button('我知道了，开始探索',type='primary'):
        st.session_state['_welcome_acknowledged']=True
        st.rerun()


def render_welcome():
    # Wait for actual browser hydration; AppTest cannot execute component JS.
    # A False response opens the dialog, True restores acknowledgement on reload.
    restored=browser_acknowledgement(st.session_state.get('_welcome_acknowledged',False))
    if restored is True:
        st.session_state['_welcome_acknowledged']=True
    if not st.session_state.get('_welcome_acknowledged',False) and restored is False:
        _welcome_dialog()
