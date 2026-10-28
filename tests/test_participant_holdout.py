import numpy as np
import pandas as pd

import src.participant_holdout as holdout
from src.window_features import WINDOW_FEATURES

DAY = 86400


def synthetic(days=range(7, 27), participants=90):
    rng = np.random.default_rng(3)
    pairs = [(a, b) for a in range(participants) for b in range(a + 1, participants) if (a + b) % 9 == 0]
    rows = pd.DataFrame([{"dataset_id": "copenhagen", "timestamp": d*DAY+28800, "user_min": a, "user_max": b,
                          "label_24h": int((a*b + d) % 3 == 0)} for d in days for a, b in pairs])
    bank = rows[holdout.KEYS].copy()
    for name in WINDOW_FEATURES:
        bank[name] = rng.random(len(rows))
    return rows, bank


def test_partition_is_deterministic_balanced_and_salted():
    people = range(500)
    groups = [holdout.group_of(p, 0) for p in people]
    assert groups == [holdout.group_of(p, 0) for p in people]
    assert 200 < sum(groups) < 300
    assert groups != [holdout.group_of(p, 1) for p in people]


def test_held_out_people_never_reach_training_or_thresholds(monkeypatch):
    rows, bank = synthetic()
    seen_people = []
    original = holdout.fit_window
    def spy(bank_, train, validation, days):
        seen_people.extend(pd.concat([train, validation])[["user_min", "user_max"]].to_numpy().ravel())
        return original(bank_, train, validation, days)
    monkeypatch.setattr(holdout, "fit_window", spy)
    times = sorted(rows.timestamp.unique())
    folds = [{"status": "evaluated", "study_day": 20, "train_times": times[:6], "validation_times": times[7:10], "test_time": times[11]}]
    out, records = holdout.holdout_predictions(rows, bank, folds, salt=0, progress=None)
    assert records[0]["status"] == "evaluated"
    assert all(holdout.group_of(p, 0) == 0 for p in seen_people)
    both = out.loc[out.population.eq("unseen_both")]
    assert all(holdout.group_of(p, 0) == 1 for p in both[["user_min", "user_max"]].to_numpy().ravel())
    one = out.loc[out.population.eq("unseen_one")]
    assert all({holdout.group_of(a, 0), holdout.group_of(b, 0)} == {0, 1} for a, b in one[["user_min", "user_max"]].to_numpy())
    assert out.timestamp.eq(times[11]).all() and {"p_7d_xgboost_holdout", "threshold_7d_xgboost_holdout"} <= set(out.columns)


def test_fold_gate_drops_folds_without_class_support():
    rows, bank = synthetic()
    times = sorted(rows.timestamp.unique())
    rows.loc[rows.timestamp.eq(times[11]), "label_24h"] = 0
    folds = [{"status": "evaluated", "study_day": 20, "train_times": times[:6], "validation_times": times[7:10], "test_time": times[11]},
             {"status": "evaluated", "study_day": 21, "train_times": times[:7], "validation_times": times[8:11], "test_time": times[12]}]
    out, records = holdout.holdout_predictions(rows, bank, folds, salt=0, progress=None)
    assert [r["status"] for r in records] == ["insufficient_class_rows", "evaluated"]
    assert out.timestamp.eq(times[12]).all()
