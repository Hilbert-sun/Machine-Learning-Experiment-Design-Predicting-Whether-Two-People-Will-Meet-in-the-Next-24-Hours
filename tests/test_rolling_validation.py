import numpy as np
import pandas as pd

from src.rolling_validation import ROLLING_PROTOCOL, fold_predictions, plan_folds, ranking_metrics, summarize
from src.window_features import WINDOW_FEATURES

DAY = 86400


def synthetic(days=range(7, 27), pairs=60):
    rng = np.random.default_rng(0)
    frame = pd.DataFrame([{"dataset_id": "copenhagen", "timestamp": d*DAY+28800, "user_min": i % 6 + 1, "user_max": i + 10,
                           "label_24h": int(i % 3 == 0)} for d in days for i in range(pairs)])
    bank = frame[["dataset_id", "timestamp", "user_min", "user_max"]].copy()
    for name in WINDOW_FEATURES:
        bank[name] = rng.random(len(frame))
    bank["pair_contact_bins"] = frame.label_24h*2 + rng.random(len(frame))
    return frame, {d: bank for d in (1, 3, 7)}


def test_fold_plan_purges_label_windows_and_needs_history():
    cohort, _ = synthetic()
    folds = plan_folds(cohort)
    ready = [f for f in folds if f["status"] == "ready"]
    assert [f["study_day"] for f in ready] == list(range(17, 28))
    for f in ready:
        assert max(f["train_times"]) + DAY < min(f["validation_times"])
        assert max(f["validation_times"]) + DAY < f["test_time"]
        assert len(f["validation_times"]) == 3 and len(f["train_times"]) >= 4
    assert all(f["status"] == "insufficient_history" for f in folds[:9])


def test_class_gate_marks_unbalanced_folds():
    cohort, _ = synthetic()
    cohort.loc[cohort.timestamp.eq(20*DAY+28800), "label_24h"] = 0
    status = {f["study_day"]: f["status"] for f in plan_folds(cohort)}
    assert status[21] == "insufficient_class_rows"


def test_ranking_metrics_hand_example():
    frame = pd.DataFrame({"timestamp": [0, 0, 0], "user_min": [1, 1, 2], "user_max": [2, 3, 3],
                          "label_24h": [1, 0, 0], "p": [0.2, 0.9, 0.1]})
    result = ranking_metrics(frame, "p", ks=(1, 2))
    # participant 1: [3(0), 2(1)]; participant 2: [1(1), 3(0)]; participant 3 has no positive.
    assert result["groups"] == 2 and result["groups_without_positive"] == 1
    assert result["precision_at_1"] == 0.5 and result["recall_at_2"] == 1.0
    np.testing.assert_allclose(result["ndcg_at_2"], (1/np.log2(3) + 1)/2)


def test_end_to_end_synthetic_rolling_summary_has_bootstrap_and_no_selection():
    cohort, banks = synthetic()
    predictions, records = fold_predictions(cohort, banks, plan_folds(cohort), progress=None)
    assert predictions.timestamp.nunique() == 11
    summary = summarize(predictions)
    assert len(summary["metrics"]) == 9
    xgb7 = next(c for c in summary["contrasts"] if c["contrast"] == "7d xgboost - 1d xgboost")
    assert xgb7["status"] == "paired_day_block_bootstrap" and len(xgb7["confidence_interval_95"]) == 2
    assert ROLLING_PROTOCOL["test_used_for_selection"] is False
    short = summarize(predictions.loc[predictions.timestamp.isin(sorted(predictions.timestamp.unique())[:5])])
    assert all(c["confidence_interval_95"] is None for c in short["contrasts"])
