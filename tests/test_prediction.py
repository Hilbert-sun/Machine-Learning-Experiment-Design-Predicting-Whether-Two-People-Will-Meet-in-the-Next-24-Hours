"""Synthetic model/source fixtures verify true inference and temporal backtest safety."""

import json
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from src.feature_engineering import FEATURE_NAMES
from src.model_registry import ModelRegistry
from src.predict import backtest_outcome, predict_pair
from src.preprocessing import preprocess_contacts
from src.temporal_split import TrainingDataError, chronological_split
from src.train import save_training_run, train_models
from test_leakage import synthetic_frame

DAY = 86400
PREDICTION = 32 * DAY + 28800


@pytest.fixture
def prediction_setup(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "bt_symmetric.csv"
    rows = ["timestamp,user_a,user_b,rssi", "0,5,97,-65"]
    rows += [f"{t},{user},-1,0" for t in range(0, 40 * DAY + 1, 300) for user in (5, 97)]
    rows.append(f"{PREDICTION+1},5,97,-60")
    source.write_text("\n".join(rows) + "\n")
    processed = preprocess_contacts(source, "Copenhagen", tmp_path / "processed")
    run = train_models(chronological_split(synthetic_frame()), ["logistic_regression"])
    record, _ = save_training_run(run, tmp_path / "models", tmp_path / "reports", provenance={"dataset": "Copenhagen", "source_kind": "synthetic_test_fixture", "label_policy": {"min_scan_coverage": 0.5}, "feature_policy": {}})
    return processed, record["saved_models"]["logistic_regression"]


def test_actual_probability_pair_symmetry_and_future_mode_hides_outcome(prediction_setup, monkeypatch):
    processed, model = prediction_setup
    monkeypatch.setattr("src.predict.backtest_outcome", lambda *args, **kwargs: pytest.fail("future mode accessed outcomes"))
    result = predict_pair(processed, model, PREDICTION, 5, 97)
    reversed_result = predict_pair(processed, model, PREDICTION, 97, 5)
    assert 0 <= result["probability"] <= 1
    assert result["probability"] == reversed_result["probability"]
    assert "actual_outcome" not in result
    assert result["historical_contact_count"] == 0
    assert 0 <= result["prediction_entropy"] <= 1
    assert result["explanation"]["method"] == "training_median_replacement_sensitivity"


def test_backtest_positive_and_incomplete_window_remain_truthful(prediction_setup):
    processed, model = prediction_setup
    result = predict_pair(processed, model, PREDICTION, 5, 97, backtest=True)
    assert result["actual_outcome"]["outcome"] == "Contact"
    assert backtest_outcome(processed, 40 * DAY, (5, 97))["outcome"] == "Unknown"


def test_model_information_deadline_self_pair_and_window_mismatch_rejected(prediction_setup):
    processed, model = prediction_setup
    for kwargs in ({"timestamp": 28800, "a": 5, "b": 97}, {"timestamp": PREDICTION, "a": 5, "b": 5}, {"timestamp": PREDICTION, "a": 5, "b": 97, "window_days": 1}):
        with pytest.raises(TrainingDataError):
            predict_pair(processed, model, **kwargs)


def test_prediction_page_computes_then_invalidates_and_hides_backtest_on_mode_change(prediction_setup, monkeypatch, tmp_path):
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {"models": str(tmp_path / "models"), "processed": str(tmp_path / "processed"), "raw_copenhagen": str(tmp_path / "raw"), "raw_sociopatterns": str(tmp_path / "raw")}})
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=10).run().switch_page("pages/5_Prediction_Lab.py").run()
    assert not app.exception and not app.metric
    app.number_input[0].set_value(33).run()
    app.button[0].click().run()
    assert not app.exception and app.metric
    assert any("合成测试" in message.value for message in app.warning)
    assert not any("Actual Outcome" in message.value for message in app.info)
    app.radio[0].set_value("历史回测（仅显式读取实际结果）").run()
    assert not app.metric
    app.button[0].click().run()
    assert any("Actual Outcome: Contact" in message.value for message in app.info)
    app.radio[0].set_value("未来实验（隐藏真实结果）").run()
    assert not any("Actual Outcome" in message.value for message in app.info)


def test_bounded_history_models_remove_longer_window_features():
    frame = synthetic_frame()
    model = ModelRegistry.create("logistic_regression", feature_window_days=1).fit(frame.loc[:, FEATURE_NAMES], frame.label_24h)
    assert "contact_count_7d" not in model.feature_columns
    assert "historical_contact_probability" not in model.feature_columns
    assert "contact_count_1d" in model.feature_columns


def test_saved_window_contract_cannot_be_changed_by_manifest_only(tmp_path):
    frame = synthetic_frame()
    model = ModelRegistry.create("logistic_regression", feature_window_days=1).fit(frame.loc[:, FEATURE_NAMES], frame.label_24h)
    saved = ModelRegistry.save(model, tmp_path / "models")
    path = saved / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["feature_window_days"] = 14
    path.write_text(json.dumps(manifest))
    with pytest.raises(TrainingDataError, match="清单不一致"):
        ModelRegistry.load(saved)
