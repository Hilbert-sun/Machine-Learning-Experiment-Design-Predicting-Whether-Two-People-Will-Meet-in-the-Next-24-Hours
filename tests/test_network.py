import networkx as nx
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from src.network import bounded_network, historical_network, network_figure, selected_node
from src.preprocessing import preprocess_contacts

DAY = 86400


@pytest.fixture
def processed(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "bt_symmetric.csv"
    source.write_text(f"timestamp,user_a,user_b,rssi\n0,5,97,-65\n{DAY-1},5,444,-70\n{DAY},5,333,-70\n{DAY+100},97,222,-60\n{2*DAY},5,555,-60\n")
    return preprocess_contacts(source, "Copenhagen", tmp_path / "processed")


def test_network_uses_inclusive_history_start_and_excludes_snapshot_future(processed):
    graph = historical_network(processed, 2 * DAY, 1)
    assert set(graph) == {5, 97, 222, 333}
    assert set(map(frozenset, graph.edges)) == {frozenset((5, 333)), frozenset((97, 222))}
    assert all(details["last_contact"] < 2 * DAY for _, _, details in graph.edges(data=True))


def test_activity_frequency_render_limits_and_search_are_consistent(processed):
    graph = historical_network(processed, 2 * DAY, 3)
    assert graph.nodes[5]["activity"] == 3
    assert graph.nodes[5]["historical_degree"] == 3
    rendered = bounded_network(graph, max_nodes=2, max_edges=1, focus=333)
    assert len(rendered) == 2 and rendered.number_of_edges() == 1
    assert 333 in rendered and 5 in rendered
    figure = network_figure(rendered, "Study Day 03 · strict history", focus=333)
    assert len(figure.data[-1].customdata) == 2
    assert "strict history" in figure.layout.title.text


def test_click_selection_uses_node_customdata_and_ignores_edge_points():
    assert selected_node({"selection": {"points": [{"x": 1}, {"customdata": [0, 12, 3]}]}}) == 0
    assert selected_node({"selection": {"points": []}}) is None


def test_empty_window_and_invalid_limits_are_explicit(processed):
    assert not historical_network(processed, 0, 1)
    with pytest.raises(ValueError):
        bounded_network(nx.Graph(), max_nodes=101)


def test_network_page_renders_real_fixture_and_searches_node(processed, monkeypatch, tmp_path):
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {"raw_copenhagen": str(tmp_path / "raw"), "raw_sociopatterns": str(tmp_path / "raw"), "processed": str(tmp_path / "processed")}})
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run().switch_page("pages/3_Encounter_Network.py").run()
    assert not app.exception and app.get("plotly_chart")
    app.text_input[0].set_value("333").run()
    assert not app.exception and "匿名ID 333" in app.subheader[0].value
    app.text_input[0].set_value("-1").run()
    assert any("非负整数" in error.value for error in app.error)
