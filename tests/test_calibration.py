"""Synthetic-only calibration, persistence and untouched-test integration checks."""

import json

import numpy as np
import pytest

from src.feature_engineering import FEATURE_NAMES
from src.model_registry import ModelRegistry
from src.predict import predict_probabilities
from src.temporal_split import TrainingDataError, chronological_split
from src.train import save_training_run, train_models
from test_leakage import synthetic_frame


@pytest.mark.parametrize("method", ["sigmoid", "isotonic"])
@pytest.mark.parametrize("name", ["logistic_regression", "xgboost", "lightgbm"])
def test_calibrated_pipeline_roundtrip_preserves_probabilities_and_threshold(tmp_path, name, method):
    split = chronological_split(synthetic_frame())
    run = train_models(split, [name], calibration=method, parameters={name: {"n_estimators": 10}} if name in {"xgboost", "lightgbm"} else None)
    model = run.models[name]
    saved = ModelRegistry.save(model, tmp_path, metadata={"source_kind": "synthetic_test_fixture"})
    X = split.validation.loc[:, FEATURE_NAMES]
    np.testing.assert_allclose(predict_probabilities(saved, X), model.predict_proba(X)[:, 1])
    np.testing.assert_array_equal(ModelRegistry.load(saved).predict(X), model.predict(X))
    summary = run.report["models"][name]["calibration"]
    assert summary["evaluation_scope"] == "later_validation_only"
    assert summary["before"]["rows"] == summary["after"]["rows"] < len(split.validation)
    assert summary["reliability_before"] and summary["reliability_after"]
    assert run.report["validation_partition"]["purged_rows"] > 0
    assert ModelRegistry.list_saved(tmp_path)[0]["model_name"] == name


def test_calibration_and_threshold_ignore_test_labels():
    split = chronological_split(synthetic_frame())
    first = train_models(split, ["logistic_regression"], calibration="sigmoid")
    split.test["label_24h"] = 1 - split.test.label_24h
    second = train_models(split, ["logistic_regression"], calibration="sigmoid")
    X = split.validation.loc[:, FEATURE_NAMES]
    np.testing.assert_allclose(first.models["logistic_regression"].predict_proba(X), second.models["logistic_regression"].predict_proba(X))
    assert first.models["logistic_regression"].threshold == second.models["logistic_regression"].threshold
    assert first.report["test_evaluated"] is False


def test_corrupt_model_is_rejected_before_loading(tmp_path):
    run = train_models(chronological_split(synthetic_frame()), ["constant"])
    saved = ModelRegistry.save(run.models["constant"], tmp_path)
    with (saved / "model.joblib").open("ab") as handle:
        handle.write(b"corrupt")
    with pytest.raises(TrainingDataError, match="校验失败"):
        ModelRegistry.load(saved)


def test_complete_run_persists_real_config_and_explicit_fixture_provenance(tmp_path):
    run = train_models(chronological_split(synthetic_frame()), ["constant", "random_forest"], parameters={"random_forest": {"n_estimators": 10}})
    record, path = save_training_run(run, tmp_path / "models", tmp_path / "reports", provenance={"source_kind": "synthetic_test_fixture"})
    assert json.loads(path.read_text())["provenance"]["source_kind"] == "synthetic_test_fixture"
    assert len(record["saved_models"]) == 2 and record["test_evaluated"] is False
    assert all(ModelRegistry.load(folder) for folder in record["saved_models"].values())


def test_insufficient_calibration_period_is_not_silently_reused_for_tuning():
    with pytest.raises(TrainingDataError, match="校准"):
        train_models(chronological_split(synthetic_frame(20)), ["logistic_regression"], calibration="sigmoid")


def test_all_seven_calibrated_models_can_save_reload_and_predict(tmp_path):
    names = ModelRegistry.names()
    parameters = {name: {"n_estimators": 5} for name in ("random_forest", "xgboost", "lightgbm")}
    split = chronological_split(synthetic_frame())
    run = train_models(split, names, parameters=parameters, calibration="sigmoid")
    record, _ = save_training_run(run, tmp_path / "models", tmp_path / "reports", provenance={"source_kind": "synthetic_test_fixture"})
    X = split.validation.loc[:, FEATURE_NAMES]
    assert len(record["saved_models"]) == 7
    for name, directory in record["saved_models"].items():
        restored = ModelRegistry.load(directory)
        np.testing.assert_allclose(restored.predict_proba(X), run.models[name].predict_proba(X))
        assert restored.threshold == run.models[name].threshold
