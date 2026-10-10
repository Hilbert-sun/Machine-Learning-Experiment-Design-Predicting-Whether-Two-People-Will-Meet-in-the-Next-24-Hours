from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.window_ui import StudySettings, study_key, run_study, study_figures, export_study

st.title("历史窗口研究 · History Window Study")
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root/"configs/default.yaml").read_text())
st.warning("预测匿名设备未来24小时接近事件；T17已看过重叠日期，本研究不是全新独立外部验证。")
st.subheader("Experiment Setup")
from src.dataset_catalog import sources
dataset = st.selectbox("Dataset",["Copenhagen","SocioPatterns"]+[s["name"] for s in sources(root) if s["dataset_id"] not in {"copenhagen","highschool2013"}])
candidate = st.selectbox("Candidate Policy",["shared_1d","expanded_7d_counts_only"])
coverage = st.select_slider("Coverage Threshold",options=[0.25,0.5,0.75],value=0.5)
windows = st.multiselect("Compare Windows",[1,3,7],default=[1,3,7])
model = st.selectbox("Model",["xgboost","historical_frequency","logistic_regression"])
seed = st.number_input("Seed",min_value=0,max_value=2147483647,value=42,step=1)
calibrate = st.checkbox("Calibrate",value=False)
settings = StudySettings(dataset,candidate,float(coverage),tuple(sorted(windows)),model,int(seed),calibrate)
key = study_key(root,config,settings)
st.caption("默认配置读取冻结测试报告；改变配置的新作业仅评估validation。扫描跨度完整不等于设备持续在线。")
if st.button("Run Study"):
    bar = st.progress(0.0,text="准备实际研究作业")
    try:
        result = run_study(root,config,settings,progress=lambda value,message:bar.progress(value,text=message))
        st.session_state['window_study_result'] = (study_key(root,config,settings),result)
        key = study_key(root,config,settings)
    except (ValueError,OSError,KeyError,RuntimeError,AssertionError) as exc:
        st.error(f"研究作业无法完成：{exc}")
        st.session_state.pop('window_study_result',None)
state = st.session_state.get('window_study_result')
if not state or state[0]!=key:
    st.info("尚未运行当前数据/策略/参数的离线研究。Case Explorer可独立使用已保存模型。")
else:
    result = state[1]
    if result['source_kind']=='synthetic_test_fixture': st.warning("合成测试数据，仅功能验证，不是研究证据。")
    st.caption(f"Run {result['run_id']} · {result['scope']}")
    if result['calibration_method'] is None: st.info("无已校准模型："+result['calibration_reason'])
    st.subheader("Cohort Audit")
    audit = result['cohort']
    st.write("统一要求完整7天历史跨度；共同1天历史候选集；未来覆盖不足保留未知并排除。")
    st.dataframe(pd.DataFrame(audit['daily_filter_funnel']),hide_index=True)
    st.json({'sets':audit['support']['sets'],'purged_by_day':audit['purged_by_day']})
    st.subheader("Window Comparison")
    st.dataframe(pd.DataFrame(result['metrics']),hide_index=True)
    st.metric("评估样本正例比例",f"{result['metrics'][0]['positive_rate']:.2%}")
    for figure in study_figures(result).values(): st.plotly_chart(figure,width="stretch")
    if 'paired_uncertainty' in result: st.json([r for r in result['paired_uncertainty'] if r['model']==model])
    if 'candidate_expansion' in result:
        with st.expander("7d候选池扩展：独立覆盖范围，不能解释为纯窗口效应"):
            st.json(result['candidate_expansion'])
    csv,json_bytes,html = export_study(result)
    st.download_button("Download CSV",csv,file_name="window_study.csv",mime="text/csv")
    st.download_button("Download JSON",json_bytes,file_name="window_study.json",mime="application/json")
    st.download_button("Download HTML",html,file_name="window_study.html",mime="text/html")

# T28: independent inference remains accessible without running an offline study.
from src.asof_ui import render_as_of_cases
render_as_of_cases(root,config,dataset)
