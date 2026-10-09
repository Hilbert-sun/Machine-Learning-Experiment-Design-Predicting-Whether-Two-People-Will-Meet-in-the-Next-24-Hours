import streamlit as st

from src.ui import source_links

st.title("数据来源 · Data Sources")
source_links()
st.subheader("Copenhagen Networks Study")
st.markdown(
    "Piotr Sapiezynski、Arkadiusz Stopczynski、David Dreyer Lassen、Sune Lehmann（2019）。"
    "[数据 DOI](https://doi.org/10.6084/m9.figshare.7267433) · "
    "[论文](https://www.nature.com/articles/s41597-019-0325-x)。"
    "Figshare 数据页标注 MIT 许可；论文许可须按论文页面单独核对。"
)
st.write("手机蓝牙接近与通信元数据。相对时间不能伪造为日历日期；蓝牙强度不能直接转换为精确距离。")
st.caption("已核对源文件：bt_symmetric.csv 的 # timestamp/user_a/user_b/rssi；calls.csv 的 timestamp/caller/callee/duration；sms.csv 的 timestamp/sender/recipient。user_b=-1/-2 是扫描标记，电话 duration=-1 是未接来电。")
st.subheader("SocioPatterns High School")
st.markdown(
    "Rossana Mastrandrea、Julie Fournet、Alain Barrat（2015）。"
    "[论文与引用](https://doi.org/10.1371/journal.pone.0136497)。"
    "官方数据采用 CC BY-NC-SA 许可，须署名、限非商业用途并遵守相同方式共享要求。"
)
st.write("空白分隔的5个字段：UNIX秒时间、两名匿名参与者ID及其班级；20秒接触窗口。短期校园样本不能外推到多年人际关系。")
st.caption("实际文件结构由数据验证页面核对。本系统不包含真实身份或完整地理轨迹。")
