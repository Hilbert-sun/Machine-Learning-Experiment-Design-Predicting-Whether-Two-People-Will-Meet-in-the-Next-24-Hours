from pathlib import Path

from streamlit.testing.v1 import AppTest

from test_experiments import saved_fixture

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_evaluation_page_displays_true_fixture_results_and_blocks_test_ablation(monkeypatch, tmp_path):
    saved_fixture(tmp_path)
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {"reports": str(tmp_path / "reports")}})
    app = AppTest.from_file(APP, default_timeout=15).run().switch_page("pages/6_Model_Evaluation.py").run()
    assert not app.exception
    assert any("合成测试" in message.value for message in app.warning)
    next(button for button in app.button if button.label == "计算冻结模型评估").click().run()
    assert not app.exception and len(app.get("plotly_chart")) >= 4
    assert app.get("download_button")
    next(button for button in app.button if button.label.startswith("运行验证集消融")).click().run()
    assert not app.exception
    assert any("E3通讯消融不可运行" in message.value for message in app.info)
    app.radio[0].set_value("test（冻结模型的最终报告）").run()
    assert not app.get("plotly_chart")  # No validation result under the test label.
    next(button for button in app.button if button.label == "计算冻结模型评估").click().run()
    assert not app.exception
    assert next(button for button in app.button if button.label.startswith("运行验证集消融")).disabled


def test_missing_real_experiments_does_not_show_placeholder_scores(monkeypatch, tmp_path):
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {"reports": str(tmp_path / "reports")}})
    app = AppTest.from_file(APP).run().switch_page("pages/6_Model_Evaluation.py").run()
    assert not app.exception and not app.metric and not app.get("plotly_chart")
    assert any("尚无" in message.value for message in app.info)
