import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.multisource_exploration import (TARGETS, aggregate_retrieval, grouped_histogram, load_source, network_summary, run_study)
from src.positive_retrieval import DAY, KEYS, retrieval_metrics
from test_positive_retrieval import write_source, T


def test_network_unique_topology_activity_and_tick_safety(tmp_path):
    rows = [(0, 1, 2), (0, 2, 3), (0, 1, 2), (2 * DAY, 1, 2), (2 * DAY, 4, 5)]
    source = write_source(tmp_path, rows, last=2 * DAY)
    result = network_summary(source)
    assert result['nodes'] == 5 and result['edges'] == 3 and result['components'] == 2
    assert result['unique_contact_records'] == 4
    assert result['density'] == .3
    assert result['activity'][1]['records'] == 0
    assert result['pairs_active_on_multiple_days'] == 1
    unknown = write_source(tmp_path, rows, unit='unverified tick', filename='ticks.parquet')
    tick = network_summary(unknown)
    assert tick['activity'] == []
    assert tick['pairs_active_on_multiple_days'] is None


def test_disclosure_and_empty_aggregate():
    assert aggregate_retrieval([]) == []
    assert grouped_histogram([1], [(0, 5, '0–5')])['status'] == 'suppressed_small_groups'
    assert grouped_histogram([1] * 6, [(0, 5, '0–5')])['bins'] == [{'bin': '0–5', 'count': 6}]
    ranking = pd.DataFrame([['x', 1, 2]], columns=KEYS)
    row = dict(dataset_id='x', scope='per_window', window_days=1, method='historical_frequency', **retrieval_metrics(ranking, ranking, 5))
    result = aggregate_retrieval([row])[0]
    assert result['disclosure_status'] == 'suppressed_small_counts_and_ratios'
    assert result['observed_positive_capture_at_k'] is None
    assert result['observed_positive_hits_at_k'] is None


@pytest.fixture
def synthetic_root(tmp_path):
    root = tmp_path
    (root / 'configs').mkdir()
    config = {'paths': {'processed': 'data/processed', 'raw_sociopatterns': 'data/raw/sociopatterns'}}
    (root / 'configs/default.yaml').write_text(yaml.safe_dump(config))
    registry = []
    for name in TARGETS:
        spec = dict(dataset_id=name, name=name, format='triplet', filename='contacts.txt',
                    source_url='https://example.test/source', licence='Synthetic test fixture only', citation='Synthetic test fixture',
                    source_verified=True, licence_verified=True, access_status='public',
                    scan_coverage_evidence='Positive contacts only', coverage_supported=False,
                    timestamp_unit='unverified integer tick' if name == 'reality_mining_mendeley' else 'seconds',
                    temporal_resolution=20)
        registry.append(spec)
        if name == 'social_evolution':
            continue
        folder = root / ('data/raw/sociopatterns' if name == 'highschool2013' else f'data/raw/catalog/{name}')
        folder.mkdir(parents=True)
        rows = [(d * DAY + 30000 + i * 20, 1 + i, 100 + i) for d in range(12) for i in range(30)]
        (folder / 'contacts.txt').write_text('\n'.join(' '.join(map(str, r)) for r in rows))
    (root / 'configs/dataset_catalog.json').write_text(json.dumps(registry))
    return root


def test_source_missing_and_workplace_blocker(synthetic_root):
    config = yaml.safe_load((synthetic_root / 'configs/default.yaml').read_text())
    registry = json.loads((synthetic_root / 'configs/dataset_catalog.json').read_text())
    missing, source, _ = load_source(synthetic_root, config, registry[-1])
    assert missing['status'] == 'source_unavailable' and source is None
    (synthetic_root / 'data/raw/catalog/workplace2013/contacts.txt').unlink()
    with pytest.raises(ValueError, match='BLOCKED.*workplace2013'):
        run_study(synthetic_root)


def test_pipeline_freeze_reproducibility_aggregate_exports_and_no_old_writes(synthetic_root, monkeypatch):
    from src import multisource_exploration as module
    original = module.reveal_positive_pairs
    old = synthetic_root / 'reports/T17_REAL_EXPERIMENT.md'
    old.parent.mkdir(parents=True)
    old.write_text('frozen sentinel')
    def checked_reveal(source, t, **kwargs):
        root = synthetic_root / 'data/processed/multisource'
        protocols = list(root.glob('*/PROTOCOL_FROZEN.json'))
        assert len(protocols) == 1
        assert list(protocols[0].parent.glob(f'{source.dataset_id}-*d-{t}-scores.parquet'))
        return original(source, t, **kwargs)
    monkeypatch.setattr(module, 'reveal_positive_pairs', checked_reveal)
    result = run_study(synthetic_root)
    again = run_study(synthetic_root)
    assert result == again and old.read_text() == 'frozen sentinel'
    private = synthetic_root / 'data/processed/multisource' / result['run_id']
    recomputed = aggregate_retrieval(pd.read_parquet(private / 'retrieval_rows.parquet').to_dict('records'))
    assert recomputed == result['retrieval']
    common = pd.DataFrame(result['retrieval'])
    common = common.loc[common.scope.eq('common_7d')]
    for _, group in common.groupby(['dataset_id', 'method', 'k']):
        for key in ['candidate_count', 'future_observed_positive_pairs', 'future_positive_pairs_in_candidate_pool', 'eligible_prediction_times']:
            assert group[key].nunique() <= 1
    for s in result['sources']:
        if 'file_path' in s and s.get('file_hash'):
            from src.baseline_audit import sha256
            assert sha256(synthetic_root / s['file_path']) == s['file_hash']
    for source in result['sources']:
        if source['dataset_id'] == 'reality_mining_mendeley':
            assert source['status'] == 'time_unit_unverified'
            assert not [r for r in result['retrieval'] if r['dataset_id'] == source['dataset_id']]
    public = synthetic_root / 'reports/multisource'
    assert len(list(public.iterdir())) == 5
    for path in public.iterdir():
        text = path.read_text()
        assert 'user_min' not in text or path.name == 'T31_PROTOCOL.json'  # tie rule names, never IDs
        assert 'user_max' not in text or path.name == 'T31_PROTOCOL.json'
        assert str(synthetic_root) not in text
    assert 'Observed Positive Retrieval' in (private / 'T31_REPORT.html').read_text()
    assert (private / 'T31_REPORT.html').stat().st_size > 10000


def test_existing_bad_cache_is_rejected(synthetic_root):
    config = yaml.safe_load((synthetic_root / 'configs/default.yaml').read_text())
    spec = json.loads((synthetic_root / 'configs/dataset_catalog.json').read_text())[0]
    from src.dataset_catalog import DatasetAdapter, directory_for
    DatasetAdapter(spec).inspect(directory_for(synthetic_root, config, spec) / spec['filename'], synthetic_root / 'data/processed/catalog')
    path = next((synthetic_root / 'data/processed/catalog').glob('*/*/contacts.parquet'))
    path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='checksum mismatch'):
        load_source(synthetic_root, config, spec)


def test_unverified_social_file_cannot_enter_study(synthetic_root):
    config = yaml.safe_load((synthetic_root / 'configs/default.yaml').read_text())
    spec = json.loads((synthetic_root / 'configs/dataset_catalog.json').read_text())[-1]
    folder = synthetic_root / 'data/raw/catalog/social_evolution'
    folder.mkdir(parents=True)
    (folder / 'contacts.txt').write_text('0 1 2\n')
    base, source, _ = load_source(synthetic_root, config, spec)
    assert source is None and base['status'] == 'blocked'
