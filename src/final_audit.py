"""Read-only public aggregate audit. No datasets, models, fitting or network access."""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

from tools.check_repository_safety import FROZEN_DOCUMENTS, approved_reports, check_frozen

T33_SHA = 'ae623111871407a74185777f4d3a74c642b0dcde'
T33_RUN = '38054089678'
METRICS = ('rows', 'positive_rate', 'threshold', 'pr_auc_average_precision',
           'roc_auc', 'brier_score', 'log_loss', 'precision', 'recall', 'f1')


class AuditError(ValueError):
    """An explicitly located public evidence inconsistency."""


def require(condition, location):
    if not condition:
        raise AuditError(location + ': inconsistent public evidence')


def equal(actual, expected, location):
    if actual in (None, '') or expected in (None, ''):
        require(actual in (None, '') and expected in (None, ''), location)
    else:
        a, b = float(actual), float(expected)
        require(math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), location)


class Evidence:
    def __init__(self, root):
        self.root = Path(root)
        self.hashes = {}

    def read(self, name):
        value = (self.root / name).read_bytes()
        self.hashes[name] = hashlib.sha256(value).hexdigest()
        return value.decode('utf-8')

    def json(self, name):
        try:
            return json.loads(self.read(name))
        except json.JSONDecodeError as exc:
            raise AuditError(name + ': invalid JSON') from exc

    def csv(self, name):
        return list(csv.DictReader(self.read(name).splitlines()))


def metric_table(json_rows, csv_rows, keys, location):
    def key(row):
        return tuple(str(row[k]) for k in keys)
    indexed = {key(row): row for row in csv_rows}
    require(len(indexed) == len(csv_rows) == len(json_rows) == len({key(r) for r in json_rows}), location + '.row_keys')
    for row in json_rows:
        require(key(row) in indexed, location + '.missing_key')
        for field in METRICS:
            if field in row:
                equal(row[field], indexed[key(row)][field], location + '.' + field)


def audit_aggregates(root):
    """Check public equations and duplicated records; never imply raw reproduction."""
    e = Evidence(root)
    meta = e.json('reports/T17_SAFE_METADATA.json')
    t17 = e.json('reports/T17_METRICS.json')
    rows17 = [dict(values, scope=scope, model=model) for scope, models in t17['metrics'].items()
              for model, values in models.items()]
    metric_table(rows17, e.csv('reports/T17_METRICS.csv'), ('scope', 'model'), 'T17_METRICS')
    require(not meta['synthetic_samples_used'] and not meta['test_used_for_selection'], 'T17.provenance')
    for scope, support in meta['split'].items():
        require(support['samples'] == support['positive'] + support['negative'], 'T17.split.' + scope)
        for row in rows17:
            if row['scope'] == scope and not (scope == 'validation' and row['model'].startswith('xgboost')):
                equal(row['rows'], support['samples'], 'T17.' + scope + '.rows')
                equal(row['positive_rate'], support['positive']/support['samples'], 'T17.' + scope + '.prevalence')
    for model in ('xgboost_raw', 'xgboost_sigmoid'):
        equal(t17['metrics']['validation'][model]['rows'], meta['calibration']['tuning_rows'], 'T17.validation.tuning_rows')
    cohort = e.json('reports/window_study/T19_COHORT_MANIFEST.json')
    t22 = e.json('reports/window_study/T22_ROBUSTNESS.json')
    main = t22['main_metrics']
    metric_table(main, e.csv('reports/window_study/T22_METRICS.csv'), ('window_days', 'model'), 'T22_METRICS')
    require(cohort['candidate_interval'] == '[t-1d,t)' and cohort['shared_windows'] == [1, 3, 7], 'T19.history_contract')
    primary=e.json('reports/window_study/T21_RESULTS.json')
    metric_table(primary['test_metrics'], e.csv('reports/window_study/T21_METRICS.csv'), ('window_days','model'), 'T21_METRICS')
    for row in primary['test_metrics']:
        other=next(r for r in main if r['window_days']==row['window_days'] and r['model']==row['model'])
        for field in METRICS:
            equal(row[field], other[field], 'T21_T22.'+field)
    require(not primary['test_used_for_selection'] and not t22['test_used_for_selection'], 'T22.no_test_selection')
    for name, values in cohort['support']['sets'].items():
        require(values['rows']==values['positive']+values['negative'], 'T19.'+name+'.partition')
    support = cohort['support']['sets']['test']
    for row in main:
        equal(row['rows'], support['rows'], 'T22.test.rows')
        equal(row['positive_rate'], support['positive']/support['rows'], 'T22.test.prevalence')
        equal(row['distinct_prediction_days'], 4, 'T22.test.dates')
    for row in t22['paired_uncertainty']:
        require(row['confidence_interval'] is None and row['status'] == 'insufficient_days_for_ci', 'T22.uncertainty')
        by_window = {r['window_days']: r for r in main if r['model'] == row['model']}
        equal(row['pooled_delta_AP_7d_minus_1d'], by_window[7]['pr_auc_average_precision']-by_window[1]['pr_auc_average_precision'], 'T22.AP_delta')
    t30 = e.json('reports/asof_audit/T30_RESULTS.json')
    s = t30['summary']
    metric_table(s['metrics'], e.csv('reports/asof_audit/T30_METRICS.csv'), ('scope','model','window_days'), 'T30_METRICS')
    require(not t30['fit_or_tune_performed'] and not t30['all_candidate_performance_identified'], 'T30.scope')
    populations = {r['population']: r for r in s['population_distributions']}
    metric_table(s['population_distributions'], e.csv('reports/asof_audit/T30_SELECTION_BIAS.csv'), ('population',), 'T30_SELECTION_BIAS')
    selection=e.csv('reports/asof_audit/T30_SELECTION_BIAS.csv')
    for row in selection:
        for field in ('rows','positive','negative','unknown','unknown_rate','known_label_rate','positive_rate_reliable_only'):
            equal(row[field], populations[row['population']][field], 'T30_SELECTION_BIAS.'+field)
    for name, p in populations.items():
        require(p['rows'] == p['positive']+p['negative']+p['unknown'], 'T30.'+name+'.Unknown_partition')
        equal(p['unknown_rate'], p['unknown']/p['rows'], 'T30.'+name+'.unknown_rate')
        equal(p['positive_rate_reliable_only'], p['positive']/(p['positive']+p['negative']), 'T30.'+name+'.known_prevalence')
    all_p, old, added = (populations[n] for n in ('all_asof','old_t22','added_asof'))
    for field in ('rows','positive','negative','unknown'):
        equal(all_p[field], old[field]+added[field], 'T30.partition.'+field)
    equal(s['candidates'], all_p['rows'], 'T30.candidates')
    equal(s['reliable_labels'], all_p['positive']+all_p['negative'], 'T30.reliable_labels')
    equal(s['unknown_labels'], all_p['unknown'], 'T30.unknown_labels')
    daily = e.csv('reports/asof_audit/T30_DAILY.csv')
    for field in ('rows','positive','negative','unknown'):
        equal(sum(int(r[field]) for r in daily), all_p[field], 'T30.daily.'+field)
    equal(sum(int(r['prediction_available']) for r in daily), s['prediction_available'], 'T30.prediction_available')
    for row in daily:
        require(int(row['rows'])==int(row['positive'])+int(row['negative'])+int(row['unknown']), 'T30.daily.partition')
        original=next(r for r in s['daily_funnel'] if str(r['timestamp'])==row['timestamp'])
        for field in ('rows','positive','negative','unknown','prediction_available'):
            equal(row[field],original[field], 'T30.daily_json.'+field)
    errors = e.csv('reports/asof_audit/T30_ERRORS.csv')
    error_map = {(r['model'],int(r['window_days'])):r for r in errors}
    old_map = {(r['model'],r['window_days']):r for r in main}
    common_counts = set()
    for row in s['metrics']:
        key = (row['model'],row['window_days'])
        if row['scope'] == 'old_t22_overlap':
            for field in METRICS:
                equal(row[field], old_map[key][field], 'T30.old_t22_overlap.'+field)
        if row['scope'] == 'reliable_predicted':
            err = error_map[key]
            positive = int(err['true_positive'])+int(err['false_negative'])
            negative = int(err['true_negative'])+int(err['false_positive'])
            equal(row['rows'], positive+negative, 'T30.predicted_known.rows')
            equal(row['positive_rate'], positive/row['rows'], 'T30.predicted_known.prevalence')
            require(positive <= all_p['positive'] and negative <= all_p['negative'], 'T30.Unknown_not_negative')
            common_counts.add((row['rows'],positive,negative))
    require(len(common_counts)==1, 'T30.common_prediction_population')
    common, positives, negatives = next(iter(common_counts))
    require(common <= s['prediction_available'] <= s['candidates'] and common <= s['reliable_labels'], 'T30.set_bounds')
    require(s['prediction_available']-common <= s['unknown_labels'], 'T30.predicted_unknown_bounds')
    sources = e.json('reports/multisource/T31_SOURCE_SUMMARY.json')['sources']
    source_map = {r['dataset_id']:r for r in sources}
    require(len(source_map)==len(sources), 'T31.unique_source_namespaces')
    feasibility={r['dataset_id']:r for r in e.json('reports/multisource/T31_FEASIBILITY.json')}
    retrieval = e.csv('reports/multisource/T31_RETRIEVAL_METRICS.csv')
    groups = {}
    for row in retrieval:
        loc = 'T31.'+row['dataset_id']+'.'+row['scope']
        src = source_map[row['dataset_id']]
        require(src['status']!='source_unavailable' and src['timestamp_unit']=='seconds', loc+'.source')
        require(row['analysis_type']=='Observed Positive Retrieval', loc+'.analysis_type')
        require(not set(row)&{'precision','pr_auc_average_precision','roc_auc','brier_score'}, loc+'.no_binary_metrics')
        n, total, inside, outside, hits, unknown, actual, dates = (int(row[k]) for k in (
            'candidate_count','future_observed_positive_pairs','future_positive_pairs_in_candidate_pool',
            'future_positive_pairs_outside_candidate_pool','observed_positive_hits_at_k','unknown_candidate_count','actual_k','eligible_prediction_times'))
        require(min(n,total,inside,outside,hits,unknown,actual,dates)>=0 and n==inside+unknown and total==inside+outside, loc+'.partition')
        require(hits<=min(inside,actual) and actual<=min(n,int(row['k'])*dates), loc+'.hits')
        for field, denominator in [('observed_positive_capture_at_k',inside),('observed_positive_capture_all_at_k',total),('candidate_reach_of_observed_positives',total)]:
            numerator = inside if field=='candidate_reach_of_observed_positives' else hits
            expected = numerator/denominator if denominator else None
            equal(row[field], expected, loc+'.'+field)
        window=feasibility[row['dataset_id']]['windows'][row['window_days']]
        require(window is not None,loc+'.verified_time_window')
        if row['scope']=='common_7d':
            equal(dates,len(feasibility[row['dataset_id']]['common_7d_times']),loc+'.common_dates')
            groups.setdefault(row['dataset_id'],set()).add((n,total,inside,outside,unknown,dates))
    require(all(len(v)==1 for v in groups.values()), 'T31.common_cohort')
    require(source_map['social_evolution']['status']=='source_unavailable', 'T31.social_evolution.unavailable')
    require(source_map['reality_mining_mendeley']['timestamp_unit']!='seconds', 'T31.MIT.unverified_time')
    for row in e.csv('reports/multisource/T31_NETWORK_METRICS.csv'):
        n, edges = int(row['nodes']),int(row['edges'])
        src=source_map[row['dataset_id']]
        equal(n,src['participants'],'T31.network.nodes')
        equal(edges,src['valid_pairs'],'T31.network.edges')
        equal(row['density'],2*edges/(n*(n-1)),'T31.network.density')
        equal(row['mean_degree'],2*edges/n,'T31.network.degree')
        equal(row['unique_contact_records'],src['unique_contact_records'],'T31.network.canonical_records')
    for src in sources:
        if src['status']!='source_unavailable':
            equal(src['event_rows'],src['unique_contact_records']+src['duplicate_canonical_records'],'T31.canonical_deduplication')
    benchmark=e.csv('reports/performance/T32_BENCHMARK.csv')
    modes={}
    for row in benchmark:
        modes.setdefault(row['operation'],[]).append(row['cache_mode'])
        loc='T32.'+row['operation']+'.'+row['cache_mode']
        before,after,mem_before,mem_after=(float(row[k]) for k in ('before_median_seconds','after_median_seconds','before_peak_rss_mb','after_peak_rss_mb'))
        require(min(before,after,mem_before,mem_after)>0 and int(row['repeat_count'])==5 and row['parity_status']=='passed',loc+'.measurement')
        equal(row['speedup_ratio'],before/after,loc+'.speedup')
        equal(row['duration_reduction_pct'],100*(1-after/before),loc+'.duration')
        equal(row['memory_reduction_pct'],100*(1-mem_after/mem_before),loc+'.memory')
    require(all(sorted(v)==['cold','warm'] for v in modes.values()),'T32.cache_modes')
    parity=e.json('reports/performance/T32_PARITY.json')
    require(parity['status']=='passed' and len(parity['operation_checks'])==len(modes),'T32.parity')
    snapshot=e.json('reports/performance/T32_SNAPSHOT_AUDIT.json')
    require(snapshot['status']=='stable_archive_snapshots_only' and snapshot['ingestion_time_status']=='unavailable','T32.snapshot_scope')
    ci=e.read('CI_VERIFICATION.md')
    require(T33_SHA in ci and ('actions/runs/'+T33_RUN) in ci,'T33.CI_reference')
    return {'status':'PASS','verification_scope':'public_aggregate_verified',
            'raw_reproduction':'not_verifiable_without_local_artifacts',
            't17_test_samples':meta['split']['test']['samples'], 't22_test_samples':support['rows'],
            't30':{'candidates':s['candidates'],'reliable_labels':s['reliable_labels'],'unknown':s['unknown_labels'],
                   'predicted_reliable':common,'predicted_reliable_positive':positives,'predicted_reliable_negative':negatives},
            'retrieval_aggregate_rows':len(retrieval),'benchmark_aggregate_rows':len(benchmark),
            'ci_record_scope':'T33 recorded historical success; current-head remote status requires GitHub verification',
            'public_input_sha256':e.hashes}


def audit_public(root):
    names=approved_reports(root)|set(FROZEN_DOCUMENTS)
    current={name:(Path(root)/name).read_bytes() for name in names if (Path(root)/name).is_file()}
    try:
        count=check_frozen(root,current)
    except ValueError as exc:
        raise AuditError(str(exc)) from exc
    result=audit_aggregates(root)
    result['frozen_files_unchanged']=count
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    try:
        print(json.dumps(audit_public(args.root),indent=2,allow_nan=False))
    except (ValueError,OSError,KeyError,TypeError,ZeroDivisionError,subprocess.CalledProcessError) as exc:
        # Do not serialize input values, samples, model paths or file contents.
        print(json.dumps({'status':'FAIL','reason':str(exc) if isinstance(exc,AuditError) else type(exc).__name__}))
        raise SystemExit(1)


if __name__=='__main__':
    main()
