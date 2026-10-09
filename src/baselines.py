"""B0–B2 probability baselines using train labels and prediction-time history only."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin


def _probabilities(values):
    values = np.asarray(values, dtype=float)
    return np.column_stack([1 - values, values])


class ConstantProbability(ClassifierMixin, BaseEstimator):
    def fit(self, X, y):
        self.prior_ = float(np.mean(y))
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        return _probabilities(np.full(len(X), self.prior_))


class HistoricalPairFrequency(ConstantProbability):
    def predict_proba(self, X):
        values = X.get("historical_contact_probability", pd.Series(np.nan, index=X.index))
        return _probabilities(values.fillna(self.prior_).clip(0, 1))


class TimeBasedRule(ConstantProbability):
    """Train-smoothed rates by historical recency bucket and prediction hour."""

    def __init__(self, alpha=1.0):
        self.alpha = alpha

    @staticmethod
    def _keys(X):
        recency = X.get("time_since_last_contact", pd.Series(np.nan, index=X.index)).to_numpy(dtype=float)
        hours = X.get("prediction_hour", pd.Series(np.nan, index=X.index)).to_numpy(dtype=float)
        buckets = np.digitize(recency, [86400, 3 * 86400, 7 * 86400], right=True)
        return [(int(hour) if np.isfinite(hour) else -1, int(bucket) if np.isfinite(age) else -1)
                for hour, bucket, age in zip(hours, buckets, recency)]

    def fit(self, X, y):
        if self.alpha < 0:
            raise ValueError("平滑系数不能为负。")
        super().fit(X, y)
        rates = {}
        for key, label in zip(self._keys(X), y):
            positive, count = rates.get(key, (0, 0))
            rates[key] = (positive + int(label), count + 1)
        self.rates_ = {key: (positive + self.alpha * self.prior_) / (count + self.alpha) for key, (positive, count) in rates.items()}
        return self

    def predict_proba(self, X):
        return _probabilities([self.rates_.get(key, self.prior_) for key in self._keys(X)])
