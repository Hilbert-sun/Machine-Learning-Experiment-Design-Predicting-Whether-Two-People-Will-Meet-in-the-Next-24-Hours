"""Verify real cache aggregation, time/user/pair scope, and honest unknown charts."""

import json
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from src.preprocessing import preprocess_contacts
from src.visualization import exploration_figures, exploration_options, summarize_exploration

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture
def bluetooth(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "bt_symmetric.csv"
    source.write_text("# timestamp,user_a,user_b,rssi\n0,5,-1,0\n0,300,-1,0\n"
                      "300,5,97,-60\n300,97,5,-60\n600,5,222,-80\n"
                      "86400,97,222,-70\n172800,5,-1,0\n")
    return source, preprocess_contacts(source, "Copenhagen", tmp_path / "processed", chunksize=2)


def test_day_boundaries_complete_counts_options_and_rssi(bluetooth):
    _, processed = bluetooth
    options = exploration_options(processed.directory, processed.report)
    assert options == {"users": [5, 97, 222, 300], "first_day": 1, "last_day": 3}
    data = summarize_exploration(processed.directory, processed.report, (1, 3))
    assert data.rows == 3
    assert data.daily.contact_records.tolist() == [2, 1, 0]
    assert data.hourly.contact_records.sum() == 3
    assert data.pairs.contact_records.sum() == 3
    assert data.activity.contact_records.sum() == 6
    assert data.rssi.records.sum() == 3
    assert summarize_exploration(processed.directory, processed.report, (2, 2)).rows == 1


def test_user_either_endpoint_pair_symmetry_and_filter_intersection(bluetooth):
    _, processed = bluetooth
    args = (processed.directory, processed.report, (1, 3))
    assert summarize_exploration(*args, users=[222]).rows == 2
    assert summarize_exploration(*args, pair=(97, 5)).rows == 1
    assert summarize_exploration(*args, pair=(5, 97)).rows == 1
    assert summarize_exploration(*args, users=[222], pair=(97, 5)).rows == 0
    # A valid but never recorded pair remains empty; no candidate pair is fabricated.
    assert summarize_exploration(*args, pair=(300, 97)).pairs.empty


def test_empty_contact_selection_retains_scan_evidence_and_zero_is_not_unknown(bluetooth):
    _, processed = bluetooth
    data = summarize_exploration(processed.directory, processed.report, (1, 1), users=[300])
    assert data.rows == 0
    assert data.coverage_mean == pytest.approx(1 / 288)
    assert data.coverage["有扫描记录"].tolist() == [1]
    receiver = summarize_exploration(processed.directory, processed.report, (1, 1), users=[222])
    assert receiver.rows == 1 and receiver.coverage_mean == 0
    assert receiver.coverage["无扫描记录"].tolist() == [1]
    pair = summarize_exploration(processed.directory, processed.report, (1, 1), pair=(5, 222))
    assert pair.coverage_mean == pytest.approx(3 / 288 / 2)


def test_plot_counts_heatmap_symmetry_limits_and_scope(bluetooth):
    _, processed = bluetooth
    data = summarize_exploration(processed.directory, processed.report, (1, 3))
    figures = exploration_figures(data, "Copenhagen · Study Day 01–03", top_n=2)
    assert len(figures) == 8
    heatmap = figures["历史接触记录热力图 · Top 2"].data[0]
    assert np.asarray(heatmap.z).shape == (2, 2)
    assert np.array_equal(heatmap.z, np.asarray(heatmap.z).T)
    assert np.asarray(heatmap.z).sum() == 2
    assert sum(figures["配对接触频率分布"].data[0].y) == 3
    assert all("Study Day 01–03" in figure.layout.title.text for figure in figures.values())


def test_sociopatterns_never_invents_rssi_or_scan_coverage(tmp_path):
    source = tmp_path / "HighSchool2013_proximity_net.csv"
    source.write_text("1385982020 97 5 MP PC\n1386068420 5 222 PC BIO\n")
    processed = preprocess_contacts(source, "SocioPatterns", tmp_path / "processed")
    data = summarize_exploration(processed.directory, processed.report, (1, 2))
    assert data.coverage_mean is None
    assert data.coverage.mean_scan_coverage.isna().all()
    assert data.coverage["覆盖率未知"].tolist() == [3, 3]
    assert data.rssi.empty
    figures = exploration_figures(data, "Study Day 01–02")
    assert "RSSI 分布" not in figures and "扫描记录覆盖率" not in figures
    assert figures["扫描与缺失观测状态"]


def app_with_config(monkeypatch, tmp_path):
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {
        "raw_copenhagen": str(tmp_path / "raw"), "raw_sociopatterns": str(tmp_path / "raw"),
        "processed": str(tmp_path / "processed"),
    }})
    return AppTest.from_file(APP).run().switch_page("pages/2_Data_Explorer.py").run()


def test_page_filters_change_actual_counts_and_remove_stale_cache(bluetooth, monkeypatch, tmp_path):
    source, _ = bluetooth
    app = app_with_config(monkeypatch, tmp_path)
    assert not app.exception
    assert app.metric[0].value == "3"
    assert len(app.get("plotly_chart")) == 8
    app.slider[0].set_range(1, 1).run()
    assert app.metric[0].value == "2"
    app.multiselect[0].select(300).run()
    assert app.metric[0].value == "0" and app.metric[3].value != "未知"
    assert any("0条记录不能证明" in message.value for message in app.info)
    app.multiselect[0].unselect(300).run()
    app.checkbox[0].check().run()
    assert app.metric[0].value == "1"
    assert any("配对 5–97" in caption.value for caption in app.caption)
    source.write_text(source.read_text() + "172800,5,97,-60\n")
    app.run()
    assert not app.exception and not app.metric
    assert any("尚无匹配" in message.value for message in app.info)


def test_page_missing_cache_is_actionable(monkeypatch, tmp_path):
    (tmp_path / "raw").mkdir()
    app = app_with_config(monkeypatch, tmp_path)
    assert not app.exception and not app.metric
    assert any("运行预处理" in message.value for message in app.info)


def test_sociopatterns_page_has_unknown_metrics_and_scoped_charts(monkeypatch, tmp_path):
    (tmp_path / "raw").mkdir()
    source = tmp_path / "raw" / "HighSchool2013_proximity_net.csv"
    source.write_text("1385982020 97 5 MP PC\n")
    preprocess_contacts(source, "SocioPatterns", tmp_path / "processed")
    app = app_with_config(monkeypatch, tmp_path)
    app.selectbox[0].select("SocioPatterns").run()
    assert not app.exception
    assert app.metric[3].value == "未知"
    assert not app.slider  # Single-day cache must not create an invalid slider.
    assert len(app.get("plotly_chart")) == 6
    assert any("扫描覆盖率未知" in message.value for message in app.info)
    for chart in app.get("plotly_chart"):
        spec = json.loads(chart.proto.spec)
        assert "SocioPatterns · Study Day 01–01" in spec["layout"]["title"]["text"]


@pytest.mark.parametrize("days,pair", [((0, 1), None), ((3, 2), None), ((1, 1), (5, 5))])
def test_invalid_scope_rejected(bluetooth, days, pair):
    _, processed = bluetooth
    with pytest.raises(ValueError):
        summarize_exploration(processed.directory, processed.report, days, pair=pair)
