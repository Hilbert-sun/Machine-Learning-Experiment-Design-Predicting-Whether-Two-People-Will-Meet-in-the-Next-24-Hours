"""T32 real, isolated-process measurements. No fitting, downloads or old report writes."""

import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import pickle
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        json.loads(temporary.read_text())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def environment():
    def sysctl(name):
        try:
            return subprocess.check_output(['sysctl', '-n', name], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return 'unavailable'
    return dict(python=platform.python_version(), system=platform.platform(), machine=platform.machine(),
                cpu=sysctl('machdep.cpu.brand_string'), cpu_count=os.cpu_count(), physical_memory_bytes=sysctl('hw.memsize'),
                available_memory='vm_stat recorded separately; OS dynamic, not assumed from physical capacity',
                libraries={name: version(name) for name in ['pandas', 'numpy', 'pyarrow', 'networkx', 'scikit-learn', 'xgboost', 'streamlit']})


def prepare_inputs(root):
    import pandas as pd
    import pyarrow.parquet as pq
    import yaml
    from src.multisource_exploration import load_source
    from src.dataset_catalog import sources
    from src.preprocessing import cached_dataset
    from src.asof_ui import available_models
    from src.window_ui import source_path, location
    root = Path(root)
    config = yaml.safe_load((root/'configs/default.yaml').read_text())
    result = {'root': str(root), 'sources': {}, 't': 23*86400+28800}
    for spec in sources(root):
        if spec['dataset_id'] not in {'workplace2013', 'workplace2015', 'highschool2013', 'reality_mining_mendeley'}:
            continue
        base, source, _ = load_source(root, config, spec)
        if source is None:
            result['sources'][spec['dataset_id']] = {'unmeasured': base['reason']}
        else:
            result['sources'][spec['dataset_id']] = dict(path=str(source.path), dataset_id=source.dataset_id,
                                                       first=source.first, last=source.last, unit=source.unit,
                                                       file_hash=digest(source.path), raw_hash=base['file_hash'],
                                                       rows=pq.ParquetFile(source.path).metadata.num_rows)
    source = source_path(root, config, 'Copenhagen')
    processed = cached_dataset(source, 'Copenhagen', location(root, config, 'processed'))
    if processed is None:
        result['copenhagen'] = {'unmeasured': 'No matching real processed source'}
    else:
        files = {name: dict(path=str(processed.directory/name), sha256=digest(processed.directory/name),
                           rows=pq.ParquetFile(processed.directory/name).metadata.num_rows)
                 for name in ['contacts.parquet', 'observations.parquet']}
        rows = [r for r in available_models(root, config, 'Copenhagen') if r['run_id']=='102140b8cf3df83f' and r['model']=='xgboost']
        predictions = pd.read_parquet(root/'data/processed/asof_audit/7521ebdeb40f0b55/predictions.parquet')
        pair = predictions.loc[predictions.timestamp.eq(result['t']) & predictions.prediction_available].iloc[0]
        result['copenhagen'] = dict(directory=str(processed.directory), report=processed.report, files=files, raw=str(source),
                                    models={r['window']: r for r in rows}, pair=[int(pair.user_min), int(pair.user_max)])
    return result


def operations(inputs):
    names = ['network:'+name for name in inputs['sources']]
    names += ['retrieval:workplace2013', 'retrieval:workplace2015', 'candidates', 'features', 'predict_models', 'model_load', 'page_prepare', 'public_reports']
    return names


def worker(inputs, operation):
    import pandas as pd
    import src.pipeline_cache as pipeline
    # Count logical Parquet opens and yielded/materialized rows, not OS page-cache reads.
    reads, rows = Counter(), Counter()
    original_frames, original_read = pipeline.parquet_frames, pd.read_parquet
    def frames(path, columns, expression=None):
        try:
            from src.bounded_history import HISTORY
            state = HISTORY.get()
            virtual = state is not None and str(Path(path).resolve()) in state['tables'] and set(columns) <= set(state['tables'][str(Path(path).resolve())].column_names)
        except ImportError:
            virtual = False
        if not virtual:
            reads[str(path)] += 1
        for frame in original_frames(path, columns, expression):
            if not virtual:
                rows[str(path)] += len(frame)
            yield frame
    def read(path, *args, **kwargs):
        reads[str(path)] += 1
        frame = original_read(path, *args, **kwargs)
        rows[str(path)] += len(frame)
        return frame
    pipeline.parquet_frames, pd.read_parquet = frames, read
    from src.positive_retrieval import ContactSource, historical_scores, rank_scores, METHODS
    from src.multisource_exploration import network_summary
    from src.asof_inference import as_of_candidates, as_of_features
    from src.preprocessing import ProcessedDataset, cached_dataset
    from src.model_registry import ModelRegistry
    from src.asof_ui import available_models
    from src.time_machine import make_prediction
    from src.multisource_report import load_public_results
    import yaml
    root = Path(inputs['root'])
    config = yaml.safe_load((root/'configs/default.yaml').read_text())
    cop = inputs.get('copenhagen', {})
    processed = ProcessedDataset(Path(cop['directory']), cop['report'], True) if 'directory' in cop else None
    model_rows = {int(k): v for k, v in cop.get('models', {}).items()}
    def action():
        if operation.startswith(('network:', 'retrieval:')):
            kind, name = operation.split(':')
            spec = inputs['sources'][name]
            if 'unmeasured' in spec:
                return {'unmeasured': spec['unmeasured']}
            source = ContactSource(Path(spec['path']), name, spec['first'], spec['last'], spec['unit'])
            if kind=='network':
                return network_summary(source)
            t = (spec['first']//86400+8)*86400+28800
            try:
                from src.positive_retrieval import historical_scores_multi
                banks = historical_scores_multi(source, t, (1,3,7))
            except ImportError:
                banks = {w: historical_scores(source, t, w) for w in (1,3,7)}
            return {w: {m: rank_scores(bank, m) for m in METHODS} for w, bank in banks.items()}
        if operation=='public_reports':
            return load_public_results(root)
        if processed is None:
            return {'unmeasured': cop.get('unmeasured')}
        if operation=='candidates':
            return as_of_candidates(processed, inputs['t'], dataset_id='copenhagen')
        if operation=='features':
            return as_of_features(processed, inputs['t'], dataset_id='copenhagen')
        if operation=='predict_models':
            return make_prediction(processed, model_rows, inputs['t'], *cop['pair'])
        if operation=='model_load':
            try:
                from src.readonly_models import load_model
            except ImportError:
                load_model = ModelRegistry.load
            loaded = [load_model(r['directory']) for r in model_rows.values()]
            return [(m.name, m.threshold, m.feature_window_days) for m in loaded]
        if operation=='page_prepare':
            rows = available_models(root, config, 'Copenhagen')
            data = cached_dataset(cop['raw'], 'Copenhagen', root/config['paths']['processed'])
            keys = as_of_candidates(data, inputs['t'], dataset_id='copenhagen')
            return {'models': rows, 'keys': keys}
        raise ValueError(operation)
    # Optionally prime exactly the same request; this mode is distinct from cold application cache.
    if os.environ.get('T32_CACHE_MODE')=='warm':
        action(); reads.clear(); rows.clear()
        try:
            from src.safe_cache import COUNTS
            for key in COUNTS:
                COUNTS[key] = 0
        except ImportError:
            pass
    start = time.perf_counter()
    output = action()
    elapsed = time.perf_counter()-start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = peak/(1024**2) if sys.platform=='darwin' else peak/1024
    try:
        from src.safe_cache import cache_stats
        cache = cache_stats()
    except ImportError:
        cache = {'hits': 0, 'misses': 0, 'status': 'baseline_no_T32_cache'}
    return output, dict(seconds=elapsed, peak_rss_mb=peak_mb, parquet_reads=sum(reads.values()),
                        repeated_scans=sum(max(0,n-1) for n in reads.values()), materialized_rows=sum(rows.values()),
                        per_path_reads=dict(reads), cache=cache)


def run(root, stage, repeats=5, cache_mode='cold'):
    root = Path(root)
    directory = root/'data/processed/performance'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/f'T32_{stage.upper()}{"_WARM" if cache_mode=="warm" else ""}.json'
    if path.exists():
        raise ValueError('Immutable benchmark already exists; use a new explicit stage, never overwrite.')
    input_path = directory/'T32_INPUTS.json'
    if not input_path.exists():
        atomic_json(input_path, prepare_inputs(root)); input_path.chmod(0o444)
    inputs = json.loads(input_path.read_text())
    records = []
    for operation in operations(inputs):
        measurements = []
        for i in range(repeats):
            result_path = directory/f'{stage}-{cache_mode}-{operation.replace(":","-")}-{i}.json'
            payload_path = result_path.with_suffix('.pickle')
            env = dict(os.environ, T32_CACHE_MODE=cache_mode)
            with tempfile.TemporaryDirectory(dir=directory) as cache_dir:
                env['ENCOUNTER_CACHE_ROOT'] = cache_dir
                subprocess.run([sys.executable, '-m', 'src.performance_benchmark', '--worker', operation,
                                '--input', str(input_path), '--output', str(result_path)], cwd=os.environ.get('T32_CODE_ROOT', str(root)), env=env,
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            measurements.append(json.loads(result_path.read_text()))
        row = dict(operation=operation, repeat_count=repeats, cache_mode=cache_mode,
                   startup='fresh interpreter per repeat; library imports/setup excluded from wall-clock, included in RSS; OS cache uncontrolled',
                   samples=measurements, median_seconds=statistics.median(m['seconds'] for m in measurements),
                   seconds_range=[min(m['seconds'] for m in measurements),max(m['seconds'] for m in measurements)],
                   median_peak_rss_mb=statistics.median(m['peak_rss_mb'] for m in measurements))
        records.append(row)
        print(f'{stage} {cache_mode} {operation}: {row["median_seconds"]:.4f}s {row["median_peak_rss_mb"]:.1f}MiB', flush=True)
    result = dict(stage=stage, environment=environment(), inputs=inputs, operations=records,
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                  source_hashes={str(p.relative_to(Path(os.environ.get('T32_CODE_ROOT', str(root))))):digest(p) for p in (Path(os.environ.get('T32_CODE_ROOT', str(root)))/'src').glob('*.py')})
    atomic_json(path,result); path.chmod(0o444)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',default='baseline'); parser.add_argument('--repeats',type=int,default=5)
    parser.add_argument('--cache-mode',choices=['cold','warm'],default='cold')
    parser.add_argument('--worker');parser.add_argument('--input');parser.add_argument('--output');parser.add_argument('--root',type=Path)
    args=parser.parse_args()
    if args.worker:
        output,measurement=worker(json.loads(Path(args.input).read_text()),args.worker)
        with Path(args.output).with_suffix('.pickle').open('wb') as handle:
            pickle.dump(output,handle)  # Self-produced private parity receipt only; never public/cache input.
        atomic_json(args.output,measurement)
    else:
        run(args.root or Path(__file__).resolve().parents[1],args.stage,args.repeats,args.cache_mode)
