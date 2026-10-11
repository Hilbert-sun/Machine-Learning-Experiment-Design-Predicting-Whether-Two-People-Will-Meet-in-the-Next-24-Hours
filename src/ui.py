"""Shared presentation helpers. Dataset and model logic live in separate modules."""

import streamlit as st

PAGES = (
    ("pages/0_Overview.py", "概览 · Overview"),
    ("pages/1_Data_Manager.py", "数据管理 · Data Manager"),
    ("pages/2_Data_Explorer.py", "数据探索 · Data Explorer"),
    ("pages/3_Encounter_Network.py", "相遇网络 · Encounter Network"),
    ("pages/4_Model_Training.py", "模型训练 · Model Training"),
    ("pages/5_Prediction_Lab.py", "预测实验室 · Prediction Lab"),
    ("pages/6_Model_Evaluation.py", "模型评估 · Model Evaluation"),
    ("pages/7_Data_Sources.py", "数据来源 · Data Sources"),
    ("pages/8_History_Window_Study.py", "历史窗口研究 · History Window Study"),
    ("pages/9_Dataset_Catalog.py", "数据目录 · Dataset Catalog"),
    ("pages/10_Time_Machine.py", "时间机器 · Time Machine"),
    ("pages/11_Multi_Dataset_Exploration.py", "多数据集探索 · Multi-Dataset Exploration"),
    ("pages/12_Chance_Encounter.py", "趣味偶遇预测 · Chance Encounter"),
    ("pages/13_Encounter_Insights.py", "偶遇分析 · Encounter Insights"),
    ("pages/14_Research_Hub.py", "科研中心 · Research Hub"),
)


PRIMARY_PAGES = (
    ("pages/0_Overview.py", "首页 Home", "🏠"),
    ("pages/12_Chance_Encounter.py", "玩一玩 Play", "✨"),
    ("pages/13_Encounter_Insights.py", "数据分析 Explore", "🔎"),
    ("pages/14_Research_Hub.py", "科研中心 Research", "🔬"),
)

RESEARCH_GROUPS = (
    ("数据与探索", (
        (1, "导入、验证与清洗数据；下载需主动操作。"),
        (2, "查看已处理接触记录的分布。"),
        (3, "浏览真实历史接触网络，与问卷线索图独立。"),
        (7, "核对数据来源、许可与研究限制。"),
        (9, "查看各来源的数据质量与可用状态。"),
    )),
    ("机器学习与评估", (
        (4, "主动训练模型；进入页面不会开始训练。"),
        (5, "使用已保存模型运行预测。"),
        (6, "检查保存的评估结果与概率校准。"),
        (8, "比较同一研究队列的1、3、7天历史窗口。"),
    )),
    ("高级研究", (
        (10, "模拟历史时点预测，冻结后独立揭晓结果。"),
        (11, "查看多来源描述网络与正接触检索。"),
    )),
)


def primary_navigation():
    with st.container(horizontal=True, wrap=True, gap="small"):
        for path, label, icon in PRIMARY_PAGES:
            st.page_link(path, label=label, icon=icon)


def empty_page(title: str, message: str) -> None:
    st.title(title)
    st.info(message)
    st.page_link("pages/1_Data_Manager.py", label="前往数据管理")


def source_links() -> None:
    st.markdown(
        "[Copenhagen 官方数据](https://figshare.com/articles/dataset/"
        "The_Copenhagen_Networks_Study_interaction_data/7267433) · "
        "[SocioPatterns 官方数据](https://sociopatterns.org/datasets/"
        "high-school-contact-and-friendship-networks/)"
    )


def dataset_picker() -> str:
    # Keep the selection outside widget state, which Streamlit removes on page changes.
    st.session_state["_dataset"] = st.session_state.get("selected_dataset", "Copenhagen")

    def remember_selection() -> None:
        st.session_state["selected_dataset"] = st.session_state["_dataset"]

    return st.selectbox(
        "数据集", ["Copenhagen", "SocioPatterns"], key="_dataset", on_change=remember_selection
    )
