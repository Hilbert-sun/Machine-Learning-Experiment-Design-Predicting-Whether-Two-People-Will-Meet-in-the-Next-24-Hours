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
)


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
