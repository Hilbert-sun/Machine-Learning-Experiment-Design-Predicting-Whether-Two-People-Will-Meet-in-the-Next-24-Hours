"""Exercise the real app router and each view without requiring a browser."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.ui import PAGES

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.mark.parametrize("path,title", PAGES)
def test_all_pages_load(path, title):
    app = AppTest.from_file(APP).run()
    app.switch_page(path).run()
    assert not app.exception
    assert app.title
    if "Overview" not in title:
        assert app.title[0].value == title


def test_empty_overview_has_no_fabricated_metrics():
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert len(app.metric) == 6
    assert all(metric.value == "—" for metric in app.metric)


def test_prediction_requires_model():
    app = AppTest.from_file(APP).run().switch_page("pages/5_Prediction_Lab.py").run()
    assert not app.exception
    assert "不预测爱情" in app.warning[0].value
    assert "尚无已训练模型" in app.info[0].value
    assert not app.metric
    assert not app.button


def test_dataset_selection_persists_after_navigation():
    app = AppTest.from_file(APP).run().switch_page("pages/1_Data_Manager.py").run()
    app.selectbox[0].select("SocioPatterns").run()
    app.switch_page("pages/7_Data_Sources.py").run()
    app.switch_page("pages/1_Data_Manager.py").run()
    assert not app.exception
    assert app.selectbox[0].value == "SocioPatterns"
