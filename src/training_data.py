"""Locate current label/feature artifacts without rebuilding earlier tasks."""

from dataclasses import dataclass
import json
from pathlib import Path

import pyarrow.parquet as pq

from src.loader import source_kind, supported_files
from src.pipeline_cache import PipelineArtifact, file_signatures
from src.preprocessing import cached_dataset


@dataclass
class TrainingInputs:
    processed: object
    labels: PipelineArtifact
    features: PipelineArtifact


def _matching(directory, prefix, required_inputs):
    artifacts = []
    for metadata in sorted(Path(directory).glob(f"{prefix}-*.json")):
        try:
            record = json.loads(metadata.read_text())
            inputs = record["identity"]["inputs"]
            path = metadata.with_suffix(".parquet")
            if inputs[:len(required_inputs)] != required_inputs or file_signatures([item["path"] for item in inputs]) != inputs:
                continue
            if pq.ParquetFile(path).metadata.num_rows != record["report"]["rows"]:
                continue
            artifacts.append(PipelineArtifact(path, record["report"], True))
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return artifacts


def available_training_inputs(root, config, dataset):
    root = Path(root)
    raw = root / config["paths"]["raw_copenhagen" if dataset == "Copenhagen" else "raw_sociopatterns"]
    output = root / config["paths"]["processed"]
    combinations = []
    for source in supported_files(raw, dataset):
        if source_kind(source, dataset) not in {"bluetooth", "proximity"}:
            continue
        processed = cached_dataset(source, dataset, output)
        if not processed:
            continue
        signatures = file_signatures([processed.directory / "contacts.parquet", processed.directory / "observations.parquet"])
        for labels in _matching(output / "labels", "labels", signatures):
            for features in _matching(root / config["paths"]["features"], "features", signatures + file_signatures([labels.path])):
                combinations.append(TrainingInputs(processed, labels, features))
    return combinations
