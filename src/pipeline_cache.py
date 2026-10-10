"""Shared small artifact cache for labels/features; raw data remain in T05 caches."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile

import pyarrow.dataset as ds
import pyarrow.parquet as pq


@dataclass
class PipelineArtifact:
    path: Path
    report: dict
    cached: bool


def file_signatures(paths) -> list[dict]:
    return [{"path": str(Path(path).resolve()), "size": Path(path).stat().st_size,
             "mtime_ns": Path(path).stat().st_mtime_ns} for path in paths]


def parquet_frames(path, columns, expression=None):
    from src.bounded_history import cached_batches
    from src.snapshot_manager import resolve_path
    batches = cached_batches(path, columns, expression)
    if batches is None:
        batches = ds.dataset(resolve_path(path), format="parquet").to_batches(columns=columns, filter=expression, batch_size=65536,
                                                                            batch_readahead=1, fragment_readahead=1, use_threads=False)
    for batch in batches:
        yield batch.to_pandas()


def cache_artifact(output, prefix, identity, schema, produce) -> PipelineArtifact:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    path = output / f"{prefix}-{key}.parquet"
    metadata = path.with_suffix(".json")
    if path.is_file() and metadata.is_file():
        try:
            record = json.loads(metadata.read_text())
            if record["identity"] == identity and pq.ParquetFile(path).metadata.num_rows == record["report"]["rows"]:
                return PipelineArtifact(path, record["report"], True)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    with tempfile.TemporaryDirectory(prefix=f".{prefix}-", dir=output) as temporary:
        staged = Path(temporary) / "artifact.parquet"
        with pq.ParquetWriter(staged, schema) as writer:
            report = produce(writer)
        if pq.ParquetFile(staged).metadata.num_rows != report["rows"]:
            raise RuntimeError("产物行数与报告不一致，未发布缓存。")
        manifest = Path(temporary) / "artifact.json"
        manifest.write_text(json.dumps({"identity": identity, "report": report}, ensure_ascii=False, indent=2))
        os.replace(staged, path)
        os.replace(manifest, metadata)
    return PipelineArtifact(path, report, False)
