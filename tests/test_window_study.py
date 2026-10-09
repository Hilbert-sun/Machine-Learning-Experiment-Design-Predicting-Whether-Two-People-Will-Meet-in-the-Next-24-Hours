import json

import numpy as np
import pandas as pd
import pytest

from src.baseline_audit import sha256
from src.model_registry import ModelRegistry
from src.window_cohort import row_hash
from src.window_features import WINDOW_FEATURES
from src.window_models import create_window_model
from src.window_study import PROTOCOL, fit_window, model_input, evaluate_windows, verify_exported_metrics
from src.window_report import write_primary_report


def small_inputs():
    frame = pd.DataFrame([{"dataset_id": "copenhagen", "timestamp": d*86400+28800, "user_min": 1, "user_max": i+2,
                           "label_24h": i%2, "split": "train" if d<11 else "validation" if d<15 else "test"}
                          for d in range(7, 19) for i in range(12)])
    bank = frame[["dataset_id", "timestamp", "user_min", "user_max"]].copy()
    for i, name in enumerate(WINDOW_FEATURES):
        bank[name] = (np.arange(len(frame))+i)%7 / 7
    bank["rssi_mean"] = np.nan  # train-only removal preserved
    return frame, bank


def test_model_contract_rejects_future_fields_and_window_mismatch_and_registry_roundtrip(tmp_path):
    frame, bank = small_inputs()
    X = model_input(bank, frame, 1)
    model = create_window_model("logistic_regression", days=1, seed=42).fit(X, frame.label_24h)
    assert "rssi_mean" not in model.feature_columns
    with pytest.raises(ValueError, match="contract/window"):
        model.predict_proba(X.assign(label_24h=1))
    X.attrs["history_window_days"] = 7
    with pytest.raises(ValueError, match="contract/window"):
        model.predict_proba(X)
    X.attrs["history_window_days"] = 1
    path = ModelRegistry.save(model, tmp_path/"models/.window_study")
    np.testing.assert_allclose(ModelRegistry.load(path).predict_proba(X), model.predict_proba(X))
    assert ModelRegistry.list_saved(tmp_path/"models") == []


def test_window_study_metrics_recompute_and_exports_contain_real_computed_values(tmp_path):
    frame, bank = small_inputs()
    train, validation, test = [frame.loc[frame.split.eq(name)] for name in ("train", "validation", "test")]
    protocol = {**PROTOCOL, "parameters": {**PROTOCOL["parameters"], "xgboost": {"n_estimators": 3, "max_depth": 2}}}
    models, summaries = {}, {}
    for days in (1,7):
        models[days], summaries[days] = fit_window(bank, train, validation, days, protocol)
    before = {d:{n:m.threshold for n,m in ms.items()} for d,ms in models.items()}
    result = evaluate_windows(tmp_path, tmp_path, "synthetic_unit_test", test, {1:bank,7:bank}, models, summaries, {}, "T21", source_kind="synthetic_test_fixture")
    assert verify_exported_metrics(tmp_path)
    assert {d:{n:m.threshold for n,m in ms.items()} for d,ms in models.items()} == before
    assert result["predictions_local_ignored"]["1"]["key_hash"] == result["predictions_local_ignored"]["7"]["key_hash"]
    # Fixture output remains in tmp_path; never published as research evidence.
    html = write_primary_report(result, tmp_path, tmp_path/"public")
    assert b"plotly.js" in html.read_bytes()
    assert len(pd.read_csv(tmp_path/"public/T21_METRICS.csv")) == 6
    path = tmp_path/result["predictions_local_ignored"]["1"]["filename"]
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        verify_exported_metrics(tmp_path)
