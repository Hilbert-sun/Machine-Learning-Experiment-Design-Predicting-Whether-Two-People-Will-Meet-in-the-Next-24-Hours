"""Small hand-verifiable graphs, never substitute for actual source experiments."""

import pandas as pd
import pytest

from src.positive_retrieval import (DAY, KEYS, KS, METHODS, ContactSource, complete_times,
                                    historical_scores, rank_scores, retrieval_metrics, reveal_positive_pairs)

T = 8 * DAY + 28800


def write_source(tmp_path, rows, *, name='workplace2013', unit='seconds', filename='contacts.parquet', first=0, last=T + DAY):
    frame = pd.DataFrame(rows, columns=['timestamp', 'user_min', 'user_max'])
    frame['dataset_id'] = name
    path = tmp_path / filename
    frame.to_parquet(path, index=False)
    return ContactSource(path, name, first, last, unit)


@pytest.fixture
def source(tmp_path):
    rows = [(T - DAY, 1, 2), (T - 20, 1, 2), (T - 100, 1, 3), (T - 80, 2, 3),
            (T - 2 * DAY, 2, 4), (T, 7, 8), (T + 1, 1, 2), (T + DAY, 5, 6), (T + DAY + 1, 1, 3)]
    return write_source(tmp_path, rows)


@pytest.mark.parametrize('window', [1, 3, 7])
def test_future_invariance_and_history_change(source, tmp_path, window):
    before = historical_scores(source, T, window)
    frame = pd.read_parquet(source.path)
    past = frame.loc[frame.timestamp < T].copy()
    future = pd.DataFrame({'timestamp': [T, T + 2, T + 999999], 'user_min': [100, 101, 102], 'user_max': [200, 201, 202], 'dataset_id': source.dataset_id})
    pd.concat([past, future], ignore_index=True).to_parquet(source.path, index=False)
    after = historical_scores(source, T, window)
    pd.testing.assert_frame_equal(before, after)
    for method in METHODS:
        pd.testing.assert_frame_equal(rank_scores(before, method), rank_scores(after, method))
    past.loc[len(past)] = [T - 1, 2, 4, source.dataset_id]
    past.to_parquet(source.path, index=False)
    changed = historical_scores(source, T, window)
    assert not changed.equals(before)


def test_fixed_scores_duplicates_and_ties(source):
    scores = historical_scores(source, T, 1)
    row = scores.loc[scores.user_min.eq(1) & scores.user_max.eq(2)].iloc[0]
    assert row.historical_frequency == 2
    assert row.last_contact_recency == -20
    assert row.common_neighbors == 1
    frame = pd.read_parquet(source.path)
    pd.concat([frame, frame], ignore_index=True).to_parquet(source.path, index=False)
    pd.testing.assert_frame_equal(scores, historical_scores(source, T, 1))
    ranking = rank_scores(scores, 'common_neighbors')
    assert list(ranking[['user_min', 'user_max']].itertuples(index=False, name=None)) == [(1, 2), (1, 3), (2, 3)]
    with pytest.raises(ValueError, match='Unknown'):
        rank_scores(scores, 'future_best')
    scores.loc[0, 'common_neighbors'] = None
    with pytest.raises(ValueError, match='unavailable'):
        rank_scores(scores, 'common_neighbors')


def test_shared_one_day_candidates_for_all_windows(source):
    keys = [historical_scores(source, T, w)[KEYS] for w in (1, 3, 7)]
    pd.testing.assert_frame_equal(keys[0], keys[1])
    pd.testing.assert_frame_equal(keys[1], keys[2])


def test_reveal_boundaries_unknown_and_authorization(source, monkeypatch):
    scores = historical_scores(source, T, 1)
    future = reveal_positive_pairs(source, T, backtest=True)
    assert set(future[['user_min', 'user_max']].itertuples(index=False, name=None)) == {(1, 2), (5, 6)}
    result = retrieval_metrics(rank_scores(scores, 'historical_frequency'), future, 5)
    assert result['candidate_count'] == 3
    assert result['actual_k'] == 3
    assert result['observed_positive_hits_at_k'] == 1
    assert result['observed_positive_capture_at_k'] == 1
    assert result['observed_positive_capture_all_at_k'] == .5
    assert result['candidate_reach_of_observed_positives'] == .5
    assert result['future_positive_pairs_outside_candidate_pool'] == 1
    assert result['unknown_candidate_count'] == 2
    assert 'label_24h' not in scores and 'label_24h' not in future
    assert not {'precision', 'f1', 'accuracy', 'roc_auc', 'ap', 'brier_score', 'log_loss'} & result.keys()
    monkeypatch.setattr(ContactSource, 'read', lambda *a, **kw: pytest.fail('Future IO before authorization'))
    with pytest.raises(ValueError, match='Explicit backtest'):
        reveal_positive_pairs(source, T)


@pytest.mark.parametrize('k,hits', [(5, 3), (10, 4), (20, 5)])
def test_hand_computed_top_k(k, hits):
    ranking = pd.DataFrame({'dataset_id': ['x'] * 12, 'user_min': [1] * 12, 'user_max': range(2, 14)})
    future = ranking.iloc[[0, 2, 4, 8, 11]].copy()
    future.loc[len(future)] = ['x', 2, 99]
    result = retrieval_metrics(ranking, future, k)
    assert result['observed_positive_hits_at_k'] == hits
    assert result['observed_positive_capture_at_k'] == hits / 5
    assert result['actual_k'] == min(k, 12)
    assert result['future_observed_positive_pairs'] == 6


@pytest.mark.parametrize('empty', ['candidate', 'future', 'both', 'disjoint'])
def test_empty_denominators(empty):
    a = pd.DataFrame([['x', 1, 2]], columns=KEYS)
    b = a.copy()
    if empty in ('candidate', 'both'):
        a = a.iloc[:0]
    if empty in ('future', 'both'):
        b = b.iloc[:0]
    if empty == 'disjoint':
        b['user_max'] = 3
    result = retrieval_metrics(a, b, 5)
    assert result['observed_positive_capture_at_k'] is None
    assert result['status'] != 'observed_positive_retrieval'


def test_time_unit_and_span_guards(source, tmp_path):
    unknown = ContactSource(source.path, source.dataset_id, 0, 233, 'unverified integer tick')
    for operation in [lambda: historical_scores(unknown, T, 1), lambda: complete_times(unknown, 1), lambda: reveal_positive_pairs(unknown, T, backtest=True)]:
        with pytest.raises(ValueError, match='time_unit_unverified'):
            operation()
    with pytest.raises(ValueError, match='insufficient_history'):
        historical_scores(source, 4 * DAY, 7)
    short = ContactSource(source.path, source.dataset_id, T - 4 * DAY, T + DAY, 'seconds')
    assert complete_times(short, 7) == []
    with pytest.raises(ValueError, match='incomplete_future_span'):
        reveal_positive_pairs(source, T + 1, backtest=True)
    with pytest.raises(ValueError, match='Only prespecified'):
        complete_times(source, 2)


def test_source_namespace_isolation_and_empty_candidates(source):
    other = ContactSource(source.path, 'workplace2015', source.first, source.last, 'seconds')
    with pytest.raises(ValueError, match='Mixed dataset'):
        historical_scores(other, T, 1)
    scores = historical_scores(source, T, 1)
    future = scores[KEYS].copy()
    future['dataset_id'] = 'workplace2015'
    with pytest.raises(ValueError, match='independent source'):
        retrieval_metrics(scores, future, 5)
    assert historical_scores(source, 5 * DAY, 1).empty
