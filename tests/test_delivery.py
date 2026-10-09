"""Final integration: actual estimators, explicitly synthetic raw scans, no study scores."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from src.experiments import evaluate_saved_run, save_evaluation
from src.feature_engineering import build_features
from src.label_builder import build_labels
from src.model_registry import ModelRegistry
from src.overview import overview_summary
from src.pipeline_cache import file_signatures
from src.predict import predict_pair
from src.preprocessing import preprocess_contacts
from src.temporal_split import chronological_split, prepare_cohort
from src.train import save_training_run, train_models


def test_raw_scans_to_labels_features_calibration_saved_prediction_and_final_report(tmp_path):
    day = 86400
    pairs = [(5, 97), (5, 222), (97, 333), (222, 333)]
    rows = ["timestamp,user_a,user_b,rssi"]
    rows += [f"0,{a},{b},-65" for a, b in pairs]
    rows += [f"{timestamp},{user},-1,0" for timestamp in range(0, 40 * day + 1, 600) for user in (5, 97, 222, 333)]
    rows += [f"{index*day+43200},{a},{b},-60" for index in range(40) for pair_index, (a, b) in enumerate(pairs) if pair_index % 2 == index % 2]
    source = tmp_path / "bt_symmetric.csv"
    source.write_text("\n".join(rows) + "\n")
    processed = preprocess_contacts(source, "Copenhagen", tmp_path / "processed", chunksize=1000)
    labels = build_labels(processed, tmp_path / "processed" / "labels")
    features = build_features(processed, labels, tmp_path / "features")
    cohort = prepare_cohort(labels, features)
    assert cohort.label_24h.nunique() == 2 and len(cohort) == labels.report["rows"]
    split = chronological_split(cohort)
    run = train_models(split, ["logistic_regression", "xgboost"], calibration="sigmoid", feature_window_days=14, parameters={"xgboost": {"n_estimators": 5}})
    provenance = {"dataset": "Copenhagen", "source_kind": "synthetic_test_fixture",
                  "input_signatures": file_signatures([labels.path, features.path]), "label_policy": labels.report["policy"], "feature_policy": features.report}
    record, path = save_training_run(run, tmp_path / "models", tmp_path / "reports", provenance=provenance)
    row = split.test.iloc[0]
    prediction = predict_pair(processed, record["saved_models"]["xgboost"], int(row.timestamp), int(row.user_min), int(row.user_max), backtest=True)
    assert 0 <= prediction["probability"] <= 1
    assert prediction["actual_outcome"]["outcome"] == ("Contact" if row.label_24h else "No Contact")
    assert prediction["source_kind"] == "synthetic_test_fixture"
    future = predict_pair(processed, record["saved_models"]["logistic_regression"], int(row.timestamp), int(row.user_min), int(row.user_max))
    assert "actual_outcome" not in future
    report = evaluate_saved_run(path, evaluation_set="test")
    assert report["scope"]["rows"] == len(split.test)
    outputs = save_evaluation(report, tmp_path / "exports")
    assert all(output.is_file() for output in outputs.values())
    assert b"synthetic_test_fixture" in outputs["html"].read_bytes()
    assert ModelRegistry.load(record["saved_models"]["xgboost"])
    summary = overview_summary(tmp_path, {"paths": {"raw_copenhagen": str(tmp_path), "raw_sociopatterns": str(tmp_path),
                               "processed": str(tmp_path / "processed"), "features": str(tmp_path / "features"), "models": str(tmp_path / "models")}}, "Copenhagen", processed)
    assert summary["positive_rate"] == 0.5 and summary["eligible_samples"] == labels.report["rows"]
    assert summary["saved_models"] == 2


def test_overview_uses_current_cache_counts_and_keeps_missing_rate_unknown(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "bt_symmetric.csv"
    source.write_text("timestamp,user_a,user_b,rssi\n0,5,97,-65\n0,97,5,-65\n300,5,222,-70\n")
    preprocess_contacts(source, "Copenhagen", tmp_path / "processed")
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {"raw_copenhagen": str(raw), "raw_sociopatterns": str(raw), "processed": str(tmp_path / "processed"), "features": str(tmp_path / "features"), "models": str(tmp_path / "models")}})
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["3", "2", "2", "1", "未知", "未训练"]
    assert len(app.get("plotly_chart")) == 3
    source.write_text(source.read_text() + "600,5,97,-60\n")
    app.run()
    assert not app.exception and all(metric.value == "—" for metric in app.metric)
