"""One bounded raw scan, independent slices, reuse frozen T20 calculations unchanged."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds

from src.snapshot_manager import resolve_path

HISTORY = ContextVar('bounded_reader', default=None)
BANKS = ContextVar('prepared_feature_banks', default=None)


@contextmanager
def bounded_reader(processed, timestamp, days):
    existing = HISTORY.get()
    if existing is not None and existing['directory'] == processed.directory.resolve() and existing['t'] == timestamp and existing['days'] >= days:
        yield
        return
    condition = (ds.field('timestamp') >= timestamp-days*86400) & (ds.field('timestamp') < timestamp)
    tables = {}
    for name, columns in [('contacts.parquet', ['timestamp', 'user_min', 'user_max', 'rssi']),
                          ('observations.parquet', ['timestamp', 'user_id', 'scan_observed'])]:
        if name == 'observations.parquet' and not processed.report.get('scan_coverage_available'):
            continue
        path = processed.directory/name
        # Reuse instrumentable Arrow chunk IO; one physical bounded scan for each file.
        from src.pipeline_cache import parquet_frames
        token = HISTORY.set(None)
        try:
            batches = [pa.Table.from_pandas(frame, preserve_index=False) for frame in parquet_frames(path, columns, condition)]
        finally:
            HISTORY.reset(token)
        if batches:
            tables[str(path.resolve())] = pa.concat_tables(batches)
    token = HISTORY.set({'directory': processed.directory.resolve(), 't': timestamp, 'days': days, 'tables': tables})
    try:
        yield
    finally:
        HISTORY.reset(token)


def cached_batches(path, columns, expression):
    state = HISTORY.get()
    if state is None or str(Path(path).resolve()) not in state['tables']:
        return None
    table = state['tables'][str(Path(path).resolve())]
    if not set(columns) <= set(table.column_names):
        return None
    return ds.dataset(table).to_batches(columns=columns, filter=expression, batch_size=65536)
