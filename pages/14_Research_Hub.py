"""Directory of registered research pages; statistics remain opt-in."""
import streamlit as st
from src.ui import PAGES, RESEARCH_GROUPS

st.title("科研中心 · Research Hub")
st.caption("Research · 从数据到模型，按需要打开研究工具；进入目录不会训练或下载。")
for title, entries in RESEARCH_GROUPS:
    with st.expander(title, expanded=True):
        for index, description in entries:
            path, label = PAGES[index]
            st.page_link(path, label=label)
            st.caption(description)
with st.expander("研究报告与复现说明"):
    base = "https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/blob/research-v2.2/"
    for name, label in (("docs/FINAL_RESEARCH_AUDIT.md", "科研审计与结果边界"), ("docs/REPRODUCIBILITY.md", "分级复现指南"), ("docs/PRODUCT_DELIVERY.md", "产品操作与交付说明")):
        st.link_button(label, base + name)
st.divider()
st.subheader("科研概览 · 原 Overview 统计")
st.caption("保留原有数据统计；仅主动打开后检查本地清洗缓存与模型清单。")
if st.session_state.get('_overview_research_open', False):
    if st.button("收起科研概览"):
        st.session_state['_overview_research_open'] = False
        st.rerun()
    from src.research_overview_ui import render
    render()
elif st.button("打开科研概览"):
    st.session_state['_overview_research_open'] = True
    st.rerun()
