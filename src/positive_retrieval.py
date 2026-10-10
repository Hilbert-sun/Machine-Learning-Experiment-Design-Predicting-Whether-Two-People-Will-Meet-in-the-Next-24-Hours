"""T31 fixed, untrained rankings and explicit observed-positive reveal; no negatives."""

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import pandas as pd
import pyarrow.dataset as ds

from src.pipeline_cache import parquet_frames

DAY = 86400
ALGORITHM_VERSION = 1
KEYS = ['dataset_id', 'user_min', 'user_max']
METHODS = ('historical_frequency', 'last_contact_recency', 'common_neighbors')
KS = (5, 10, 20)


@dataclass(frozen=True)
class ContactSource:
    path: Path
    dataset_id: str
    first: int
    last: int
    unit: str

    def read(self, expression=None):
        frames = list(parquet_frames(self.path, ['dataset_id', 'timestamp', 'user_min', 'user_max'], expression))
        frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['timestamp', *KEYS])
        if not frame.empty:
            if set(frame.dataset_id) != {self.dataset_id}:
                raise ValueError('Mixed dataset namespaces are forbidden.')
            if (frame.user_min >= frame.user_max).any() or (frame.user_min < 0).any():
                raise ValueError('Require valid canonical undirected pairs.')
        return frame.drop_duplicates(['timestamp', *KEYS])

    def require_seconds(self):
        if self.unit != 'seconds':
            raise ValueError('time_unit_unverified: no 24h conversion permitted.')


def complete_times(source, window):
    source.require_seconds()
    if window not in (1, 3, 7):
        raise ValueError('Only prespecified 1/3/7d windows are supported.')
    return [d * DAY + 28800 for d in range(source.first // DAY, source.last // DAY + 1)
            if d * DAY + 28800 - window * DAY >= source.first and d * DAY + 28800 + DAY <= source.last]


def historical_scores(source, t, window):
    """Does not consult future contacts, future completeness or labels. T itself is excluded."""
    source.require_seconds()
    if window not in (1, 3, 7) or t - window * DAY < source.first:
        raise ValueError('insufficient_history: incomplete declared historical source span.')
    past = source.read((ds.field('timestamp') >= t - window * DAY) & (ds.field('timestamp') < t))
    candidates = past.loc[past.timestamp >= t - DAY, KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    columns = [*KEYS, *METHODS]
    if candidates.empty:
        return pd.DataFrame(columns=columns)
    stats = past.groupby(KEYS).timestamp.agg(['count', 'max']).reset_index()
    scored = candidates.merge(stats, on=KEYS, validate='one_to_one')
    graph = nx.from_pandas_edgelist(past, 'user_min', 'user_max')
    scored['historical_frequency'] = scored['count'] / window
    scored['last_contact_recency'] = scored['max'] - t  # descending: less negative is more recent
    scored['common_neighbors'] = [len(set(graph[a]) & set(graph[b])) for a, b in scored[['user_min', 'user_max']].itertuples(index=False, name=None)]
    result = scored[columns].reset_index(drop=True)
    result.attrs['historical_network'] = {'nodes': len(graph), 'edges': graph.number_of_edges(), 'density': nx.density(graph)}
    return result


def rank_scores(scores, method):
    if method not in METHODS:
        raise ValueError('Unknown fixed scoring rule.')
    if scores[method].isna().any():
        raise ValueError('unavailable: scoring evidence missing; no artificial score.')
    return scores.sort_values([method, *KEYS], ascending=[False, True, True, True], kind='stable').reset_index(drop=True)


def reveal_positive_pairs(source, t, *, backtest=False):
    if backtest is not True:
        raise ValueError('Explicit backtest required before future IO.')
    source.require_seconds()
    if t + DAY > source.last:
        raise ValueError('incomplete_future_span: no complete 24h recorded source span.')
    return source.read((ds.field('timestamp') > t) & (ds.field('timestamp') <= t + DAY))[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)


def retrieval_metrics(ranking, future, k):
    if k not in KS:
        raise ValueError('Only frozen K=5/10/20 are supported.')
    for frame in (ranking, future):
        if frame.duplicated(KEYS).any():
            raise ValueError('Duplicate pair keys.')
    namespaces = set(ranking.dataset_id) | set(future.dataset_id)
    if len(namespaces) > 1:
        raise ValueError('Cannot combine independent source populations.')
    candidates = set(ranking[KEYS].itertuples(index=False, name=None))
    positives = set(future[KEYS].itertuples(index=False, name=None))
    pool = candidates & positives
    hits = len(set(ranking.head(k)[KEYS].itertuples(index=False, name=None)) & positives)
    status = 'no_candidates' if not candidates else 'no_future_observed_positives' if not positives else 'no_positive_in_candidate_pool' if not pool else 'observed_positive_retrieval'
    return dict(k=k, actual_k=min(k, len(ranking)), candidate_count=len(candidates),
                future_observed_positive_pairs=len(positives), future_positive_pairs_in_candidate_pool=len(pool),
                future_positive_pairs_outside_candidate_pool=len(positives - candidates),
                observed_positive_hits_at_k=hits,
                observed_positive_capture_at_k=hits / len(pool) if pool else None,
                observed_positive_capture_all_at_k=hits / len(positives) if positives else None,
                candidate_reach_of_observed_positives=len(pool) / len(positives) if positives else None,
                unknown_candidate_count=len(candidates - positives), status=status)
