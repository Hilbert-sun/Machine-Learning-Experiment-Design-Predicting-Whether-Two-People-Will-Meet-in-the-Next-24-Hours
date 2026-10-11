"""P03 presentation parity, touch descriptions and session/navigation integrity."""
from pathlib import Path
import subprocess

from streamlit.testing.v1 import AppTest
from src.chance_encounter import Questionnaire, evaluate_questionnaire
from src.encounter_graph import clue_graph, clue_figure, graph_positions
from src.encounter_insights import factor_figure
from src.product_ui import readable_figure
from test_chance_encounter_ui import fill, VALID

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / 'app.py')
PLAY = 'pages/12_Chance_Encounter.py'
EXPLORE = 'pages/13_Encounter_Insights.py'
HUB = 'pages/14_Research_Hub.py'


def button(app, label): return next(b for b in app.button if b.label == label)


def test_touch_description_focus_restore_and_mutual_removal():
    app = fill(AppTest.from_file(APP).run().switch_page(PLAY).run(), VALID)
    app.switch_page(EXPLORE).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ['我的偶遇分析', '真实数据中的相遇规律']
    app.selectbox(key='_explore_mutual').select('three_five').run()
    app.selectbox(key='_explore_node_details').select('summary:mutual').run()
    assert any('仅为用户自述的汇总范围' in c.value for c in app.caption)
    app.radio(key='_explore_focus').set_value('B').run()
    assert app.radio(key='_explore_focus').value == 'B'
    button(app, '恢复默认视图').click().run()
    assert app.selectbox(key='_explore_node_details').value is None
    assert app.radio(key='_explore_focus').value == 'all'
    app.selectbox(key='_explore_node_details').select('summary:mutual').run()
    app.selectbox(key='_explore_mutual').select('none').run()
    assert not app.exception and app.selectbox(key='_explore_node_details').value is None
    assert 'summary:mutual' not in app.selectbox(key='_explore_node_details').options


def test_research_roundtrip_keeps_personal_result_then_edit_invalidates():
    app = fill(AppTest.from_file(APP).run().switch_page(PLAY).run(), VALID)
    app.switch_page(EXPLORE).run()
    original = app.session_state['_chance_result']
    app.switch_page(HUB).run()
    assert not app.exception and not app.metric
    app.switch_page(EXPLORE).run()
    assert app.session_state['_chance_result'] == original and original.score == 66
    button(app, '修改我的信息').click().run()
    app.switch_page(EXPLORE).run()
    assert not any(m.label == '当前会话的趣味偶遇指数' for m in app.metric)
    fresh = AppTest.from_file(APP).run().switch_page(EXPLORE).run()
    assert not any(m.label == '当前会话的趣味偶遇指数' for m in fresh.metric)


def test_display_changes_preserve_graph_positions_points_and_factor_values():
    result = evaluate_questionnaire(Questionnaire.from_mapping(VALID))
    graph = clue_graph(result, 'three_five')
    positions = graph_positions(graph)
    for focus in ('all', 'A', 'B'):
        figure = clue_figure(graph, focus)
        points = figure.data[-1]
        assert dict(zip(points.ids, zip(points.x, points.y))) == positions
        assert figure.layout.xaxis.range == (-1.65, 1.65)
        assert figure.layout.yaxis.range == (-1.65, 1.65)
        assert not points.cliponaxis
    factors = factor_figure(result)
    before = [trace.to_plotly_json() for trace in factors.data]
    readable_figure(factors)
    assert [trace.to_plotly_json() for trace in factors.data] == before


def test_product_data_and_scientific_engines_byte_preserved():
    baseline = 'bb05d4ae709e64643a3d436aeeb7e73f880b6202'
    for name in ('src/chance_encounter.py', 'src/welcome.py', 'src/encounter_insights.py',
                 'src/window_features.py', 'src/asof_inference.py', 'src/time_machine.py',
                 'src/train.py', 'src/evaluate.py', 'src/overview.py'):
        assert (ROOT / name).read_bytes() == subprocess.check_output(['git', '-C', str(ROOT), 'show', baseline + ':' + name])
