"""Versioned, hash-verified JSON/Parquet bundles, published by a final atomic pointer."""

import copy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

import pandas as pd
import pyarrow.parquet as pq

from src.snapshot_manager import ACTIVE, cache_root, canonical, file_hash, resolve_path

CACHE_VERSION = 1
COUNTS = {'hits': 0, 'misses': 0, 'corrupt': 0}


def cache_stats():
    return dict(COUNTS)


def record_cache(kind, hit):
    key=kind+('_hits' if hit else '_misses')
    COUNTS[key]=COUNTS.get(key,0)+1


def _read_frame(path):
    COUNTS['payload_reads']=COUNTS.get('payload_reads',0)+1
    return pq.read_table(path).to_pandas()


class SafeCache:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else cache_root()/'objects'
        self.directory.mkdir(parents=True, exist_ok=True)

    def get(self, identity, producer, *, guard=lambda: None):
        identity = {'cache_schema': CACHE_VERSION, **identity}
        key = hashlib.sha256(canonical(identity).encode()).hexdigest()
        pointer = self.directory/f'{key}.json'
        active = ACTIVE.get()
        defer = active is not None and getattr(guard, '__self__', None) is active and getattr(guard, '__name__', '') == 'check_live'
        verify = (lambda: None) if defer else guard
        if defer and str(pointer) in active.pending_results:
            COUNTS['hits'] += 1
            return copy.deepcopy(active.pending_results[str(pointer)])
        try:
            record = json.loads(pointer.read_text())
            version = record['version']
            if Path(version).name != version or not version.startswith(key+'-'):
                raise ValueError('Invalid version pointer')
            bundle = self.directory/version
            manifest_path = bundle/'COMMITTED.json'
            if file_hash(manifest_path) != record['manifest_sha256']:
                raise ValueError('Manifest checksum mismatch')
            manifest = json.loads(manifest_path.read_text())
            if manifest['identity'] != identity:
                raise ValueError('Identity mismatch')
            for filename, expected in manifest['hashes'].items():
                if Path(filename).name != filename or file_hash(bundle/filename) != expected:
                    raise ValueError('Payload checksum mismatch')
            result = {name: _read_frame(bundle/filename) for name, filename in manifest['frames'].items()}
            verify()
            COUNTS['hits'] += 1
            return result
        except (OSError, ValueError, KeyError, TypeError):
            # Source changes are not a corrupt-cache retry condition.
            from src.snapshot_manager import SnapshotChanged
            import sys
            if isinstance(sys.exception(), SnapshotChanged):
                raise
            if pointer.exists():
                COUNTS['corrupt'] += 1
        COUNTS['misses'] += 1
        result = producer()
        verify()
        version = key+'-'+uuid4().hex
        with tempfile.TemporaryDirectory(dir=self.directory, prefix='.pending-') as temporary:
            staged = Path(temporary)
            frames = {}
            for i, (name, frame) in enumerate(result.items()):
                if not isinstance(name, str) or not isinstance(frame, pd.DataFrame):
                    raise ValueError('Cache payload must map names to DataFrames.')
                filename = f'{i}.parquet'
                frame.to_parquet(staged/filename, index=False)
                pd.testing.assert_frame_equal(frame, _read_frame(staged/filename))
                frames[name] = filename
            hashes = {filename: file_hash(staged/filename) for filename in frames.values()}
            manifest = {'identity': identity, 'frames': frames, 'hashes': hashes}
            (staged/'COMMITTED.json').write_text(canonical(manifest))
            verify()
            # Directory is immutable after publication; readers only discover it through pointer.
            os.rename(staged, self.directory/version)
        with tempfile.NamedTemporaryFile(mode='w', dir=self.directory, prefix='.pointer-', delete=False) as handle:
            temp_pointer = Path(handle.name)
            json.dump({'version': version, 'manifest_sha256': file_hash(self.directory/version/'COMMITTED.json')}, handle)
            handle.flush(); os.fsync(handle.fileno())
        if defer:
            active.pending.append((temp_pointer, pointer))
            active.pending_results[str(pointer)] = copy.deepcopy(result)
        else:
            try:
                guard()
                os.replace(temp_pointer, pointer)
            finally:
                temp_pointer.unlink(missing_ok=True)
        return result


def frame_identity(kind, processed, timestamp, window=None, coverage=None):
    snapshot = ACTIVE.get()
    if snapshot is None:
        raise ValueError('Private feature cache requires an active pinned snapshot.')
    relevant = {name: snapshot.hashes[str((processed.directory/name).resolve())] for name in ('contacts.parquet', 'observations.parquet') if (processed.directory/name).is_file()}
    return {'object': kind, 'dataset': processed.report['dataset'], 'source_hashes': relevant,
            'source_processing_version': 1, 'source_origin': processed.report['time_origin_seconds'],
            'source_start': processed.report['source_timestamp_min'], 'scan_coverage_available': processed.report.get('scan_coverage_available'),
            'timestamp': int(timestamp), 'history_window_days': window, 'coverage_policy': coverage,
            'candidate_policy': '[t-1d,t) contacts only', 'feature_version': 'bounded_window_v1/T32-reader1'}


@lru_cache(maxsize=32)
def _json_bytes(content):
    return json.loads(content)


def cached_json(path):
    """Bound by exact bytes, safe across same-mtime edits; callers get a private copy."""
    return copy.deepcopy(_json_bytes(resolve_path(path).read_bytes()))
