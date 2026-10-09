import numpy as np
import pandas as pd
import pytest

from src.window_robustness import forward_folds, paired_uncertainty, sensitivity_tables
from src.window_study import PROTOCOL
from test_window_study import small_inputs


def cohort_twenty_days():
    return pd.DataFrame([{"dataset_id":"copenhagen","timestamp":d*86400+28800,"user_min":1,"user_max":i+2,"label_24h":i%2}
                         for d in range(7,27) for i in range(60)])


def test_forward_folds_have_complete_grouped_days_and_strict_future_boundaries():
    folds = forward_folds(cohort_twenty_days(),PROTOCOL["walk_forward"])
    assert [f["status"] for f in folds] == ["ready"]*3
    for fold in folds:
        a,b,c = [fold["parts"][n] for n in ("train","validation","test")]
        assert a.timestamp.max()+86400 < b.timestamp.min()
        assert b.timestamp.max()+86400 < c.timestamp.min()
        assert c.timestamp.nunique()==2 and b.timestamp.nunique()==3
        assert c.timestamp.max()//86400+1 < 24  # no primary holdout used for robustness selection
    short = cohort_twenty_days().query("timestamp >= 18*86400")
    assert any(f["status"]=="insufficient_days" for f in forward_folds(short,PROTOCOL["walk_forward"]))


def test_paired_day_ranges_refuse_mismatched_labels_and_do_not_fake_ci():
    first = cohort_twenty_days().query("timestamp >= 23*86400").copy()
    first["p_xgboost"] = 0.5
    second = first.copy()
    second["p_xgboost"] = np.where(second.label_24h,0.8,0.2)
    result = paired_uncertainty(first,second,"xgboost",PROTOCOL["uncertainty"])
    assert result["distinct_prediction_days"]==4
    assert result["confidence_interval"] is None
    assert result["status"]=="insufficient_days_for_ci"
    assert result["descriptive_leave_one_day_out_range"]==[0.5,0.5]
    second.iloc[0,second.columns.get_loc("label_24h")] = 1
    with pytest.raises(ValueError,match="different keys/labels"):
        paired_uncertainty(first,second,"xgboost",PROTOCOL["uncertainty"])


def test_temporal_block_bootstrap_resamples_whole_paired_days_when_supported():
    first = cohort_twenty_days().copy()
    first["p_xgboost"] = 0.5
    second = first.assign(p_xgboost=np.where(first.label_24h,0.8,0.2))
    result = paired_uncertainty(first,second,"xgboost",{**PROTOCOL["uncertainty"],"bootstrap_repetitions":20})
    assert result["status"]=="paired_day_block_bootstrap"
    assert result["confidence_interval"]==[0.5,0.5]


def test_sensitivity_groups_are_common_across_windows_and_counts_reconcile():
    frame,bank = small_inputs()
    first = frame.copy()
    for name in PROTOCOL["models"]:
        first[f"p_{name}"] = np.where(first.label_24h,0.7,0.3)
        first[f"threshold_{name}"] = 0.5
    rows = sensitivity_tables({1:first,3:first.copy(),7:first.copy()},bank)
    for days in (1,3,7):
        for dimension in ("contact_frequency_1d_bins","historical_1d_scan_quality","prediction_study_day"):
            subset = [r for r in rows if r["window_days"]==days and r["model"]=="xgboost" and r["dimension"]==dimension]
            assert sum(r["rows"] for r in subset)==len(first)
