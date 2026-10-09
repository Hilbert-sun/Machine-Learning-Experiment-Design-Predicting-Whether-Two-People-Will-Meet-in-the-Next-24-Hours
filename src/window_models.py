"""Bounded research input contract using existing registry estimators and persistence."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.model_registry import ModelRegistry
from src.temporal_split import TrainingDataError
from src.window_features import WINDOW_FEATURES


@dataclass
class WindowModel:
    name: str
    estimator: object
    parameters: dict
    seed: int
    feature_window_days: int
    feature_columns: list = field(default_factory=list)
    feature_reference: dict = field(default_factory=dict)
    threshold: float = 0.5
    fitted: bool = False
    feature_contract: str = "bounded_window_v1"

    def checked(self, X):
        if set(X.columns) != set(WINDOW_FEATURES) or X.attrs.get("history_window_days") != self.feature_window_days:
            raise TrainingDataError("Bounded window feature contract/window mismatch; keys, future fields and legacy banks are forbidden.")
        frame = X.apply(pd.to_numeric, errors="raise")
        if np.isinf(frame.to_numpy(dtype=float)).any():
            raise TrainingDataError("Infinite historical features.")
        return frame

    def fit(self, X, y):
        X = self.checked(X)
        y = np.asarray(y)
        if len(X) != len(y) or not len(y) or not np.isin(y, [0, 1]).all():
            raise TrainingDataError("Aligned known binary training labels required.")
        self.feature_columns = [name for name in WINDOW_FEATURES if X[name].notna().any()]
        self.feature_reference = {name: float(X[name].median()) for name in self.feature_columns}
        self.estimator.fit(X.loc[:, self.feature_columns], y)
        self.fitted = True
        return self

    def predict_proba(self, X):
        if not self.fitted:
            raise TrainingDataError("Model is not fitted.")
        X = self.checked(X)
        probabilities = np.asarray(self.estimator.predict_proba(X.loc[:, self.feature_columns]), dtype=float)
        if probabilities.shape != (len(X), 2) or not np.isfinite(probabilities).all() or ((probabilities < 0)|(probabilities > 1)).any() or not np.allclose(probabilities.sum(axis=1), 1):
            raise TrainingDataError("Invalid binary probabilities.")
        return probabilities

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= self.threshold).astype("int8")


def create_window_model(name, *, days, seed, parameters=None):
    original = ModelRegistry.create(name, seed=seed, parameters=parameters)
    return WindowModel(name, original.estimator, original.parameters, seed, days)
