import numpy as np
import pandas as pd

from src.day_analysis import DESCRIPTORS, MODELS, correlations, day_table

DAY = 86400


def frame(days=(16, 17, 18)):
    rng = np.random.default_rng(0)
    rows = pd.DataFrame([{"dataset_id": "copenhagen", "timestamp": d*DAY+28800, "user_min": 1, "user_max": i+2,
                          "label_24h": int(i % (d - 13) == 0)} for d in days for i in range(40)])
    for model in MODELS:
        rows[f"p_7d_{model}"] = rows.label_24h*0.5 + rng.random(len(rows))*0.5
    bank = rows[["dataset_id", "timestamp", "user_min", "user_max"]].copy()
    bank["pair_contact_days"] = (rows.user_max % 3) + 1
    bank["recency_seconds"] = 3600.0*(rows.user_max % 24 + 1)
    for name in ("participant_a_activity", "participant_b_activity", "scan_coverage_a", "scan_coverage_b"):
        bank[name] = rng.random(len(rows))
    return rows, bank


def test_day_table_reports_lift_over_prevalence_per_day():
    rows, bank = frame()
    table = day_table(rows, bank)
    assert [r["study_day"] for r in table] == [17, 18, 19]
    for record in table:
        assert set(DESCRIPTORS) <= set(record)
        np.testing.assert_allclose(record["lift_xgboost"], record["ap_xgboost"]/record["positive_rate"])
        assert record["rows"] == 40


def test_correlations_cover_every_descriptor_for_ap_and_lift():
    rows, bank = frame(days=(16, 17, 18, 19, 20))
    out = correlations(day_table(rows, bank))
    assert len(out) == 2*len(DESCRIPTORS) and all(-1 <= c["spearman_rho"] <= 1 for c in out if c["spearman_rho"] == c["spearman_rho"])
