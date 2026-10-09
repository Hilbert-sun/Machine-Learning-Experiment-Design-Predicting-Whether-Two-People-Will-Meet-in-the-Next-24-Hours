import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.experiments import comparison_table, evaluate_saved_run, evaluation_figures, run_ablation_experiments, save_evaluation
from src.pipeline_cache import file_signatures
from src.ui import dataset_picker

st.title("模型评估 · Model Evaluation")
dataset = dataset_picker()
root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "configs/default.yaml").read_text())
reports_directory = root / config["paths"]["reports"]
records = {}
for path in sorted(reports_directory.glob("training-*.json")):
    try:
        record = json.loads(path.read_text())
        if record.get("provenance", {}).get("dataset") == dataset:
            records[path] = record
    except (OSError, ValueError):
        continue
if not records:
    st.info("尚无该数据集的已保存训练实验。有效样本不足时不能生成模型性能或消融分数。")
    st.page_link("pages/4_Model_Training.py", label="前往模型训练")
    st.stop()
report_path = st.selectbox("已保存实验", list(records), format_func=lambda path: records[path]["run_version"])
record = records[report_path]
if record["provenance"].get("source_kind") == "synthetic_test_fixture":
    st.warning("该实验来自合成测试数据，仅验证功能；下列结果不是实际研究性能。")
scope_label = st.radio("评估范围", ["validation（模型选择结果）", "test（冻结模型的最终报告）"])
evaluation_set = "test" if scope_label.startswith("test") else "validation"
st.caption("只加载冻结模型与阈值。测试集不重新训练、调参或选择历史窗口；消融只在验证集比较。PR-AUC采用Average Precision，单类目标的ROC-AUC显示不可用。")
try:
    dependencies = [report_path] + [item["path"] for item in record["provenance"]["input_signatures"]]
    for directory in record["saved_models"].values():
        dependencies.extend([Path(directory) / "manifest.json", Path(directory) / "model.joblib"])
    state_key = "evaluation_" + hashlib.sha256(json.dumps({"files": file_signatures(dependencies), "scope": evaluation_set}, sort_keys=True).encode()).hexdigest()
except (OSError, KeyError, ValueError) as exc:
    st.error(f"实验文件缺失或不可用：{exc}。请恢复原实验版本，不能替换成不匹配的数据。")
    st.stop()
if st.button("计算冻结模型评估"):
    try:
        with st.spinner("检查原始切分并计算冻结模型指标…"):
            result = evaluate_saved_run(report_path, evaluation_set=evaluation_set)
            outputs = save_evaluation(result, reports_directory)
        st.session_state[state_key] = (result, outputs)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        st.error(f"评估失败：{exc}")
if state_key not in st.session_state:
    st.info("选择范围后计算评估。没有计算结果时不显示占位指标。")
    st.stop()
result, outputs = st.session_state[state_key]
st.caption(f"{dataset} · {evaluation_set} · {result['scope']['rows']:,} 个可靠目标 · Study Day {result['scope']['first_timestamp']//86400+1}–{result['scope']['last_timestamp']//86400+1}")
st.dataframe(comparison_table(result), hide_index=True, width="stretch")
if result["experiments"]["E1"]["missing_baselines"]:
    st.info("该保存实验没有包含全部Baseline；表格仅列出实际训练的模型。完整比较请先运行Compare All Models。")
name = st.selectbox("模型详情", list(result["models"]))
summary = result["models"][name]
if summary["curves"]["roc"] is None:
    st.info("该范围只有一种目标类别，ROC曲线与ROC-AUC不可计算。")
if summary["curves"]["pr"] is None:
    st.info("该范围没有正例，PR曲线与Average Precision不可计算，未生成占位曲线。")
main_figures = {title: figure for title, figure in evaluation_figures(result, name).items() if title != "Historical Window Ablation"}
for index, figure in enumerate(main_figures.values()):
    if index % 2 == 0:
        columns = st.columns(2)
    with columns[index % 2]:
        st.plotly_chart(figure, width="stretch", key=f"evaluation_plot_{index}")
st.caption(f"特征重要性方法：{summary['explanation']['importance_method']}；不表示因果作用。")
shap = summary["explanation"]["shap"]
if shap["status"] == "available":
    st.caption(f"TreeSHAP解释前{shap['rows_explained']}条按时间排序的评估记录；指标使用全部记录。贡献属于基模型原始分数，不是校准后概率。")
else:
    st.info("此模型没有原生TreeSHAP，未将其他解释方法标成SHAP。")
st.subheader("E4 · 历史低频配对分组")
st.dataframe(summary["frequency_groups"], hide_index=True, width="stretch")
st.subheader("E5 · 校准前后概率分数")
st.dataframe([{"阶段": stage, "Brier Score": summary["calibration_comparison"][stage]["brier_score"], "Log Loss": summary["calibration_comparison"][stage]["log_loss"]} for stage in ("before", "after")], hide_index=True)
st.subheader("E2/E3 · 验证集消融")
if evaluation_set == "test":
    st.info("最终测试报告不运行参数/窗口/通讯消融；请使用验证集实验结果确定配置。")
if st.button("运行验证集消融实验（固定已选参数）", disabled=evaluation_set == "test"):
    bar = st.progress(0.0, text="准备消融实验…")
    try:
        policy = record["provenance"].get("feature_policy", {})
        experiments = run_ablation_experiments(report_path, model_name=name,
                    communications_verified=bool(policy.get("communications_enabled") and policy.get("communication_availability_reference")),
                    progress=lambda done, total, window: bar.progress(done / total, text=f"历史窗口 {window} · {done}/{total}"))
        result["experiments"].update({key: experiments[key] for key in ("E2", "E3")})
        outputs = save_evaluation(result, reports_directory)
        st.session_state[state_key] = (result, outputs)
        st.success("验证集消融完成并保存；测试集未用于选择。")
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        st.error(f"消融失败：{exc}")
if "E2" in result["experiments"]:
    st.dataframe(result["experiments"]["E2"]["windows"], hide_index=True)
    ablation_model = result["experiments"]["E2"]["model"]
    st.plotly_chart(evaluation_figures(result, ablation_model)["Historical Window Ablation"], width="stretch", key="history_ablation_curve")
    e3 = result["experiments"]["E3"]
    if e3["status"] == "not_available":
        st.info("E3通讯消融不可运行：通讯可用时间未验证或特征未启用；不生成虚构分数。")
    else:
        st.dataframe([{"通讯特征": variant, **e3[variant]} for variant in ("with", "without")], hide_index=True)
st.download_button("下载实验结果 CSV", outputs["csv"].read_bytes(), file_name=outputs["csv"].name, mime="text/csv")
st.download_button("下载独立 HTML 报告", outputs["html"].read_bytes(), file_name=outputs["html"].name, mime="text/html")
