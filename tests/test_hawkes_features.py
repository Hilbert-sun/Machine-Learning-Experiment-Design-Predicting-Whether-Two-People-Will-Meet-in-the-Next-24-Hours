import numpy as np
import pandas as pd

from src.hawkes_features import HAWKES_COLUMNS, fit_predict, fold_predictions
from src.window_features import WINDOW_FEATURES

DAY = 86400


def frame(days=range(7, 27), pairs=60):
    rng = np.random.default_rng(1)
    rows = pd.DataFrame([{"dataset_id": "copenhagen", "timestamp": d*DAY+28800, "user_min": 1, "user_max": i + 2,
                          "label_24h": int(i % 3 == 0)} for d in days for i in range(pairs)])
    for name in WINDOW_FEATURES:
        rows[name] = rng.random(len(rows))
    rows["rssi_mean"] = np.nan
    for name in HAWKES_COLUMNS:
        rows[name] = rows.label_24h*0.6 + rng.random(len(rows))*0.4
    return rows


def test_fit_drops_train_all_null_columns_and_uses_hawkes_signal():
    rows = frame()
    train, validation, test = (rows.loc[rows.timestamp.lt(17*DAY)], rows.loc[rows.timestamp.between(17*DAY, 20*DAY)],
                               rows.loc[rows.timestamp.gt(22*DAY)])
    p, threshold, columns = fit_predict(train, validation, test, list(WINDOW_FEATURES) + HAWKES_COLUMNS)
    assert "rssi_mean" not in columns and set(HAWKES_COLUMNS) <= set(columns)
    assert 0 < threshold < 1 and p[test.label_24h.eq(1).to_numpy()].mean() > p[test.label_24h.eq(0).to_numpy()].mean()


def test_fold_predictions_only_cover_evaluated_test_times():
    rows = frame()
    times = sorted(rows.timestamp.unique())
    folds = [{"status": "evaluated", "study_day": 20, "train_times": times[:5], "validation_times": times[6:9], "test_time": times[10]},
             {"status": "insufficient_history", "study_day": 9}]
    out = fold_predictions(rows, folds, list(WINDOW_FEATURES) + HAWKES_COLUMNS, progress=None)
    assert out.timestamp.eq(times[10]).all() and len(out) == 60
    assert out.threshold_7d_xgboost_hawkes.nunique() == 1
