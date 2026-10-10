"""Request/process-local verified model cache; no cached probability or time authorization."""

from collections import OrderedDict
import copy
from pathlib import Path

from src.model_registry import ModelRegistry
from src.model_registry import package_version
from src.snapshot_manager import file_hash, resolve_path, snapshot_context, model_paths

MODELS = OrderedDict()


def load_model(directory):
    with snapshot_context(model_paths(directory), {'object': 'verified_model_load'}):
        return _load_model(directory)


def _load_model(directory):
    directory = Path(directory)
    manifest = resolve_path(directory/'manifest.json')
    artifact = resolve_path(directory/'model.joblib')
    key = (file_hash(manifest), file_hash(artifact))
    from src.safe_cache import record_cache
    record_cache('model', key in MODELS)
    if key in MODELS:
        from src.snapshot_manager import read_json
        manifest_record = read_json(directory/'manifest.json')
        if any(package_version(name) != expected for name, expected in manifest_record['package_versions'].items()):
            raise ValueError('Model dependencies differ from the verified saved version.')
        cached = MODELS[key]
        if (cached.name != manifest_record['model_name'] or cached.feature_columns != manifest_record['feature_columns']
            or cached.threshold != manifest_record['threshold'] or cached.feature_window_days != manifest_record.get('feature_window_days')):
            raise ValueError('Cached model object differs from verified manifest.')
    if key not in MODELS:
        if manifest.parent != artifact.parent:
            raise ValueError('Model manifest/weights must belong to the same pinned version.')
        MODELS[key] = ModelRegistry.load(manifest.parent)
        while len(MODELS) > 16:
            MODELS.popitem(last=False)
    # Callers cannot mutate thresholds or weights used by another session.
    return copy.deepcopy(MODELS[key])
