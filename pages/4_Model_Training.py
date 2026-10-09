import hashlib
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

from src.model_registry import BASELINES, MAIN_MODELS, ModelRegistry
from src.pipeline_cache import file_signatures
from src.temporal_split import TrainingDataError, chronological_split, prepare_cohort
from src.train import save_training_run, train_models
from src.training_data import available_training_inputs
from src.ui import dataset_picker

st.title("模型训练 · Model Training")
dataset = dataset_picker()
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "configs/default.yaml").read_text())
saved = ModelRegistry.list_saved(root / config["paths"]["models"])
if saved:
    with st.expander("已保存的模型版本"):
        st.dataframe(saved, hide_index=True, width="stretch")
inputs = available_training_inputs(root, config, dataset)
if not inputs:
    st.info("尚无匹配当前数据的标签/特征缓存。请在 Data Manager 完成预处理、标签及历史特征生成。")
    st.button("训练并保存模型", disabled=True)
    st.page_link("pages/1_Data_Manager.py", label="前往数据管理")
    st.stop()
chosen = st.selectbox("样本/特征缓存版本", range(len(inputs)), format_func=lambda i: f"{inputs[i].processed.report['source_file']} · 覆盖阈值 {inputs[i].labels.report['policy'].get('min_scan_coverage', 0.5):.0%} · {inputs[i].labels.path.stem[-8:]}")
selected = inputs[chosen]
try:
    with st.spinner("检查有效样本与时间切分…"):
        cohort = prepare_cohort(selected.labels, selected.features)
        settings = config.get("split", {})
        fractions = tuple(settings.get(name, default) for name, default in (("train_fraction", 0.6), ("validation_fraction", 0.2), ("test_fraction", 0.2)))
        split = chronological_split(cohort, fractions=fractions, horizon_hours=selected.labels.report["policy"]["horizon_hours"])
except (OSError, ValueError, KeyError) as exc:
    st.warning(str(exc))
    st.button("训练并保存模型", disabled=True)
    st.page_link("pages/1_Data_Manager.py", label="返回数据管理检查观测覆盖率")
    st.stop()

st.subheader("时间切分预览")
st.dataframe([{"集合": name, **summary} for name, summary in split.report["sets"].items()], hide_index=True, width="stretch")
st.caption(f"按有效预测时点 {'/'.join(f'{fraction:.0%}' for fraction in fractions)} 的配置比例切分；已排除 {split.report['excluded_rows']:,} 个不可靠目标，清除 {split.report['purged_rows']:,} 个跨边界样本。时间为研究相对秒。测试集不参与参数、阈值或校准选择。")
mode = st.selectbox("训练模式", ["选择模型", "Run All Baselines", "Compare All Models"])
names = list(BASELINES) if mode == "Run All Baselines" else list(ModelRegistry.names()) if mode == "Compare All Models" else st.multiselect("模型", ModelRegistry.names(), default=["logistic_regression"])
seed = int(st.number_input("随机种子", min_value=0, max_value=2**31 - 1, value=int(config.get("training", {}).get("random_seed", 42))))
trees = int(st.number_input("树模型迭代数", min_value=10, max_value=500, value=100, step=10))
small_grid = st.checkbox("比较两组树模型迭代数（验证集 Log Loss 选择）")
calibration = st.selectbox("概率校准", ["sigmoid", "isotonic", "none"])
history_window = st.selectbox("模型历史特征最长窗口（天）", [1, 3, 7, 14], index=3)
st.caption("只保留所选窗口以内的历史特征组；超出该窗口的最近接触间隔设为未知。完全不可用的训练列移除；插补和标准化仅在训练段拟合。启用校准时，验证集前段校准、后段选择参数/阈值并比较可靠性，中间隔离24小时标签窗口。")
identity = {"inputs": file_signatures([selected.labels.path, selected.features.path]), "models": names, "seed": seed,
            "trees": trees, "grid": small_grid, "calibration": calibration, "fractions": fractions, "history_window": history_window}
state_key = "training_" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
if st.button("训练并保存模型", disabled=not names):
    bar = st.progress(0.0, text="准备训练…")
    try:
        options = {name: {"n_estimators": trees} for name in names if name in (*MAIN_MODELS, "random_forest")}
        grids = {name: {"n_estimators": [max(5, trees // 2), trees]} for name in options} if small_grid else None
        run = train_models(split, names, seed=seed, parameters=options, parameter_grids=grids,
                           calibration=None if calibration == "none" else calibration, feature_window_days=history_window,
                           progress=lambda done, total, name: bar.progress(done / total, text=f"训练 {name} · {done}/{total}"))
        record, path = save_training_run(run, root / config["paths"]["models"], root / config["paths"]["reports"],
                                         provenance={"dataset": dataset, "source_file": selected.processed.report["source_file"],
                                                     "processed_cache_version": selected.processed.directory.name,
                                                     "source_kind": selected.labels.report.get("source_kind", "official_dataset_cache"),
                                                     "input_signatures": identity["inputs"], "label_policy": selected.labels.report["policy"],
                                                     "feature_policy": selected.features.report})
        st.session_state[state_key] = (record, str(path))
        bar.progress(1.0, text="训练与模型保存完成")
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        st.error(f"训练失败：{exc}。请检查有效类别、验证时长和参数后重试；不会自动放宽覆盖率或时间隔离。")

if state_key in st.session_state:
    record, path = st.session_state[state_key]
    st.success(f"已训练并保存 {len(record['models'])} 个模型。实验版本：{record['run_version']}")
    st.caption(f"实验报告：{path}；以下为训练/验证结果，测试集尚未评估。")
    st.dataframe([{"模型": name, **summary["validation"], "duration_seconds": summary["duration_seconds"]} for name, summary in record["models"].items()], hide_index=True, width="stretch")
    for name, summary in record["models"].items():
        if "calibration" in summary:
            details = summary["calibration"]
            with st.expander(f"{name} · 校准前后比较（后段验证集）"):
                st.dataframe([{"阶段": stage, "Brier Score": details[stage]["brier_score"], "Log Loss": details[stage]["log_loss"]} for stage in ("before", "after")], hide_index=True)
                figure = go.Figure()
                for stage in ("before", "after"):
                    points = details[f"reliability_{stage}"]
                    figure.add_scatter(x=[point["mean_probability"] for point in points], y=[point["observed_fraction"] for point in points], mode="lines+markers", name=stage)
                figure.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line={"dash": "dash"}, name="理想校准线")
                figure.update_layout(title=f"{name} · 后段验证集可靠性图", xaxis_title="平均预测概率", yaxis_title="实际正例比例")
                st.plotly_chart(figure, width="stretch", key=f"calibration_{name}")
