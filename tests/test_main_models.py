"""Synthetic fixtures exercise both native CPU boosters and validation-only search."""

import numpy as np
import pytest

from src.feature_engineering import FEATURE_NAMES
from src.model_registry import MAIN_MODELS
from src.temporal_split import TrainingDataError, chronological_split
from src.train import train_models
from test_leakage import synthetic_frame


@pytest.mark.parametrize("name", MAIN_MODELS)
def test_main_model_native_training_and_probabilities(name):
    split = chronological_split(synthetic_frame())
    run = train_models(split, [name], parameters={name: {"n_estimators": 10, "max_depth": 2}})
    model = run.models[name]
    probabilities = model.predict_proba(split.validation.loc[:, FEATURE_NAMES])
    assert probabilities.shape == (len(split.validation), 2)
    assert np.isfinite(probabilities).all() and np.allclose(probabilities.sum(axis=1), 1)
    assert run.report["models"][name]["parameters"]["random_state"] == 42
    assert run.report["test_evaluated"] is False


@pytest.mark.parametrize("name", MAIN_MODELS)
def test_grid_selection_is_reproducible_and_ignores_test_targets(name):
    split = chronological_split(synthetic_frame())
    arguments = {"parameter_grids": {name: {"n_estimators": [5, 10], "max_depth": [2]}}}
    first = train_models(split, [name], **arguments)
    split.test["label_24h"] = 1 - split.test.label_24h
    second = train_models(split, [name], **arguments)
    report = first.report["models"][name]
    assert len(report["trials"]) == 2
    assert report["validation"]["log_loss"] == min(trial["validation"]["log_loss"] for trial in report["trials"])
    assert report["parameters"] == second.report["models"][name]["parameters"]
    X = split.validation.loc[:, FEATURE_NAMES]
    np.testing.assert_allclose(first.models[name].predict_proba(X), second.models[name].predict_proba(X))


def test_native_model_errors_have_actionable_context():
    with pytest.raises(TrainingDataError, match="lightgbm 训练/校准失败"):
        train_models(chronological_split(synthetic_frame()), ["lightgbm"], parameters={"lightgbm": {"num_leaves": 1}})
