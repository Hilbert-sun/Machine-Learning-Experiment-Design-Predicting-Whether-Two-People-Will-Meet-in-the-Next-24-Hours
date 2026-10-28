"""Public online-demo boundary: only pages that need no local data and start no server-side work."""

import os

import streamlit as st

# Home, Play, Explore, Research Hub directory and static source notes read only repository files.
DEMO_PAGES = frozenset({"pages/0_Overview.py", "pages/7_Data_Sources.py", "pages/12_Chance_Encounter.py",
                        "pages/13_Encounter_Insights.py", "pages/14_Research_Hub.py"})
SESSION_FLAG = "_encounter_demo_mode"
REPOSITORY = "https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/tree/research-v2.2"


def demo_requested():
    return st.session_state.get(SESSION_FLAG) is True or os.environ.get("ENCOUNTER_DEMO_MODE") == "1"


def render_unavailable(title):
    st.title(title)
    st.info("在线演示只开放首页、Play、Explore、科研中心目录和数据来源说明。下载、导入、训练和科研分析需要本地数据，"
            "也会在服务器上执行操作，因此只能在本地运行。")
    st.link_button("查看本地运行方法", REPOSITORY + "#快速开始")
