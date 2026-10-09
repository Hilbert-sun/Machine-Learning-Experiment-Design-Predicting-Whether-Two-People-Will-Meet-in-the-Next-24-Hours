"""Frozen evaluation, native SHAP and validation-only experiments on synthetic fixtures."""

import json
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from src.experiments import evaluate_saved_run, evaluation_figures, export_evaluation, run_ablation_experiments, save_evaluation, evaluate_model
from src.explain import native_tree_shap
from src.feature_engineering import FEATURE_NAMES
from src.model_registry import ModelRegistry
from src.pipeline_cache import file_signatures
from src.temporal_split import TrainingDataError, chronological_split, prepare_cohort
from src.train import save_training_run, train_models
from test_leakage import artifacts, synthetic_frame


def saved_fixture(tmp_path, *, communications=False, names=None):
    frame = synthetic_frame()
    if communications:
        frame["sms_count_7d"] = frame.contact_count_1d + 1
        frame["call_count_7d"] = frame.contact_count_1d
    labels, features = artifacts(tmp_path, frame)
    split = chronological_split(prepare_cohort(labels, features))
    run = train_models(split, names or ["logistic_regression", "xgboost", "lightgbm"], calibration="sigmoid", parameters={"random_forest": {"n_estimators": 5}, "xgboost": {"n_estimators": 5}, "lightgbm": {"n_estimators": 5}})
    policy = {"communications_enabled": communications, "communication_availability_reference": "synthetic past-availability convention" if communications else None}
    _, path = save_training_run(run, tmp_path / "models", tmp_path / "reports", provenance={
        "dataset": "Copenhagen", "source_kind": "synthetic_test_fixture", "input_signatures": file_signatures([labels.path, features.path]),
        "label_policy": {"horizon_hours": 24, "min_scan_coverage": 0.5}, "feature_policy": policy,
    })
    return path, split, run


def test_frozen_test_evaluation_has_curves_counts_and_no_retraining(tmp_path, monkeypatch):
    path, split, _ = saved_fixture(tmp_path)
    monkeypatch.setattr("src.experiments.train_models", lambda *a, **k: pytest.fail("test evaluation retrained models"))
    report = evaluate_saved_run(path, evaluation_set="test", explain_limit=7)
    assert report["scope"]["rows"] == len(split.test)
    assert report["test_used_for_selection"] is False
    for summary in report["models"].values():
        assert np.asarray(summary["curves"]["confusion_matrix"]).sum() == len(split.test)
        assert summary["curves"]["roc"] and summary["curves"]["pr"]
        assert sum(group["rows"] for group in summary["frequency_groups"]) == len(split.test)
        assert 0 <= summary["metrics"]["calibration_error_ece"] <= 1
    for name in ("xgboost", "lightgbm"):
        shap = report["models"][name]["explanation"]["shap"]
        assert shap["status"] == "available" and shap["rows_explained"] == 7
        assert shap["scale"] == "base_model_raw_margin"
    assert report["models"]["logistic_regression"]["explanation"]["shap"]["status"] == "not_available"


@pytest.mark.parametrize("name", ["xgboost", "lightgbm"])
def test_native_shap_sums_to_raw_base_margin(tmp_path, name):
    _, split, run = saved_fixture(tmp_path)
    values = native_tree_shap(run.models[name], split.validation.loc[:, FEATURE_NAMES])
    np.testing.assert_allclose(values["values"].sum(axis=1) + values["bias"], values["raw_margin"], atol=1e-4)


def test_validation_window_ablation_and_unavailable_communication_are_honest(tmp_path):
    path, _, _ = saved_fixture(tmp_path)
    experiments = run_ablation_experiments(path, model_name="logistic_regression")
    assert [item["window_days"] for item in experiments["E2"]["windows"]] == [1, 3, 7, 14]
    assert experiments["E2"]["scope"] == "validation_only"
    assert experiments["E3"]["status"] == "not_available"
    assert "with" not in experiments["E3"]
    report = evaluate_saved_run(path)
    report["experiments"].update({name: experiments[name] for name in ("E2", "E3")})
    assert "Historical Window Ablation" in evaluation_figures(report, "logistic_regression")
    csv, _ = export_evaluation(report)
    rows = pd.read_csv(BytesIO(csv), encoding="utf-8-sig")
    assert rows.record_type.eq("window_ablation").sum() == 4
    unavailable = rows.loc[rows.record_type.eq("experiment_unavailable")]
    assert len(unavailable) == 1 and unavailable.log_loss.isna().all()
    assert experiments["test_used_for_selection"] is False


def test_communication_ablation_requires_explicit_verified_availability(tmp_path):
    path, _, _ = saved_fixture(tmp_path, communications=True)
    assert run_ablation_experiments(path)["E3"]["status"] == "not_available"
    experiment = run_ablation_experiments(path, communications_verified=True)["E3"]
    assert experiment["status"] == "available"
    assert experiment["with"]["rows"] == experiment["without"]["rows"]


def test_csv_html_exports_are_standalone_and_keep_fixture_provenance(tmp_path):
    path, _, _ = saved_fixture(tmp_path)
    report = evaluate_saved_run(path)
    csv, html = export_evaluation(report)
    assert "synthetic_test_fixture" in csv.decode("utf-8-sig")
    assert b"synthetic_test_fixture" in html and b"plotly.js" in html
    assert b"Confusion Matrix" in html and b"Native TreeSHAP" in html
    outputs = save_evaluation(report, tmp_path / "exports")
    assert all(output.is_file() for output in outputs.values())
    assert json.loads(outputs["json"].read_text())["evaluation_set"] == "validation"


def test_input_signature_changes_reject_old_experiment_reconstruction(tmp_path):
    path, _, _ = saved_fixture(tmp_path)
    record = json.loads(path.read_text())
    labels_path = record["provenance"]["input_signatures"][0]["path"]
    frame = pd.read_parquet(labels_path)
    frame["label_24h"] = 1 - frame.label_24h
    frame.to_parquet(labels_path, index=False)
    with pytest.raises(TrainingDataError, match="签名已改变"):
        evaluate_saved_run(path)


def test_one_class_targets_do_not_fabricate_roc_auc(tmp_path):
    _, split, run = saved_fixture(tmp_path)
    summary = evaluate_model(run.models["logistic_regression"], split.test.assign(label_24h=0))
    assert summary["metrics"]["roc_auc"] is None
    assert summary["curves"]["roc"] is None
    assert summary["curves"]["pr"] is None
    assert summary["metrics"]["pr_auc_average_precision"] is None


def test_full_baseline_and_main_model_comparison_uses_one_frozen_cohort(tmp_path):
    path, _, _ = saved_fixture(tmp_path, names=ModelRegistry.names())
    report = evaluate_saved_run(path)
    assert set(report["models"]) == set(ModelRegistry.names())
    assert report["experiments"]["E1"]["missing_baselines"] == []
    assert all(summary["metrics"]["rows"] == report["scope"]["rows"] for summary in report["models"].values())
