import streamlit as st

st.title("Encounter Lab · 相遇实验室")
st.caption("Can We Predict When Two People Meet Again?")
st.info("尚未加载并验证数据。请从数据管理开始；模型和实验结果将在实际运行后展示。")

metrics = (
    ("参与者", "有效匿名参与者数量"),
    ("接触事件", "经过验证的接触事件行数"),
    ("有效配对", "清洗后的无向配对数量"),
    ("观测天数", "数据覆盖的研究天数"),
    ("正例占比", "可评估样本中未来24小时发生接触的比例"),
    ("当前模型", "已经训练并加载的模型"),
)
for offset in (0, 3):
    for column, (label, explanation) in zip(st.columns(3), metrics[offset : offset + 3]):
        column.metric(label, "—", help=explanation)

st.subheader("开始研究")
for column, (path, label) in zip(
    st.columns(4),
    (
        ("pages/1_Data_Manager.py", "加载数据"),
        ("pages/2_Data_Explorer.py", "探索数据"),
        ("pages/4_Model_Training.py", "训练模型"),
        ("pages/5_Prediction_Lab.py", "打开 Prediction Lab"),
    ),
):
    with column:
        st.page_link(path, label=label)
st.caption("时间轴使用 Study Day；无观测不代表无接触。")
