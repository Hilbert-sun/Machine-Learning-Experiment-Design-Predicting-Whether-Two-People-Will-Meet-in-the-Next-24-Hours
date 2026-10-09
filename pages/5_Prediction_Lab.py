import streamlit as st

from src.ui import empty_page

st.warning("本系统预测匿名设备的近距离接触概率，不预测爱情、友谊或命运。")
empty_page("预测实验室 · Prediction Lab", "尚无已训练模型。完成模型训练后，才能计算配对未来24小时的接触概率。")
