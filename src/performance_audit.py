"""T32 real parity and sanitized performance summaries; old research files stay read-only."""

import json
from pathlib import Path
import pickle
import statistics

import numpy as np
import pandas as pd

from src.performance_benchmark import atomic_json, digest

RTOL = ATOL = 1e-12


def assert_equal(before, after):
    if isinstance(before, pd.DataFrame):
        pd.testing.assert_frame_equal(before, after, rtol=RTOL, atol=ATOL)
        exact = [c for c in before.columns if pd.api.types.is_integer_dtype(before[c]) or c in
                 {'pair_contact_count', 'pair_contact_bins', 'pair_contact_days', 'participant_a_activity', 'participant_b_activity',
                  'common_neighbors', 'network_degree_a', 'network_degree_b', 'observed_history_days'}]
        pd.testing.assert_frame_equal(before[exact], after[exact], check_exact=True)
    elif isinstance(before, dict):
        assert set(before)==set(after), (set(before)-set(after), set(after)-set(before))
        for key in before:
            assert_equal(before[key], after[key])
    elif isinstance(before, (list, tuple)):
        assert len(before)==len(after)
        for a, b in zip(before, after):
            assert_equal(a, b)
    elif isinstance(before, (int, bool, str)) or before is None:
        assert before == after, (before, after)
    elif isinstance(before, (float, np.floating)):
        np.testing.assert_allclose(before, after, rtol=RTOL, atol=ATOL, equal_nan=True)
    else:
        assert before == after


def verify_preservation(root):
    root=Path(root)
    before=json.loads((root/'data/processed/performance/T32_PRESERVATION.json').read_text())
    allowed={'.gitignore','AGENTS.md','TASKS.md','PROGRESS.md','README.md',
             'src/asof_inference.py','src/asof_ui.py','src/pipeline_cache.py','src/positive_retrieval.py',
             'src/multisource_exploration.py','src/multisource_report.py','src/multisource_ui.py','src/time_machine.py','src/time_machine_ui.py'}
    protected={name: h for name,h in before.items() if name not in allowed}
    changed=[name for name,h in protected.items() if not (root/name).is_file() or digest(root/name)!=h]
    assert not changed, 'STOP: frozen artifact changed: '+str(changed)
    reports={name:h for name,h in before.items() if name.startswith('reports/')}
    return {'protected_files':len(protected),'frozen_public_and_private_reports':len(reports),'status':'unchanged',
            'report_hashes_sha256':digest(root/'data/processed/performance/T32_PRESERVATION.json')}


def verify_real_research(root):
    import os
    from src.asof_audit import _frozen_inputs, predict_snapshot, reveal_snapshot, summarize, verify_audit
    from src.preprocessing import cached_dataset
    from src.window_cohort import KEYS
    from src.multisource_exploration import run_study
    root=Path(root)
    directory=root/'data/processed/performance/parity';directory.mkdir(parents=True,exist_ok=True)
    os.environ['ENCOUNTER_CACHE_ROOT']=str(directory/'cache')
    t30=root/'data/processed/asof_audit/7521ebdeb40f0b55'
    original=json.loads((t30/'RESULTS.json').read_text())
    models,_=_frozen_inputs(root)
    processed=cached_dataset(root/'data/raw/copenhagen/bt_symmetric.csv','Copenhagen',root/'data/processed')
    before=pd.read_parquet(t30/'predictions.parquet').sort_values(KEYS).reset_index(drop=True)
    actual=pd.concat([predict_snapshot(processed,int(t),models) for t in sorted(before.timestamp.unique())],ignore_index=True).sort_values(KEYS).reset_index(drop=True)
    assert_equal(before,actual)
    actual.to_parquet(directory/'T32_T30_PREDICTIONS.parquet',index=False)  # Private predictions frozen before outcome comparison.
    outcomes=pd.concat([reveal_snapshot(processed,int(t),g,min_scan_coverage=.5,backtest=True) for t,g in actual.groupby('timestamp')],ignore_index=True).sort_values(KEYS).reset_index(drop=True)
    samples=pd.read_parquet(t30/'samples.parquet').sort_values(KEYS).reset_index(drop=True)
    assert_equal(samples[outcomes.columns],outcomes)
    current=samples.copy()
    for column in actual.columns:
        current[column]=actual[column]
    specs=[m.spec() for m in models]
    assert_equal(original['summary'],summarize(current,specs))
    assert verify_audit(t30)
    result=run_study(root)
    frozen=json.loads((root/'data/processed/multisource/6d5df52b7fd76419/RESULTS.json').read_text())
    for key in ('sources','networks','retrieval','feasibility'):
        assert_equal(frozen[key],result[key])
    from src.dataset_catalog import sources as catalog_sources
    from src.multisource_exploration import load_source
    import pyarrow.dataset as ds
    import networkx as nx
    import yaml
    config=yaml.safe_load((root/'configs/default.yaml').read_text())
    exact_network_sources=[]
    for spec in catalog_sources(root):
        if spec['dataset_id'] not in {'workplace2013','workplace2015','highschool2013','reality_mining_mendeley'}:
            continue
        _,source,_=load_source(root,config,spec)
        columns=['dataset_id','timestamp','user_min','user_max']
        reference=pd.concat([batch.to_pandas() for batch in ds.dataset(source.path,format='parquet').to_batches(columns=columns)],ignore_index=True).drop_duplicates(['timestamp','dataset_id','user_min','user_max']).reset_index(drop=True)
        current_source=source.read()
        pd.testing.assert_frame_equal(reference,current_source,check_exact=True)
        pd.testing.assert_series_equal(reference.groupby(['user_min','user_max']).size(),current_source.groupby(['user_min','user_max']).size(),check_exact=True)
        g1=nx.from_pandas_edgelist(reference,'user_min','user_max');g2=nx.Graph()
        for chunk in source.iter_unique():
            g2.add_edges_from(chunk.groupby(['user_min','user_max']).size().index)
        assert set(g1)==set(g2) and {frozenset(e) for e in g1.edges}=={frozenset(e) for e in g2.edges}
        assert dict(g1.degree())==dict(g2.degree())
        assert {frozenset(c) for c in nx.connected_components(g1)}=={frozenset(c) for c in nx.connected_components(g2)}
        exact_network_sources.append(spec['dataset_id'])
    optimized=root/'data/processed/performance/research'/result['run_id']
    scores=list((root/'data/processed/multisource/6d5df52b7fd76419').glob('*-scores.parquet'))
    for old in scores:
        first=pd.read_parquet(old);second=pd.read_parquet(optimized/old.name)
        assert_equal(first,second)
        from src.positive_retrieval import METHODS,rank_scores
        for method in METHODS:
            assert_equal(rank_scores(first,method),rank_scores(second,method))
    return {'T30':{'status':'passed','candidate_rows':len(actual),'known':original['summary']['reliable_labels'],
                  'unknown':original['summary']['unknown_labels'],'dates':4,'model_window_combinations':len(models),
                  'checks':'per-row probabilities, exact masks/keys/counts, daily funnels, all metrics/reliability/subgroups/aggregates'},
            'T31':{'status':'passed','score_files':len(scores),'aggregate_rows':len(result['retrieval']),
                   'exact_full_unique_records_pair_counts_node_edge_degree_component_sources':exact_network_sources,
                   'optimized_run_id':result['run_id'],'checks':'all source states/topology/unique records, scores, complete rankings, hits/capture/reach and aggregates'}}


def verify_payloads(directory, stage):
    baseline=json.loads((directory/'T32_BASELINE.json').read_text())
    checks=[]
    for operation in [r['operation'] for r in baseline['operations']]:
        suffix=operation.replace(':','-')+'-0.pickle'
        # Only self-generated local parity receipts are read, never downloaded/uploaded pickle inputs.
        with (directory/('baseline-cold-'+suffix)).open('rb') as stream:
            before=pickle.load(stream)
        with (directory/(stage+'-cold-'+suffix)).open('rb') as stream:
            after=pickle.load(stream)
        if operation=='predict_models':
            fields=['dataset_id','timestamp','pair','mode','models','cases','future_label_policy']
            assert_equal({k:before[k] for k in fields},{k:after[k] for k in fields})
            assert after['data_snapshot']['ingestion_time_status']=='unavailable'
            assert after['prediction_schema_version']==3
        else:
            assert_equal(before,after)
        checks.append({'operation':operation,'status':'passed'})
    return checks


def publish(root, stage='optimized_release'):
    root=Path(root);local=root/'data/processed/performance'
    baseline=json.loads((local/'T32_BASELINE.json').read_text())
    receipt=json.loads((local/'T32_BASELINE_RECEIPT.json').read_text())
    assert digest(local/'T32_BASELINE.json')==receipt['baseline_sha256']
    protected=verify_preservation(root)
    operations=verify_payloads(local,stage)
    real=verify_real_research(root)
    protected=verify_preservation(root)
    rows=[]
    for mode,before_name,after_name in [('cold','T32_BASELINE.json',f'T32_{stage.upper()}.json'),
                                        ('warm','T32_BASELINE_REFERENCE_WARM.json',f'T32_{stage.upper()}_WARM.json')]:
        first=json.loads((local/before_name).read_text());second=json.loads((local/after_name).read_text())
        assert first['environment']==second['environment'],'Different measurement environments'
        assert first['inputs']==second['inputs'],'Different real inputs'
        for a,b in zip(first['operations'],second['operations']):
            assert a['operation']==b['operation'] and a['repeat_count']>=5 and b['repeat_count']>=5
            operation=a['operation'];dataset=operation.split(':')[-1] if ':' in operation else 'aggregate_reports' if operation=='public_reports' else 'copenhagen'
            spec=first['inputs']['sources'].get(dataset)
            if spec:
                input_rows=spec['rows'];source_hash=spec['file_hash'];input_bytes=Path(spec['path']).stat().st_size
            elif dataset=='copenhagen':
                cop=first['inputs']['copenhagen'];input_rows=sum(v['rows'] for v in cop['files'].values())
                source_hash=';'.join(v['sha256'] for v in cop['files'].values())
                input_bytes=sum(Path(v['path']).stat().st_size for v in cop['files'].values())
            else:
                input_rows=len(pd.read_csv(root/'reports/multisource/T31_RETRIEVAL_METRICS.csv'));source_hash=digest(root/'reports/multisource/T31_SOURCE_SUMMARY.json')
                input_bytes=sum((root/'reports/multisource'/name).stat().st_size for name in ['T31_SOURCE_SUMMARY.json','T31_RETRIEVAL_METRICS.csv','T31_FEASIBILITY.json'])
            time_pct=100*(1-b['median_seconds']/a['median_seconds'])
            memory_pct=100*(1-b['median_peak_rss_mb']/a['median_peak_rss_mb'])
            rows.append(dict(operation=operation,dataset=dataset,input_rows=input_rows,input_inventory_bytes=input_bytes,source_hash=source_hash,
                             before_median_seconds=a['median_seconds'],after_median_seconds=b['median_seconds'],
                             before_seconds_range=json.dumps(a['seconds_range']),after_seconds_range=json.dumps(b['seconds_range']),
                             before_peak_rss_mb=a['median_peak_rss_mb'],after_peak_rss_mb=b['median_peak_rss_mb'],
                             before_peak_rss_range=json.dumps([min(s['peak_rss_mb'] for s in a['samples']),max(s['peak_rss_mb'] for s in a['samples'])]),
                             after_peak_rss_range=json.dumps([min(s['peak_rss_mb'] for s in b['samples']),max(s['peak_rss_mb'] for s in b['samples'])]),
                             speedup_ratio=a['median_seconds']/b['median_seconds'],duration_reduction_pct=time_pct,memory_reduction_pct=memory_pct,
                             before_parquet_reads=statistics.median(s['parquet_reads'] for s in a['samples']),
                             after_parquet_reads=statistics.median(s['parquet_reads'] for s in b['samples']),
                             after_private_payload_reads=statistics.median(s['cache'].get('payload_reads',0) for s in b['samples']),
                             before_repeated_scans=statistics.median(s['repeated_scans'] for s in a['samples']),
                             after_repeated_scans=statistics.median(s['repeated_scans'] for s in b['samples']),
                             before_processed_rows=statistics.median(s['materialized_rows'] for s in a['samples']),
                             after_processed_rows=statistics.median(s['materialized_rows'] for s in b['samples']),
                             after_cache=json.dumps(b['samples'][0]['cache'],sort_keys=True),cache_mode=mode,repeat_count=b['repeat_count'],parity_status='passed',
                             regression_exception='Additional exact-hash/pinned-copy/cache verification and model object isolation overhead; explicit security tradeoff' if time_pct < -10 else 'none'))
    goals=[r for r in rows if r['cache_mode']=='cold' and (r['memory_reduction_pct']>=25 or r['duration_reduction_pct']>=30)]
    assert goals,'Measured cold-to-cold performance target not achieved; keep task IN_PROGRESS/BLOCKED'
    output=root/'reports/performance';output.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(output/'T32_BENCHMARK.csv',index=False)
    parity={'status':'passed','rtol':RTOL,'atol':ATOL,'integer_counts_and_candidate_order':'exact','operation_checks':operations,
            'frozen_preservation':protected,'real_research':real,
            'intentional_record_changes':['prediction_schema_version2→3; source snapshot binding/time/ingestion status added; cases/models/label coverage policy unchanged']}
    atomic_json(output/'T32_PARITY.json',parity)
    audit={'version':1,'status':'stable_archive_snapshots_only','ingestion_time_status':'unavailable',
           'source_identity':'namespace, normalized content hashes, processing/report policy, model/evidence content, protocol and prediction time',
           'reads':'byte-verified read-only copied inputs; nested calculations require bound dependency subset',
           'publication':'versioned hash-verified JSON/Parquet bundles; final pointer after outer snapshot check; interruptions keep prior pointers; corrupt inactive snapshot copies re-pin the same verified source into a new version',
           'change_response':'source_snapshot_changed; discard pending cache pointers; do not display predictions; no silent retry',
           'limitations':['No cross-file atomic capture guarantee from live writers; stable archive bytes required.',
                          'No atomic live acquisition, ingestion chronology or adversarial same-owner immutable filesystem guarantee.',
                          'A writer may change the live files after final verification; final-check/publication TOCTOU remains.',
                          'Concurrent processes may publish separate valid versions; no global multi-request transaction.',
                          'Orphan versions may remain after interruption; automatic eviction/retention not implemented.'],
           'preservation':protected}
    atomic_json(output/'T32_SNAPSHOT_AUDIT.json',audit)
    environment=baseline['environment'];environment['cpu']=receipt['cpu'];environment['physical_memory_bytes']=receipt['physical_memory_bytes']
    text='# T32 — Performance, Safe Caching & Snapshot Audit\n\n'
    text+='Actual local measurements on the same machine and identical hash-bound real inputs;5 independent processes per operation/cache state. Cold means empty APPLICATION cache, not forced cold OS pages. Wall time excludes imports/setup; RSS includes interpreter/imports and native allocations (resource.ru_maxrss, not tracemalloc). Warm RSS includes priming. CPU '+receipt['cpu']+', physical memory16GiB. Baseline available-memory proxy(free+inactive+speculative pages)='+str(receipt['available_memory_proxy_bytes'])+' bytes, not guaranteed allocatable RAM. OS cache and other desktop activity are uncontrolled; ranges expose variation. Warm reference executes exported immutable T31 commit5c74553 code; initial cold baseline was frozen BEFORE performance edits. Intermediate optimized/optimized_v2 runs are diagnostic only; final comparisons use '+stage+'.\n\n'
    text+='| Operation | Cache | Before seconds | After seconds | Before RSS MiB | After RSS MiB | Time reduction % | RSS reduction % |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n'
    for r in rows:
        text+=f"|{r['operation']}|{r['cache_mode']}|{r['before_median_seconds']:.6f}|{r['after_median_seconds']:.6f}|{r['before_peak_rss_mb']:.2f}|{r['after_peak_rss_mb']:.2f}|{r['duration_reduction_pct']:.2f}|{r['memory_reduction_pct']:.2f}|\n"
    text+='\nPerformance target achieved on cold paths: '+', '.join(r['operation'] for r in goals)+'. Negative reductions are regressions, not gains. Cold feature/retrieval/candidate requests now pay for cryptographic source binding, verified copied snapshots, private bundle validation/publication and model isolation; >10% regressions are explicit security exceptions, not hidden or compared with warm hits. Attribution to additional checks is an inference from code, not a separately timed stage decomposition. Very short operations have large relative noise; no cross-machine or significance claim. Raw5-repeat records, source hashes/input sizes, CPU/memory receipt and immutable baseline digest remain in ignored data/processed/performance.\n\n'
    text+='Optimized modules: ContactSource incremental canonical dedup and streaming graph aggregation; Arrow readahead bounded to1; bounded_history reuses pre-t raw scans but frozen T20 math remains unchanged for independent1/3/7d budgets. As-of candidate/features use content-version private cache; Time Machine primes multi-window inputs once but verifies every model/time/coverage/clock contract on every prediction. Model clones prevent caller/session mutation. Only aggregate public JSON/CSV parsing is memoized process-wide with content hashes. DatasetCatalog already scans only on explicit action; HistoryWindowStudy statistical/evaluation and broad invalidation logic remain unchanged because no measured reason justified rewriting frozen study paths. Small JSON metadata parsing reuses exact bytes. Cache debug counters and explicit unavailable ingestion status appear in Time Machine.\n\n'
    text+='Parquet counts are logical physical source opens through chunk IO/pandas Parquet reads; virtual bounded-history slices are not additional physical scans. Private SafeCache Arrow payload verification reads are counted separately in after_private_payload_reads. materialized_rows reports rows yielded by physical Parquet source scans, not JSON/CSV rows, opaque full-file hash reads, disk bytes or all row-group decoding. Input rows/bytes are complete normalized-source inventory (or public aggregate inventory), not actual filtered workload or physical IO bytes; model-load rows describe its associated dataset, not rows fed to an estimator. Page preparation measures saved-model discovery, processed-source selection and candidate preparation; full Streamlit rendering/context hashing is tested for correctness, not a measured whole-page speedup. Final CSV includes filtered materialized rows, repeats/ranges, hits/misses and exceptions.\n\n'
    text+='Cache keys bind object type, namespace, relevant content hashes, source/version/start/origin/coverage availability, t, windows, candidate policy and feature/algorithm version. Feature keys omit unrelated model settings; model load keys bind manifest/weight bytes, with dependency/object checks preserved. No probabilities are cached. Future byte edits may invalidate caches conservatively, but candidate/features/probabilities are verified invariant. Corrupt/incomplete payloads are not accepted; valid old pointers survive interrupted writes. Corrupted inactive pinned copies are re-established from the same verified live source hashes in a fresh version, without replacing any copy already in use. Snapshot objects bind all needed source/model/evidence files and report/protocol identity. Inputs are verified copied read-only archives, not size/mtime snapshots. Pending feature/ranking cache publication is delayed until outer source/copy verification; changes raise source_snapshot_changed and clear active UI state.\n\n'
    text+='Guarantee limits: read-only copies plus byte checks require stable trusted archive files, not adversarial same-owner mutation protection or an atomic live feed. Source/check/publication TOCTOU remains after final verification; no cross-file atomic acquisition, cross-process transaction, atomic multi-pointer commit or power-loss durability is claimed. Orphan content versions may persist after crashes; no automatic cleanup or retention policy. event_time comes from recorded events; ingestion_time_status=unavailable. Download time, mtime, snapshot establishment and Study Day are never ingestion evidence. T28 prospective clock/freshness guards remain mandatory. Reveal remains independent and coverage policies unchanged. Prediction schema3 invalidates old active sessions; frozen historical cases/probabilities are unchanged.\n\n'
    text+='Real parity: '+str(real['T30']['candidate_rows'])+' T30 candidates/4 dates/9 model-window combinations, all per-row probabilities and Known/Unknown/funnels/metrics checked against unchanged frozen samples; T31 '+str(real['T31']['score_files'])+' score files and complete rankings, all117 aggregates, topology/availability states match. Optimized full research reproduction writes ONLY a new data/processed/performance/research/<run_id> directory, never frozen T31 files. All protected report/data/model hashes unchanged; exact count/order checks and1e-12 float tolerance. Full evidence in T32_PARITY.json.\n\n'
    text+='Reproduction (matching lawful LOCAL sources/models required; no download/refit):\n\n```bash\n.venv/bin/python -m src.performance_benchmark --stage NEW_STAGE --repeats 5\n.venv/bin/python -m src.performance_benchmark --stage NEW_STAGE --cache-mode warm --repeats 5\n.venv/bin/python -m src.performance_audit\n.venv/bin/python -m pytest -q\n```\n\nExisting baseline/measurement stage files refuse overwrite; explicit new names preserve prior receipts. Only three reviewed performance aggregates and this report enter Git. Raw inputs, model copies, caches, pickle parity receipts, predictions and pair scores remain ignored. T33/T34 not started.\n'
    text+='\nMeasurement environment (no home paths):\n\n```json\n'+json.dumps(environment,indent=2)+'\n```\n'
    (root/'PERFORMANCE_AUDIT.md').write_text(text)
    return parity,rows


if __name__=='__main__':
    parity,rows=publish(Path(__file__).resolve().parents[1])
    print(json.dumps({'parity':parity,'comparison_rows':len(rows)},indent=2))
