"""Algorithm verification uses synthetic samples, never real research metrics."""

import numpy as np
import pandas as pd
import pytest

from src.baselines import ConstantProbability, HistoricalPairFrequency
from src.feature_engineering import FEATURE_NAMES
from src.model_registry import BASELINES, ModelRegistry
from src.temporal_split import TrainingDataError, chronological_split
from src.train import train_models
from test_leakage import synthetic_frame


@pytest.mark.parametrize("name", BASELINES)
def test_each_baseline_runs_with_valid_probabilities_and_validation_metrics(name):
    split = chronological_split(synthetic_frame())
    run = train_models(split, [name], parameters={"random_forest": {"n_estimators": 10}})
    model = run.models[name]
    p = model.predict_proba(split.validation.loc[:, FEATURE_NAMES])
    assert p.shape == (len(split.validation), 2)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    assert run.report["models"][name]["validation"]["rows"] == len(split.validation)
    assert run.report["test_evaluated"] is False
    assert "relative_weekday" not in model.feature_columns


def test_constant_prior_and_unavailable_historical_probability_fallback():
    X = pd.DataFrame({"historical_contact_probability": [np.nan, 0.9, 0.1]})
    y = [0, 0, 1]
    constant = ConstantProbability().fit(X, y)
    history = HistoricalPairFrequency().fit(X, y)
    assert constant.predict_proba(X)[:, 1].tolist() == [1 / 3] * 3
    assert history.predict_proba(X)[:, 1].tolist() == [1 / 3, 0.9, 0.1]


def test_changing_test_targets_does_not_change_model_or_threshold():
    split = chronological_split(synthetic_frame())
    original = train_models(split, ["logistic_regression"])
    split.test["label_24h"] = 1 - split.test.label_24h
    changed = train_models(split, ["logistic_regression"])
    X = split.validation.loc[:, FEATURE_NAMES]
    np.testing.assert_allclose(original.models["logistic_regression"].predict_proba(X), changed.models["logistic_regression"].predict_proba(X))
    assert original.models["logistic_regression"].threshold == changed.models["logistic_regression"].threshold


def test_future_fields_and_single_class_training_refused():
    X = synthetic_frame().loc[:, FEATURE_NAMES].copy()
    X["label_24h"] = 1
    with pytest.raises(TrainingDataError, match="白名单"):
        ModelRegistry.create("logistic_regression").fit(X, np.zeros(len(X)))
    split = chronological_split(synthetic_frame())
    split.train["label_24h"] = 0
    with pytest.raises(TrainingDataError, match="正负两类"):
        train_models(split, ["logistic_regression"])
