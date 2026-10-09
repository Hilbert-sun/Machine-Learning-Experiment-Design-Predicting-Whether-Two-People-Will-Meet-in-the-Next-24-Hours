import hashlib
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from src.loader import source_kind, supported_files
from src.model_registry import ModelRegistry
from src.pipeline_cache import file_signatures
from src.predict import historical_pairs, model_information_deadline, predict_pair
from src.preprocessing import cached_dataset
from src.ui import dataset_picker

st.warning("本系统预测匿名设备的近距离接触概率，不预测爱情、友谊或命运。")
st.title("预测实验室 · Prediction Lab")
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "configs/default.yaml").read_text())
saved = ModelRegistry.list_saved(root / config["paths"]["models"])
if not saved:
    st.info("尚无已训练模型。完成可靠数据准备及模型训练后，才能计算接触概率。")
    st.page_link("pages/4_Model_Training.py", label="前往模型训练")
    st.stop()
dataset = dataset_picker()
window = st.selectbox("Historical Window（模型历史窗口，天）", [1, 3, 7, 14], index=3)
models = []
for item in saved:
    manifest = json.loads((Path(item["path"]) / "manifest.json").read_text())
    if manifest["metadata"].get("provenance", {}).get("dataset") == dataset and (manifest.get("feature_window_days") or 14) == window:
        models.append((item, manifest))
if not models:
    st.info("当前数据集/历史窗口没有匹配的模型，请先训练对应窗口的模型。")
    st.page_link("pages/4_Model_Training.py", label="前往模型训练")
    st.stop()
model_index = st.selectbox("Model", range(len(models)), format_func=lambda i: f"{models[i][0]['model_name']} · {models[i][0]['version']}")
item, manifest = models[model_index]
if manifest.get("feature_window_days") is None:
    st.caption("该模型使用原完整1/3/7/14天特征组；最近接触间隔来自全部已知历史，14天同时用于历史展示范围。")
raw = root / config["paths"]["raw_copenhagen" if dataset == "Copenhagen" else "raw_sociopatterns"]
available = {}
for path in supported_files(raw, dataset):
    if source_kind(path, dataset) in {"bluetooth", "proximity"}:
        processed = cached_dataset(path, dataset, root / config["paths"]["processed"])
        if processed:
            available[path.name] = processed
if not available:
    st.info("缺少匹配当前源文件的清洗缓存，请返回 Data Manager 处理数据。")
    st.page_link("pages/1_Data_Manager.py", label="前往数据管理")
    st.stop()
source = st.selectbox("主接触文件", list(available)) if len(available) > 1 else next(iter(available))
processed = available[source]
try:
    deadline = model_information_deadline(manifest)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
last_day = (processed.report["source_timestamp_max"] - processed.report["time_origin_seconds"]) // 86400 + 1
default_day = max(last_day + 1, deadline // 86400 + 2)
day = int(st.number_input("Prediction Day · Study Day", min_value=1, max_value=default_day + 7, value=default_day))
hour = int(st.number_input("Prediction Hour", min_value=0, max_value=23, value=8))
t = (day - 1) * 86400 + hour * 3600
mode = st.radio("模式", ["未来实验（隐藏真实结果）", "历史回测（仅显式读取实际结果）"])
past_pairs = historical_pairs(processed, t)
if not past_pairs:
    st.info("该预测时点之前没有可用于Known Pair模式的历史配对。")
    st.stop()
people = sorted({user for pair in past_pairs for user in pair})
a = st.selectbox("Person A", people)
b = st.selectbox("Person B（仅过去有接触的配对）", sorted({right if left == a else left for left, right in past_pairs if a in (left, right)}))
st.caption(f"{dataset} · {source} · Study Day {day:02d} {hour:02d}:00 · 窗口{window}天 · 模型{item['version']}。模型必须在该时点之前已完成训练、校准及选择。")
if manifest["metadata"].get("provenance", {}).get("source_kind") == "synthetic_test_fixture":
    st.warning("当前模型来自合成测试数据，仅用于功能验证，不代表真实研究结果。")
query = {"model": item["version"], "checksum": manifest["sha256"], "inputs": file_signatures([processed.directory / "contacts.parquet", processed.directory / "observations.parquet"]), "time": t, "pair": sorted((a, b)), "window": window, "mode": mode}
result_key = "prediction_" + hashlib.sha256(json.dumps(query, sort_keys=True).encode()).hexdigest()
if st.button("Predict Encounter"):
    try:
        with st.spinner("计算历史特征与模型概率…"):
            result = predict_pair(processed, item["path"], t, a, b, window_days=window, backtest=mode.startswith("历史"))
        st.session_state[result_key] = result
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        st.error(f"无法预测：{exc}")
if result_key in st.session_state:
    result = st.session_state[result_key]
    st.metric("未来24小时内发生近距离接触的模型概率", f"{result['probability']:.1%}")
    st.caption("以上为所选已训练模型的实际计算结果；概率不是命运或交谈的保证。")
    cols = st.columns(3)
    cols[0].metric("所选窗口历史接触记录", result["historical_contact_count"])
    cols[1].metric("距最近历史接触（小时）", f"{result['time_since_last_contact']/3600:.1f}")
    cols[2].metric("预测分布熵（0–1）", f"{result['prediction_entropy']:.3f}")
    st.caption("分布熵只是模型概率的数学不确定性指标，不是经过验证的置信区间。")
    st.plotly_chart(px.line(pd.DataFrame(result["trend"]), x="study_day", y="contact_records", markers=True,
                            title=f"配对 {min(a,b)}–{max(a,b)} · 预测前{window}天记录趋势", labels={"study_day": "Study Day", "contact_records": "接触记录数"}), width="stretch")
    explanation = result["explanation"]
    st.caption("原生TreeSHAP解释基模型的原始分数，不是校准后概率的可加总贡献。" if explanation["method"] == "native_tree_shap" else "单特征替换为训练中位数的概率敏感度：不是SHAP，也不是因果解释。")
    if explanation["rows"]:
        st.dataframe(explanation["rows"], hide_index=True)
    if "actual_outcome" in result:
        st.info(f"Actual Outcome: {result['actual_outcome']['outcome']} · {result['actual_outcome']['reason']}")
