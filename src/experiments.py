"""Frozen-model evaluation and validation-only experiments with honest availability."""

import hashlib
import html
import json
from pathlib import Path
import tempfile
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve

from src.calibration import reliability_points
from src.evaluate import binary_metrics
from src.explain import native_tree_shap
from src.feature_engineering import FEATURE_NAMES
from src.model_registry import BASELINES, ModelRegistry
from src.pipeline_cache import PipelineArtifact, file_signatures
from src.temporal_split import TrainingDataError, chronological_split, prepare_cohort, validation_partition
from src.train import train_models


def _ece(y, probabilities, bins=10):
    groups = np.minimum((np.asarray(probabilities) * bins).astype(int), bins - 1)
    return float(sum(np.sum(groups == index) / len(y) * abs(np.mean(probabilities[groups == index]) - np.mean(y[groups == index]))
                     for index in np.unique(groups)))


def feature_explanation(model, X, *, limit=200):
    base = getattr(model, "base", model)
    sample = X.head(limit)
    pipeline = base.estimator
    importance = []
    if hasattr(pipeline, "named_steps"):
        classifier = pipeline.named_steps["classifier"]
        names = list(pipeline[:-1].get_feature_names_out())
        values = getattr(classifier, "feature_importances_", None)
        method = "native_feature_importance"
        if values is None and hasattr(classifier, "coef_"):
            values, method = np.abs(classifier.coef_[0]), "absolute_standardized_coefficient"
        if values is not None:
            importance = [{"feature": str(name), "importance": float(value)} for name, value in zip(names, values)]
    else:
        method = "rule_model_no_generic_native_importance"
    native = native_tree_shap(model, sample)
    shap = {"status": "not_available", "reason": "Native TreeSHAP is available for XGBoost/LightGBM; other model types do not claim SHAP values."}
    if native is not None:
        shap = {"status": "available", "method": "native_tree_shap", "scale": native["scale"], "rows_explained": len(sample),
                "selection": f"first {len(sample)} chronological evaluation rows; metrics use all evaluation rows",
                "mean_absolute_values": [{"feature": str(name), "importance": float(value)} for name, value in zip(native["feature_names"], np.abs(native["values"]).mean(axis=0))]}
    return {"importance_method": method, "feature_importance": sorted(importance, key=lambda item: -item["importance"]), "shap": shap}


def evaluate_model(model, frame, *, explain_limit=200):
    X, y = frame.loc[:, FEATURE_NAMES], frame.label_24h.to_numpy(dtype=int)
    probabilities = model.predict_proba(X)[:, 1]
    pr = None
    if y.any():
        precision, recall, _ = precision_recall_curve(y, probabilities)
        pr = {"precision": precision.tolist(), "recall": recall.tolist()}
    curves = {"pr": pr, "roc": None,
              "calibration": reliability_points(y, probabilities),
              "confusion_matrix": confusion_matrix(y, probabilities >= model.threshold, labels=[0, 1]).tolist()}
    if len(np.unique(y)) == 2:
        fpr, tpr, _ = roc_curve(y, probabilities)
        curves["roc"] = {"fpr": fpr.tolist(), "tpr": tpr.tolist()}
    metrics = binary_metrics(y, probabilities, threshold=model.threshold)
    metrics["calibration_error_ece"] = _ece(y, probabilities)
    counts = frame.contact_count_7d.to_numpy(dtype=float)
    names = np.where(np.isnan(counts), "unknown", np.where(counts <= 1, "0–1", np.where(counts <= 5, "2–5", np.where(counts <= 20, "6–20", ">20"))))
    groups = [{"historical_contact_records_7d": name, **binary_metrics(y[names == name], probabilities[names == name], threshold=model.threshold)} for name in sorted(set(names))]
    base = getattr(model, "base", model)
    before = base.predict_proba(X)[:, 1]
    calibration = {"method": getattr(model, "method", None), "before": binary_metrics(y, before), "after": metrics,
                   "reliability_before": reliability_points(y, before), "reliability_after": curves["calibration"]}
    return {"metrics": metrics, "curves": curves, "frequency_groups": groups, "calibration_comparison": calibration,
            "explanation": feature_explanation(model, X, limit=explain_limit)}


def _run_inputs(record):
    signatures = record["provenance"]["input_signatures"]
    if len(signatures) != 2 or file_signatures([item["path"] for item in signatures]) != signatures:
        raise TrainingDataError("实验输入签名已改变或缺失，不能用不同数据重建旧模型的测试集。")
    label_path, feature_path = (Path(item["path"]) for item in signatures)
    labels = PipelineArtifact(label_path, {"policy": record["provenance"]["label_policy"]}, True)
    features = PipelineArtifact(feature_path, record["provenance"].get("feature_policy", {}), True)
    return labels, features


def saved_run_split(record):
    labels, features = _run_inputs(record)
    cohort = prepare_cohort(labels, features)
    split = chronological_split(cohort, fractions=record["split"]["requested_fractions"], horizon_hours=record["split"]["horizon_hours"])
    if split.report != record["split"]:
        raise TrainingDataError("重建时间切分与原训练报告不一致。")
    return split


def evaluate_saved_run(report_path, *, evaluation_set="validation", explain_limit=200):
    if evaluation_set not in {"validation", "test"}:
        raise ValueError("评估范围只能为validation或test。")
    record = json.loads(Path(report_path).read_text())
    split = saved_run_split(record)
    frame = split.test if evaluation_set == "test" else validation_partition(split.validation)[1] if record["calibration_method"] else split.validation
    summaries, signatures = {}, {}
    for name, directory in record["saved_models"].items():
        manifest = json.loads((Path(directory) / "manifest.json").read_text())
        if manifest["metadata"].get("provenance", {}).get("input_signatures") != record["provenance"]["input_signatures"]:
            raise TrainingDataError("保存模型与实验报告的数据版本不一致。")
        model = ModelRegistry.load(directory)
        if model.threshold != record["models"][name]["threshold"]:
            raise TrainingDataError("模型阈值与冻结的验证结果不一致。")
        summaries[name] = evaluate_model(model, frame, explain_limit=explain_limit)
        signatures[name] = {"version": manifest["version"], "sha256": manifest["sha256"]}
    return {"run_version": record["run_version"], "evaluation_set": evaluation_set,
            "scope": {"rows": len(frame), "first_timestamp": int(frame.timestamp.min()), "last_timestamp": int(frame.timestamp.max())},
            "models": summaries, "model_versions": signatures, "provenance": record["provenance"], "split": split.report,
            "selection_policy": "Frozen models/thresholds; no fit or parameter selection during evaluation.",
            "experiments": {"E1": {"status": "available", "missing_baselines": [name for name in BASELINES if name not in summaries]},
                            "E4": {"status": "available", "group_definition": "historical 7d contact record counts, never future counts"},
                            "E5": {"status": "available", "scope": evaluation_set}},
            "test_used_for_selection": False}


def run_ablation_experiments(report_path, *, model_name=None, communications_verified=False, progress=None):
    """E2/E3 always retrain on train and compare on validation; never use test scores."""
    record = json.loads(Path(report_path).read_text())
    split = saved_run_split(record)
    name = model_name or next(iter(record["models"]))
    if name not in record["models"]:
        raise ValueError("消融模型必须来自该已保存实验。")
    parameters = {key: value for key, value in record["models"][name]["parameters"].items() if key not in {"random_state", "n_jobs"}}
    arguments = {"seed": record["seed"], "parameters": {name: parameters}, "calibration": record["calibration_method"]}
    windows = []
    for index, days in enumerate((1, 3, 7, 14)):
        if progress:
            progress(index, 4, days)
        run = train_models(split, [name], feature_window_days=days, **arguments)
        windows.append({"window_days": days, "model": name, **run.report["models"][name]["validation"]})
    e3 = {"status": "not_available", "model": name, "reason": "Communication availability is unverified/disabled; no scores were fabricated."}
    if progress:
        progress(4, 4, "complete")
    policy = record["provenance"].get("feature_policy", {})
    if communications_verified and policy.get("communications_enabled") and policy.get("communication_availability_reference"):
        if not split.train[["sms_count_7d", "call_count_7d"]].notna().all().all():
            raise TrainingDataError("经验证通讯特征在训练段仍有不可用值，不能声称完成通讯对比。")
        with_communications = train_models(split, [name], feature_window_days=14, **arguments)
        without = type(split)(*(part.assign(sms_count_7d=np.nan, call_count_7d=np.nan) for part in (split.train, split.validation, split.test)), split.report)
        without_communications = train_models(without, [name], feature_window_days=14, **arguments)
        e3 = {"status": "available", "model": name, "with": with_communications.report["models"][name]["validation"],
              "without": without_communications.report["models"][name]["validation"], "availability_reference": policy["communication_availability_reference"]}
    return {"E2": {"status": "available", "scope": "validation_only", "model": name, "fixed_hyperparameters": parameters, "windows": windows}, "E3": e3,
            "test_used_for_selection": False, "run_version": record["run_version"]}


def evaluation_figures(report, model_name):
    summary = report["models"][model_name]
    curves = summary["curves"]
    source = "synthetic fixture · " if report["provenance"].get("source_kind") == "synthetic_test_fixture" else ""
    scope = f"{source}{report['provenance'].get('dataset', 'unknown')} · {model_name} · {report['evaluation_set']} · {report['scope']['rows']} samples · Study Day {report['scope']['first_timestamp']//86400+1}–{report['scope']['last_timestamp']//86400+1}"
    figures = {"Confusion Matrix": go.Figure(go.Heatmap(z=curves["confusion_matrix"], x=["Predicted0", "Predicted1"], y=["Actual0", "Actual1"], text=curves["confusion_matrix"], texttemplate="%{text}")),
               "Calibration Curve": go.Figure()}
    if curves["pr"]:
        figures["PR Curve"] = go.Figure(go.Scatter(x=curves["pr"]["recall"], y=curves["pr"]["precision"], mode="lines"))
    if curves["roc"]:
        figures["ROC Curve"] = go.Figure(go.Scatter(x=curves["roc"]["fpr"], y=curves["roc"]["tpr"], mode="lines"))
    for stage in ("before", "after"):
        points = summary["calibration_comparison"][f"reliability_{stage}"]
        figures["Calibration Curve"].add_scatter(x=[point["mean_probability"] for point in points], y=[point["observed_fraction"] for point in points], mode="lines+markers", name=stage)
    figures["Calibration Curve"].add_scatter(x=[0, 1], y=[0, 1], mode="lines", line={"dash": "dash"}, name="ideal")
    explanation = summary["explanation"]
    for title, rows in (("Feature Importance", explanation["feature_importance"]), ("Native TreeSHAP", explanation["shap"].get("mean_absolute_values", []))):
        if rows:
            ranked = sorted(rows, key=lambda row: -row["importance"])[:20]
            figures[title] = go.Figure(go.Bar(x=[row["feature"] for row in ranked], y=[row["importance"] for row in ranked]))
    if "PR Curve" in figures:
        figures["PR Curve"].update_layout(xaxis_title="Recall", yaxis_title="Precision")
    if "ROC Curve" in figures:
        figures["ROC Curve"].update_layout(xaxis_title="False Positive Rate", yaxis_title="True Positive Rate")
    figures["Calibration Curve"].update_layout(xaxis_title="Mean predicted probability", yaxis_title="Observed positive fraction")
    for title, figure in figures.items():
        figure.update_layout(title=f"{title}<br><sup>{scope}</sup>")
    window_experiment = report["experiments"].get("E2", {})
    if window_experiment.get("status") == "available" and window_experiment["model"] == model_name:
        points = window_experiment["windows"]
        figures["Historical Window Ablation"] = go.Figure()
        for metric in ("pr_auc_average_precision", "brier_score"):
            figures["Historical Window Ablation"].add_scatter(x=[point["window_days"] for point in points], y=[point[metric] for point in points], mode="lines+markers", name=metric)
        figures["Historical Window Ablation"].update_layout(title=f"{source}{report['provenance'].get('dataset', 'unknown')} · {model_name} · 历史窗口特征消融 · validation only", xaxis_title="Maximum history days", yaxis_title="Validation metric")
    return figures


def comparison_table(report):
    return pd.DataFrame([{"model": name, "kind": "baseline" if name in BASELINES else "main", "dataset": report["provenance"].get("dataset"),
                          "source_kind": report["provenance"].get("source_kind", "unspecified"), "evaluation_set": report["evaluation_set"], **summary["metrics"]}
                         for name, summary in report["models"].items()])


def export_evaluation(report):
    records = [{"record_type": "model_metrics", **row} for row in comparison_table(report).to_dict(orient="records")]
    shared = {"dataset": report["provenance"].get("dataset"), "source_kind": report["provenance"].get("source_kind", "unspecified"), "evaluation_set": report["evaluation_set"]}
    for name, summary in report["models"].items():
        records.extend({"record_type": "frequency_group", "model": name, **shared, **row} for row in summary["frequency_groups"])
        records.extend({"record_type": f"calibration_{stage}", "model": name, **shared, **summary["calibration_comparison"][stage]} for stage in ("before", "after"))
        records.extend({"record_type": "feature_importance", "model": name, **shared, **row} for row in summary["explanation"]["feature_importance"])
        shap = summary["explanation"]["shap"]
        records.extend({"record_type": "native_tree_shap_mean_absolute", "model": name, **shared, "scale": shap.get("scale"), "rows_explained": shap.get("rows_explained"), **row} for row in shap.get("mean_absolute_values", []))
    if "E2" in report["experiments"]:
        records.extend({"record_type": "window_ablation", **shared, "evaluation_set": "validation", **row} for row in report["experiments"]["E2"]["windows"])
    if "E3" in report["experiments"]:
        e3 = report["experiments"]["E3"]
        if e3["status"] == "available":
            records.extend({"record_type": "communication_ablation", "model": e3["model"], **shared, "evaluation_set": "validation", "communications": stage, **e3[stage]} for stage in ("with", "without"))
        else:
            records.append({"record_type": "experiment_unavailable", "model": e3["model"], **shared, "experiment": "E3", "reason": e3["reason"]})
    csv = pd.DataFrame(records).to_csv(index=False).encode("utf-8-sig")
    fragments = ["<!doctype html><html><head><meta charset='utf-8'><title>Encounter Lab evaluation</title></head><body><h1>Encounter Lab evaluation</h1>",
                 "<p>Data source: " + html.escape(report["provenance"].get("source_kind", "unspecified")) + "</p>",
                 comparison_table(report).to_html(index=False, escape=True), "<pre>" + html.escape(json.dumps({key: report[key] for key in ("run_version", "evaluation_set", "scope", "selection_policy", "model_versions", "experiments")}, ensure_ascii=False, indent=2)) + "</pre>"]
    include_js = True
    for name in report["models"]:
        fragments.append("<h2>" + html.escape(name) + "</h2>")
        fragments.append(pd.DataFrame(report["models"][name]["frequency_groups"]).to_html(index=False, escape=True))
        fragments.append(pd.DataFrame([{"stage": stage, **report["models"][name]["calibration_comparison"][stage]} for stage in ("before", "after")]).to_html(index=False, escape=True))
        for figure in evaluation_figures(report, name).values():
            fragments.append(figure.to_html(full_html=False, include_plotlyjs=include_js))
            include_js = False
    fragments.append("</body></html>")
    return csv, "".join(fragments).encode("utf-8")


def save_evaluation(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    key = hashlib.sha256(payload).hexdigest()[:16]
    csv, html_bytes = export_evaluation(report)
    with tempfile.TemporaryDirectory(prefix=".evaluation-", dir=directory) as temporary:
        outputs = {}
        for suffix, content in (("csv", csv), ("html", html_bytes), ("json", payload)):
            staged = Path(temporary) / f"report.{suffix}"
            staged.write_bytes(content)
            destination = directory / f"evaluation-{key}.{suffix}"
            os.replace(staged, destination)
            outputs[suffix] = destination
    return outputs
