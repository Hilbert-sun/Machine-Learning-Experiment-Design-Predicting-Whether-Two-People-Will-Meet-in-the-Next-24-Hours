"""Small, bounded cache of aggregate reports only; never private predictions."""

import copy
from pathlib import Path

from src.snapshot_manager import file_hash

PUBLIC = {}


def load_public(root, loader):
    root = Path(root)
    directory = root/'reports/multisource'
    if not (directory/'T31_SOURCE_SUMMARY.json').exists():
        return None
    paths = [directory/name for name in ['T31_SOURCE_SUMMARY.json', 'T31_RETRIEVAL_METRICS.csv', 'T31_FEASIBILITY.json']]
    identity = tuple((str(p.resolve()), file_hash(p)) for p in paths)
    from src.safe_cache import record_cache
    record_cache('public', identity in PUBLIC)
    if identity not in PUBLIC:
        value = loader(root)
        if identity != tuple((str(p.resolve()), file_hash(p)) for p in paths):
            from src.snapshot_manager import SnapshotChanged
            raise SnapshotChanged('source_snapshot_changed: public report bundle changed while reading.')
        if len(PUBLIC) >= 16:
            PUBLIC.clear()
        PUBLIC[identity] = value
    result = copy.deepcopy(PUBLIC[identity])
    if identity != tuple((str(p.resolve()), file_hash(p)) for p in paths):
        from src.snapshot_manager import SnapshotChanged
        raise SnapshotChanged('source_snapshot_changed: public reports changed on cached read.')
    return result
