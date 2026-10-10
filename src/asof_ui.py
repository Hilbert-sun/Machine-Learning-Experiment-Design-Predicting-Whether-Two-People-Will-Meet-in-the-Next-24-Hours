"""Case Explorer bridge to independent T28 APIs; old offline routines remain frozen."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.asof_inference import MODES, NAMESPACES, as_of_candidates, read_model_contract
from src.preprocessing import cached_dataset
from src.window_ui import location, source_path
from src.safe_cache import cached_json
from src.time_machine import make_prediction, reveal_prediction


def available_models(root, config, dataset):
    """Only model/time metadata is consulted; evaluation samples/banks are not opened."""
    root = Path(root)
    reports = location(root, config, "reports")/"window_study"
    records = list(reports.glob("*/T21_RESULTS.json")) + list(reports.glob("*/T22_RESULTS.json"))
    records += list((reports/"ui_jobs").glob("*/result.json"))
    rows = []
    for path in sorted(records):
        record = cached_json(path)
        mapping = record.get("model_artifacts", record.get("models", {}))
        for window, models in mapping.items():
            for name, directory in models.items():
                candidate_paths = [(parent/Path(directory)).resolve() for parent in (root, *path.resolve().parents)]
                directory = next((p for p in candidate_paths if (p/"manifest.json").is_file()), candidate_paths[0])
                try:
                    contract = read_model_contract(directory, evidence_path=path)
                except (ValueError, OSError, KeyError):
                    continue  # Missing provenance is never turned into an early guessed deadline.
                if contract.dataset_id == NAMESPACES.get(dataset):
                    rows.append({"window": int(window), "model": name, "run_id": record["run_id"],
                                 "directory": str(directory), "evidence_path": str(path), "deadline": contract.information_deadline,
                                 "dataset_id": contract.dataset_id})
    return rows


def render_as_of_cases(root, config, dataset):
    st.subheader("Case Explorer · As-of-time")
    st.caption("候选仅由[t-1d,t)接触生成；不使用离线评估cohort或未来覆盖筛选后的特征库。")
    if dataset not in NAMESPACES:
        st.info("该来源尚无已核验的有界历史推理契约。")
        return
    source = source_path(root, config, dataset)
    if not source.is_file():
        st.info("推理需要本地已验证的接触/扫描快照；请先在Data Manager准备数据。")
        return
    processed = cached_dataset(source, dataset, location(root, config, "processed"))
    if processed is None:
        st.info("缺少与当前来源匹配的已验证接触/观测缓存；请先运行预处理。")
        return
    rows = available_models(root, config, dataset)
    if not rows:
        st.info("尚无包含可核实数据集、窗口和标签信息截止时间的推理模型。")
        return
    groups = sorted({(r["run_id"], r["model"]) for r in rows}, key=lambda key: (key[1] != "xgboost", key))
    group = st.selectbox("As-of saved model family", groups, format_func=lambda key: f"{key[1]} · {key[0]}")
    choices = {r["window"]: r for r in rows if (r["run_id"], r["model"]) == group}
    windows = st.multiselect("As-of History Windows", sorted(choices), default=sorted(choices))
    mode = st.radio("Inference Mode", MODES)
    deadline = max(r["deadline"] for r in choices.values())
    day = st.number_input("Prediction Study Day (as-of)", min_value=1, value=deadline//86400+2, step=1)
    hour = st.number_input("Prediction Hour (as-of)", min_value=0, max_value=23, value=8, step=1)
    t = (int(day)-1)*86400 + int(hour)*3600
    if mode == "prospective_inference":
        st.info("当前静态归档没有核实的UTC观测时间锚点，不能称作实时未来预测。实时API还要求两端近期的t前扫描证据。")
    if not windows or t <= max(choices[w]["deadline"] for w in windows):
        st.info("请选择窗口和严格晚于模型训练/验证/阈值标签信息截止时间的预测时点。")
        return
    try:
        keys = as_of_candidates(processed, t, dataset_id=NAMESPACES[dataset])
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        return
    st.caption(f"As-of候选：{len(keys):,} 对；未使用t及以后扫描信息。")
    if keys.empty:
        st.info("该时点前24小时没有已观测接触候选。")
        return
    a = st.selectbox("Person A", sorted(keys.user_min.unique()))
    b = st.selectbox("Person B", sorted(keys.loc[keys.user_min.eq(a), "user_max"].unique()))
    backtest = st.checkbox("历史回测：独立揭晓实际结果", value=False) if mode == "historical_blind_replay" else False
    if st.button("Compare Case"):
        try:
            # Reuse the verified common coverage policy and pinned multi-model snapshot.
            # No future evidence is read until the explicit backtest branch below.
            prediction = make_prediction(processed, {w: choices[w] for w in windows}, t, int(a), int(b), mode=mode)
            cases = prediction["cases"]
            for w, case in cases.items():
                st.metric(f"{w}d历史 ·未来24h接近概率 · {mode}", f"{case['probability']:.2%}")
            st.dataframe(pd.DataFrame({w: case["historical_features"] for w, case in cases.items()}).T)
            if backtest:
                outcome = reveal_prediction(processed, prediction)
                st.write("Actual Outcome:", outcome["outcome"])
                st.caption(outcome["reason"])
        except (ValueError, OSError, KeyError, RuntimeError) as exc:
            st.error(str(exc))
