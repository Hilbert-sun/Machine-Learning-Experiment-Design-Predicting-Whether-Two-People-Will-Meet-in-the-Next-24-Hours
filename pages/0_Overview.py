"""Public landing page: no data/model discovery or research computation."""
import streamlit as st

st.title("Encounter Lab · 相遇实验室")
st.header("世界这么大，明天我们会不会刚好遇见？")
st.write("用过去的信息，探索未来24小时偶然相遇的趣味倾向。")
for column, (name, description, label, path, primary) in zip(st.columns(3), (
    ("✨ Play", "回答几个简单问题，看看你和TA的趣味偶遇指数。", "开始偶遇预测", "pages/12_Chance_Encounter.py", True),
    ("🔎 Explore", "看懂偶遇线索、关系图谱和真实研究数据。", "探索相遇的规律", "pages/13_Encounter_Insights.py", False),
    ("🔬 Research", "查看机器学习、数据处理、模型实验和研究报告。", "进入科研中心", "pages/14_Research_Hub.py", False),
)):
    with column:
        with st.container(border=True):
            st.subheader(name)
            st.write(description)
            if st.button(label, type="primary" if primary else "secondary", width="stretch"):
                st.switch_page(path)
st.caption("约一分钟开始探索 · 无需登录 · 趣味问卷与匿名设备科研实验独立")
