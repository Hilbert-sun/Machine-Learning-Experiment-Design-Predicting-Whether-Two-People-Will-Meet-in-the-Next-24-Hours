"""Real Streamlit controls run real estimators on explicitly synthetic fixture artifacts."""

from pathlib import Path
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from src.training_data import TrainingInputs
from test_leakage import artifacts, synthetic_frame

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def training_page(monkeypatch, tmp_path, *, eligible=True):
    labels, features = artifacts(tmp_path, synthetic_frame())
    labels.report.update(source_kind="synthetic_test_fixture", rows=160)
    if not eligible:
        import pandas as pd
        frame = pd.read_parquet(labels.path)
        frame["eligible_for_evaluation"] = False
        frame.to_parquet(labels.path, index=False)
    selected = TrainingInputs(SimpleNamespace(report={"source_file": "synthetic_fixture"}, directory=tmp_path / "synthetic_processed_fixture"), labels, features)
    monkeypatch.setattr("src.training_data.available_training_inputs", lambda *args: [selected])
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {"models": str(tmp_path / "models"), "reports": str(tmp_path / "reports")}})
    return AppTest.from_file(APP).run().switch_page("pages/4_Model_Training.py").run()


def test_training_ui_saves_a_real_calibrated_pipeline(monkeypatch, tmp_path):
    app = training_page(monkeypatch, tmp_path)
    assert not app.exception
    next(button for button in app.button if button.label == "训练并保存模型").click().run()
    assert not app.exception and any("已训练并保存 1 个模型" in message.value for message in app.success)
    assert len(list((tmp_path / "models").rglob("model.joblib"))) == 1
    assert len(list((tmp_path / "reports").glob("training-*.json"))) == 1
    assert app.get("plotly_chart")
    app.number_input[0].set_value(43).run()
    assert not app.success  # Results must not be presented under changed settings.


def test_no_eligible_targets_disables_training_instead_of_fabricating_results(monkeypatch, tmp_path):
    app = training_page(monkeypatch, tmp_path, eligible=False)
    assert not app.exception
    assert any("没有覆盖策略" in message.value for message in app.warning)
    assert next(button for button in app.button if button.label == "训练并保存模型").disabled
    assert not list((tmp_path / "models").rglob("*.joblib"))
