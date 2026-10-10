"""T31 independent, read-only exploration of real catalog sources. No model fitting."""

from collections import Counter
import hashlib
import json
from pathlib import Path

import networkx as nx
import pandas as pd
import yaml

from src.baseline_audit import sha256
from src.dataset_catalog import ADAPTER_VERSION, DatasetAdapter, directory_for, sources
from src.positive_retrieval import (ALGORITHM_VERSION, DAY, KEYS, KS, METHODS, ContactSource,
                                    complete_times, historical_scores, rank_scores, reveal_positive_pairs, retrieval_metrics)

TARGETS = ('workplace2013', 'workplace2015', 'highschool2013', 'reality_mining_mendeley', 'social_evolution')
PUBLIC_FILES = ('T31_SOURCE_SUMMARY.json', 'T31_NETWORK_METRICS.csv', 'T31_RETRIEVAL_METRICS.csv',
                'T31_FEASIBILITY.json', 'T31_PROTOCOL.json')


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')


def grouped_histogram(values, bins, *, minimum=5):
    """Only publish broad buckets with >=5 members; withhold the entire histogram otherwise."""
    counts = Counter(next(label for low, high, label in bins if low <= v <= high) for v in values)
    if any(n < minimum for n in counts.values()):
        return {'status': 'suppressed_small_groups', 'minimum_group_size': minimum, 'bins': []}
    return {'status': 'aggregate', 'minimum_group_size': minimum,
            'bins': [{'bin': label, 'count': counts[label]} for _, _, label in bins if counts[label]]}


def network_summary(source):
    """One source at a time; Arrow chunk reads. Exact canonical duplicates count once."""
    frame = source.read()
    graph = nx.from_pandas_edgelist(frame, 'user_min', 'user_max')
    pair_counts = frame.groupby(['user_min', 'user_max']).size()
    degrees = list(dict(graph.degree()).values())
    components = [len(c) for c in nx.connected_components(graph)]
    seconds = source.unit == 'seconds'
    activity = []
    repeated = None
    if seconds:
        previous = set()
        for day in range(source.first // DAY, source.last // DAY + 1):
            group = frame.loc[frame.timestamp // DAY == day]
            pairs = set(group[['user_min', 'user_max']].itertuples(index=False, name=None))
            # These source-level daily totals are public aggregates; tiny days are suppressed in full.
            activity.append({'study_day': day - source.first // DAY + 1,
                             'records': len(group) if len(group) == 0 or len(group) >= 5 else None,
                             'active_pairs': len(pairs) if len(pairs) == 0 or len(pairs) >= 5 else None,
                             'previous_day_repeated_pairs': len(pairs & previous) if len(pairs & previous) == 0 or len(pairs & previous) >= 5 else None})
            previous = pairs
        pair_days = frame.assign(day=frame.timestamp // DAY).drop_duplicates(['day', 'user_min', 'user_max']).groupby(['user_min', 'user_max']).size()
        repeated = int((pair_days >= 2).sum())
    return {'dataset_id': source.dataset_id, 'analysis_type': 'Descriptive Network Analysis',
            'nodes': len(graph), 'edges': graph.number_of_edges(), 'unique_contact_records': len(frame),
            'components': len(components), 'largest_component_nodes': max(components, default=0),
            'density': nx.density(graph), 'mean_degree': sum(degrees) / len(degrees) if degrees else None,
            'degree_histogram': grouped_histogram(degrees, [(0, 5, '0–5'), (6, 20, '6–20'), (21, 50, '21–50'), (51, float('inf'), '>50')]),
            'pair_record_histogram': grouped_histogram(pair_counts, [(1, 5, '1–5'), (6, 20, '6–20'), (21, 100, '21–100'), (101, float('inf'), '>100')]),
            'activity': activity, 'pairs_active_on_multiple_days': repeated,
            'time_activity_status': 'relative_study_days' if seconds else 'unavailable_unverified_tick_scale',
            'scope': 'Entire archived observed graph; never used as a historical ranking graph.'}


def load_source(root, config, spec):
    path = directory_for(root, config, spec) / spec['filename']
    base = {k: spec.get(k) for k in ['dataset_id', 'name', 'source_url', 'download_url', 'citation', 'licence', 'scan_coverage_evidence']}
    if spec['dataset_id'] == 'highschool2013':
        base['download_url'] = 'https://sociopatterns.org/assets/data/HighSchool2013_proximity_net.csv.gz'
    base['source_verification_date'] = '2026-10-10'
    base['schema'] = 'timestamp,user_a,user_b,class_a,class_b' if spec['format'] == 'highschool' else spec.get('column_order', 'unverified actual header')
    base.update(file_path=str(path.relative_to(root)), adapter_version=ADAPTER_VERSION,
                independent_online_logs=False, timestamp_unit=spec.get('timestamp_unit', 'seconds' if spec['format'] == 'highschool' else 'unverified'),
                timestamp_encoding='UNIX ctime seconds' if spec['dataset_id'] == 'highschool2013' else 'actual encoding unverified' if spec['dataset_id'] == 'social_evolution' else 'relative integer; epoch mapping unverified',
                timestamp_origin_policy='Study Day from floor(first/86400) only if seconds verified; no civil dates or tick conversion',
                deduplication='Canonical (dataset,timestamp,minID,maxID); exact repeats once; different pair/time retained.')
    if not path.is_file():
        base.update(status='source_unavailable', descriptive_status='source_unavailable', retrieval_status='source_unavailable',
                    reason=spec.get('access_note', 'Local raw file missing; no synthetic substitution.'), file_hash=None)
        return base, None, None
    if spec['dataset_id'] == 'social_evolution' and not (spec.get('source_verified') and spec.get('licence_verified') and spec.get('column_mapping') and spec.get('timestamp_unit') == 'seconds' and spec.get('raw_only_provenance_verified')):
        base.update(status='blocked', descriptive_status='blocked', retrieval_status='blocked', reason='Actual file schema/time/license/provenance unverified.')
        return base, None, None
    # Existing verified v3 caches are reused read-only; new caches, if needed, stay in T31's own directory.
    checksum = sha256(path)
    matches = []
    for manifest in (Path(root) / config['paths']['processed'] / 'catalog' / spec['dataset_id']).glob('v3-*/dataset_manifest.json'):
        record = json.loads(manifest.read_text())
        spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]
        if record['file_hash'] == checksum and manifest.parent.name.endswith(spec_hash):
            if sha256(manifest.parent / 'contacts.parquet') != record['processed_sha256']:
                raise ValueError('Existing catalog checksum mismatch; preserve and investigate.')
            matches.append((manifest.parent / 'contacts.parquet', record))
    if matches:
        parquet, record = matches[0]
    else:
        output = Path(root) / config['paths']['processed'] / 'multisource/catalog'
        record = DatasetAdapter(spec).inspect(path, output)
        manifests = list((output / spec['dataset_id']).glob('*/dataset_manifest.json'))
        parquet = next(p.parent / 'contacts.parquet' for p in manifests if json.loads(p.read_text())['processed_sha256'] == record['processed_sha256'])
    source = ContactSource(parquet, spec['dataset_id'], record['first_timestamp'], record['last_timestamp'], record['time_unit'])
    base.update({k: record[k] for k in ['file_hash', 'processed_sha256', 'participants', 'valid_pairs', 'raw_rows', 'event_rows',
                                      'first_timestamp', 'last_timestamp', 'span_days', 'days_without_contact_records']})
    base.update(descriptive_status='descriptive_ready', status='descriptive_ready')
    return base, source, record


def aggregate_retrieval(rows):
    if not rows:
        return []
    frame = pd.DataFrame(rows)
    result = []
    for keys, group in frame.groupby(['dataset_id', 'scope', 'window_days', 'method', 'k'], sort=True):
        names = ['dataset_id', 'scope', 'window_days', 'method', 'k']
        item = dict(zip(names, keys))
        item['window_days'], item['k'] = int(item['window_days']), int(item['k'])
        if 'historical_network_density' in group:
            item['mean_historical_network_density'] = float(group.historical_network_density.mean())
        for col in ['candidate_count', 'future_observed_positive_pairs', 'future_positive_pairs_in_candidate_pool',
                    'future_positive_pairs_outside_candidate_pool', 'observed_positive_hits_at_k', 'unknown_candidate_count', 'actual_k']:
            item[col] = int(group[col].sum())
        denom = item['future_positive_pairs_in_candidate_pool']
        total = item['future_observed_positive_pairs']
        item.update(eligible_prediction_times=len(group), nonempty_candidate_times=int((group.candidate_count > 0).sum()),
                    times_with_positive_pool=int((group.future_positive_pairs_in_candidate_pool > 0).sum()),
                    observed_positive_capture_at_k=item['observed_positive_hits_at_k'] / denom if denom else None,
                    observed_positive_capture_all_at_k=item['observed_positive_hits_at_k'] / total if total else None,
                    candidate_reach_of_observed_positives=denom / total if total else None,
                    evidence_status='descriptive_only_insufficient_times' if (group.future_positive_pairs_in_candidate_pool > 0).sum() < 3 else 'descriptive_only',
                    analysis_type='Observed Positive Retrieval')
        # Even aggregate Top-K hits may be <5. Suppress counts AND derived ratios as one disclosure family.
        if any(0 < item[col] < 5 for col in ['candidate_count', 'future_observed_positive_pairs', 'future_positive_pairs_in_candidate_pool',
                                           'future_positive_pairs_outside_candidate_pool', 'observed_positive_hits_at_k', 'unknown_candidate_count']):
            for col in ['candidate_count', 'future_observed_positive_pairs', 'future_positive_pairs_in_candidate_pool',
                        'future_positive_pairs_outside_candidate_pool', 'observed_positive_hits_at_k', 'unknown_candidate_count',
                        'observed_positive_capture_at_k', 'observed_positive_capture_all_at_k', 'candidate_reach_of_observed_positives', 'actual_k']:
                item[col] = None
            item['disclosure_status'] = 'suppressed_small_counts_and_ratios'
        else:
            item['disclosure_status'] = 'aggregate_only'
        result.append(item)
    return result


def run_study(root):
    root = Path(root)
    config = yaml.safe_load((root / 'configs/default.yaml').read_text())
    registry = {s['dataset_id']: s for s in sources(root)}
    protocol = dict(task='T31', algorithm_version=ALGORITHM_VERSION, adapter_version=ADAPTER_VERSION,
                    candidate_interval='[t-1d,t)', historical_interval='[t-window,t)', future_interval='(t,t+24h]',
                    windows=[1, 3, 7], ks=list(KS), methods=list(METHODS), snapshot_hour=8,
                    scores={'historical_frequency': 'unique canonical records / window days, descending',
                            'last_contact_recency': 'last timestamp - t, descending', 'common_neighbors': 'shared neighbors in bounded undirected historical graph, descending'},
                    ties='ascending dataset_id,user_min,user_max; deterministic',
                    scopes='per_window; common_7d with identical 1d candidates/times across windows when complete',
                    unknown='No observed future contact remains Unknown; no binary labels or classification metrics.',
                    aggregation='sum snapshot-pair hits / sum observed positive snapshot-pairs; repeated pairs across dates counted separately',
                    evidence='Descriptive only, <3 positive-pool dates flagged; no significance or optimized rule/window/K.',
                    disclosure='No individual/pair IDs; small (<5 nonzero) public histogram/count families suppressed.',
                    event_availability='Event time only, no arrival logs; not a real-time ingestion replay.',
                    copenhagen='Primary binary source remains frozen T17/T22/T30; no new fit or comparison ranking.',
                    sources=[])
    code_root = Path(__file__).resolve().parents[1]
    protocol['code_sha256'] = {name: sha256(code_root / name) for name in ['src/positive_retrieval.py', 'src/multisource_exploration.py', 'src/multisource_report.py', 'src/dataset_catalog.py']}
    protocol['source_checks'] = {'date': '2026-10-10', 'workplace2013': 'Official page: seconds,20s interval,CC0; actual linked URL matches local source.',
                               'workplace2015': 'Official page: seconds,20s interval,CC0; actual linked URL matches local source.',
                               'highschool2013': 'Official page: UNIXctime seconds,20s interval,CC BY-NC-SA; actual linked URL matches local source.',
                               'reality_mining_mendeley': 'Publisher version1 CC BY4.0 description lacks processed tick-to-time transformation; no units borrowed from other versions.',
                               'social_evolution': 'Official overview/dictionary live web fetch returned502; no actual file/license/timezone verified.'}
    loaded = []
    for name in TARGETS:
        base, source, record = load_source(root, config, registry[name])
        if source:
            times = {str(w): complete_times(source, w) for w in (1, 3, 7)} if source.unit == 'seconds' else {str(w): [] for w in (1, 3, 7)}
            base['prediction_times'] = times
            protocol['sources'].append({k: base[k] for k in ['dataset_id', 'file_hash', 'processed_sha256', 'timestamp_unit', 'prediction_times']})
        else:
            protocol['sources'].append({'dataset_id': name, 'status': base['status']})
        loaded.append((base, source, record))
    missing_required = [b['dataset_id'] for b, s, _ in loaded if b['dataset_id'].startswith('workplace') and s is None]
    if missing_required:
        raise ValueError('BLOCKED: required real Workplace source missing: ' + ','.join(missing_required))
    # Freeze full rules/time lists/hash provenance BEFORE any ranking or future reveal.
    run_id = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()[:16]
    private = root / config['paths']['processed'] / 'multisource' / run_id
    private.mkdir(parents=True, exist_ok=True)
    frozen = private / 'PROTOCOL_FROZEN.json'
    if frozen.exists() and json.loads(frozen.read_text()) != protocol:
        raise ValueError('Protocol integrity conflict.')
    if not frozen.exists():
        _write_json(frozen, protocol)
    networks, detailed, source_rows, feasibility = [], [], [], []
    for base, source, record in loaded:
        name = base['dataset_id']
        if source is None:
            source_rows.append(base)
            feasibility.append({'dataset_id': name, 'status': base['status'], 'reason': base['reason']})
            continue
        network = network_summary(source)
        networks.append(network)
        base['unique_contact_records'] = network['unique_contact_records']
        base['duplicate_canonical_records'] = record['event_rows'] - network['unique_contact_records']
        if source.unit != 'seconds':
            base.update(status='time_unit_unverified', retrieval_status='time_unit_unverified',
                        reason='No publisher dictionary or transformation maps processed ticks to seconds; original study duration is not a mapping.')
            feasibility.append({'dataset_id': name, 'status': 'time_unit_unverified', 'windows': {str(w): None for w in (1, 3, 7)}})
        else:
            by_window = base['prediction_times']
            common = by_window['7']
            window_status = {}
            for w in (1, 3, 7):
                times = by_window[str(w)]
                valid_times = 0
                positive_times = 0
                for t in times:
                    scores = historical_scores(source, t, w)
                    # Freeze scores/rank inputs locally before explicit future access. No participant results published.
                    filename = private / f'{name}-{w}d-{t}-scores.parquet'
                    if filename.exists():
                        pd.testing.assert_frame_equal(pd.read_parquet(filename), scores)
                    else:
                        scores.to_parquet(filename, index=False)
                    frozen_scores = pd.read_parquet(filename)
                    rankings = {method: rank_scores(frozen_scores, method) for method in METHODS}
                    future = reveal_positive_pairs(source, t, backtest=True)
                    future.to_parquet(private / f'{name}-{t}-future.parquet', index=False)
                    valid_times += int(not scores.empty)
                    pool = set(scores[KEYS].itertuples(index=False, name=None)) & set(future[KEYS].itertuples(index=False, name=None))
                    positive_times += int(bool(pool))
                    for method in METHODS:
                        ranking = rankings[method]
                        for k in KS:
                            row = dict(dataset_id=name, timestamp=t, window_days=w, method=method,
                                       historical_network_density=scores.attrs.get('historical_network', {}).get('density', 0.0),
                                       **retrieval_metrics(ranking, future, k))
                            detailed.append(dict(row, scope='per_window'))
                            if t in common:
                                detailed.append(dict(row, scope='common_7d'))
                window_status[str(w)] = dict(complete_prediction_times=len(times), nonempty_candidate_times=valid_times, positive_pool_times=positive_times,
                                            status='positive_retrieval_ready' if positive_times >= 3 else 'insufficient_history',
                                            reason='Calendar completeness is not continuous badge coverage; fewer than3 positive-pool dates yield only limited descriptive evidence.' if positive_times < 3 else 'Observed-positive retrieval only; unrecorded pairs remain Unknown.')
            base.update(status='positive_retrieval_ready' if any(x['positive_pool_times'] >= 3 for x in window_status.values()) else 'insufficient_history',
                        retrieval_status=window_status, reason='No reliable independent online/scan logs: no binary prediction evaluation.')
            feasibility.append({'dataset_id': name, 'status': base['status'], 'windows': window_status, 'common_7d_times': common})
        source_rows.append(base)
    for base, source, _ in loaded:
        if source is not None:
            raw = root / base['file_path']
            if sha256(raw) != base['file_hash'] or sha256(source.path) != base['processed_sha256']:
                raise ValueError('Source changed during study; do not publish inconsistent results.')
    # Every private intermediate stays ignored. Aggregates are recomputed directly from these rows.
    pd.DataFrame(detailed).to_parquet(private / 'retrieval_rows.parquet', index=False)
    result = dict(run_id=run_id, source_kind='real_public_dataset', protocol=protocol, sources=source_rows,
                  networks=networks, retrieval=aggregate_retrieval(detailed), feasibility=feasibility)
    _write_json(private / 'RESULTS.json', result)
    from src.multisource_report import write_report
    write_report(result, root, private)
    return result


if __name__ == '__main__':
    result = run_study(Path(__file__).resolve().parents[1])
    print(json.dumps({'run_id': result['run_id'], 'sources': [{k: s.get(k) for k in ('dataset_id', 'status', 'participants', 'event_rows', 'valid_pairs')} for s in result['sources']],
                      'aggregate_retrieval_rows': len(result['retrieval'])}, indent=2))
