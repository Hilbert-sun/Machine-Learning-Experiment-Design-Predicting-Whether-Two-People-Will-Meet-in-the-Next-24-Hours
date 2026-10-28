"""Play research reference: public aggregate only, suppressed small cells, honest unavailability."""
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.play_reference import FREQUENCY, RECENCY, SUPPRESSION, TABLE, reference
from tools.check_repository_safety import _private_structure

ROOT = Path(__file__).resolve().parents[1]
VALID = {'relationship': 'friend', 'distance': 'walkable', 'frequency': 'three_five', 'recency': 'week',
         'area': 'sometimes', 'timing': 'sometimes', 'arrangement': 'no'}


def test_public_table_is_complete_suppressed_and_aggregate_only():
    table = json.loads(TABLE.read_text())
    assert not _private_structure(table) and table['protocol']['fitting'] is False
    assert {(c['recency'], c['frequency']) for c in table['cells']} == {(r, f) for r in RECENCY for f in FREQUENCY}
    for cell in table['cells']:
        if cell['suppressed']:
            assert cell['samples'] is None and cell['recontact_rate'] is None
        else:
            assert cell['samples'] >= SUPPRESSION['minimum_samples'] and 0 < cell['recontact_rate'] < 1


def test_lookup_ready_suppressed_and_unavailable_answers():
    table = {'overall_recontact_rate': 0.1, 'cells': [
        {'recency': r, 'frequency': f, 'samples': 500, 'recontact_rate': 0.2, 'suppressed': f == 'six_plus'}
        for r in RECENCY for f in FREQUENCY]}
    ready = reference('week', 'three_five', table)
    assert ready['status'] == 'ready' and ready['rate'] == 0.2 and ready['samples'] == 500
    assert reference('day', 'six_plus', table)['status'] == 'suppressed'
    for recency, frequency in (('older', 'one_two'), ('never', 'zero'), ('unknown', 'three_five'), ('week', 'unknown'), (None, None)):
        assert reference(recency, frequency, table)['status'] == 'unavailable'


def test_result_page_shows_reference_without_changing_index():
    app = AppTest.from_file(str(ROOT / 'pages/12_Chance_Encounter.py')).run()
    for field, value in VALID.items():
        app.selectbox(key='chance_input_' + field).select(value)
    next(b for b in app.button if b.label == '计算趣味偶遇指数').click().run()
    assert not app.exception and app.metric[0].value == '66 / 100'
    expected = reference('week', 'three_five')
    text = ' '.join(m.value for m in app.markdown)
    assert '研究参照' in text and f"{expected['rate']*100:.0f}%" in text and '不能当作你们真实的相遇概率' in ' '.join(c.value for c in app.caption)
