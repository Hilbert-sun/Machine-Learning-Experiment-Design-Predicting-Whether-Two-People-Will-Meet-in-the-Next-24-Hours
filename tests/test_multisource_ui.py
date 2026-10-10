from pathlib import Path

from streamlit.testing.v1 import AppTest

from src import multisource_ui

ROOT = Path(__file__).resolve().parents[1]


def test_page_switching_actual_aggregate_loader_and_unavailable(monkeypatch, tmp_path):
    import json
    import pandas as pd
    from src.multisource_report import load_public_results
    folder = tmp_path / 'reports/multisource'
    folder.mkdir(parents=True)
    sources = [dict(dataset_id='workplace2013', name='Workplace fixture', status='descriptive_ready', source_url='https://example.test', licence='fixture'),
               dict(dataset_id='social_evolution', name='Unavailable source', status='source_unavailable', source_url='https://example.test', licence='unverified', reason='No lawful verified source file')]
    network = dict(dataset_id='workplace2013', nodes=42, edges=50, unique_contact_records=123, components=2,
                   largest_component_nodes=40, density=.1, mean_degree=2, degree_histogram={'bins': []}, pair_record_histogram={'bins': []}, activity=[])
    (folder / 'T31_SOURCE_SUMMARY.json').write_text(json.dumps(dict(run_id='synthetic_fixture', sources=sources, networks=[network])))
    (folder / 'T31_FEASIBILITY.json').write_text(json.dumps([dict(dataset_id=s['dataset_id'], status=s['status']) for s in sources]))
    pd.DataFrame(columns=['dataset_id']).to_csv(folder / 'T31_RETRIEVAL_METRICS.csv', index=False)
    monkeypatch.setattr(multisource_ui, 'load_public_results', lambda _: load_public_results(tmp_path))
    app = AppTest.from_file(str(ROOT / 'pages/11_Multi_Dataset_Exploration.py')).run()
    assert not app.exception
    assert app.metric[0].value == '42'
    app.selectbox[0].select(sources[1]).run()
    assert not app.exception and not app.metric
    assert any('source_unavailable' in i.value for i in app.info)
    app.selectbox[0].select(sources[0]).run()
    assert not app.exception and app.metric[2].value == '123'


def test_page_missing_report_has_no_fabricated_metrics(monkeypatch):
    monkeypatch.setattr(multisource_ui, 'load_public_results', lambda _: None)
    app = AppTest.from_file(str(ROOT / 'pages/11_Multi_Dataset_Exploration.py')).run()
    assert not app.exception and not app.metric
    assert '尚无真实' in app.info[0].value
