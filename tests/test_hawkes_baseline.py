import numpy as np
import pandas as pd

from src.hawkes_baseline import fit_pair, forecast, half_life_beta, hawkes_scores, select_per_fold

DAY = 86400


def test_poisson_history_recovers_rate_without_excitation():
    events = np.arange(0.5, 168, 1.0)  # perfectly regular: no clustering
    mu, alpha = fit_pair(events, 168.0, half_life_beta(2))
    assert abs(mu - 1.0) < 0.1 and alpha < 0.1


def test_recent_burst_raises_short_horizon_forecast_more_than_old_burst():
    beta = half_life_beta(8)
    recent = np.concatenate([[1.0, 50.0], 160 + np.arange(0, 6, 0.1)])
    old = np.concatenate([[1.0, 50.0], 10 + np.arange(0, 6, 0.1)])
    assert forecast(recent, 168.0, beta) > forecast(old, 168.0, beta)
    assert 0 <= forecast(old, 168.0, beta) <= 1


def test_scores_only_read_strict_past_contacts(tmp_path):
    t = 10*DAY
    contacts = pd.DataFrame({"timestamp": [t-3600, t-7200, t, t+600, t-8*DAY], "user_min": [1]*5, "user_max": [2]*5})
    contacts.to_parquet(tmp_path/"contacts.parquet", index=False)
    rows = pd.DataFrame({"dataset_id": ["copenhagen"], "timestamp": [t], "user_min": [1], "user_max": [2]})
    first = hawkes_scores(tmp_path/"contacts.parquet", rows, grid=[2], progress=None)
    # Future (>= t) and outside-window events must not change the score.
    contacts.iloc[:2].to_parquet(tmp_path/"contacts.parquet", index=False)
    second = hawkes_scores(tmp_path/"contacts.parquet", rows, grid=[2], progress=None)
    np.testing.assert_allclose(first.hawkes_2h, second.hawkes_2h)


def test_half_life_is_selected_on_validation_only():
    keys = [{"dataset_id": "copenhagen", "timestamp": t, "user_min": 1, "user_max": i + 2} for t in (1, 2, 3) for i in range(20)]
    scores = pd.DataFrame(keys)
    labels = scores.assign(label_24h=[i % 2 for i in range(60)])
    good = labels.label_24h*0.8 + 0.1
    # 2h ranks validation (t=1) perfectly; 8h ranks only the test day (t=3) perfectly.
    scores["hawkes_2h"] = np.where(scores.timestamp.eq(1), good, 0.5)
    scores["hawkes_8h"] = np.where(scores.timestamp.eq(3), good, 1 - good)
    folds = [{"status": "evaluated", "study_day": 1, "validation_times": [1], "test_time": 3}]
    test, selections = select_per_fold(scores, labels, folds, grid=[2, 8])
    assert selections[0]["selected_half_life_hours"] == 2
    assert test.timestamp.eq(3).all() and test.p_7d_hawkes.eq(0.5).all()
