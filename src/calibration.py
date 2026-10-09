"""Frozen-base probability calibration on early validation, never train/test labels."""

from dataclasses import dataclass

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from src.temporal_split import TrainingDataError


def _log_odds(probabilities):
    clipped = np.clip(probabilities, 1e-7, 1 - 1e-7)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


@dataclass
class CalibratedModel:
    base: object
    calibrator: object
    method: str
    threshold: float = 0.5

    @property
    def name(self):
        return self.base.name

    @property
    def parameters(self):
        return self.base.parameters

    @property
    def seed(self):
        return self.base.seed

    @property
    def feature_columns(self):
        return self.base.feature_columns

    @property
    def feature_window_days(self):
        return self.base.feature_window_days

    def predict_proba(self, X):
        raw = self.base.predict_proba(X)[:, 1]
        probabilities = self.calibrator.predict_proba(_log_odds(raw))[:, 1] if self.method == "sigmoid" else self.calibrator.predict(raw)
        return np.column_stack([1 - probabilities, probabilities])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= self.threshold).astype("int8")


def calibrate_model(model, X, y, *, method="sigmoid"):
    if len(np.unique(y)) != 2:
        raise TrainingDataError("校准段必须包含正负两类可靠标签；增加有效校准样本或明确禁用校准。")
    probabilities = model.predict_proba(X)[:, 1]
    if method == "sigmoid":
        estimator = LogisticRegression(random_state=model.seed).fit(_log_odds(probabilities), y)
    elif method == "isotonic":
        estimator = IsotonicRegression(out_of_bounds="clip").fit(probabilities, y)
    else:
        raise TrainingDataError("校准方法必须为sigmoid或isotonic。")
    return CalibratedModel(model, estimator, method)


def reliability_points(y, probabilities):
    observed, predicted = calibration_curve(y, probabilities, n_bins=10, strategy="uniform")
    return [{"mean_probability": float(p), "observed_fraction": float(y)} for p, y in zip(predicted, observed)]
