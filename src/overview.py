"""Measured Overview summaries from current processed artifacts, not UI placeholders."""

import json
from pathlib import Path

from src.model_registry import ModelRegistry
from src.pipeline_cache import parquet_frames
from src.training_data import available_training_inputs
from src.visualization import exploration_options, summarize_exploration


def overview_summary(root, config, dataset, processed):
    options = exploration_options(processed.directory, processed.report)
    exploration = summarize_exploration(processed.directory, processed.report, (options["first_day"], options["last_day"]))
    policy = config.get("prediction", {})
    label_sources = {}
    # Minimal page-test configurations may omit features; no label rate is then claimed.
    if "features" in config.get("paths", {}):
        for inputs in available_training_inputs(root, config, dataset):
            label_policy = inputs.labels.report["policy"]
            if inputs.processed.directory == processed.directory and label_policy["snapshot_hour"] == policy.get("snapshot_hour", 8) and label_policy["min_scan_coverage"] == policy.get("min_scan_coverage", 0.5):
                label_sources[str(inputs.labels.path)] = inputs.labels
    eligible = positives = 0
    if len(label_sources) == 1:
        labels = next(iter(label_sources.values()))
        for frame in parquet_frames(labels.path, ["label_24h", "eligible_for_evaluation"]):
            known = frame.eligible_for_evaluation.eq(True) & frame.label_24h.notna()
            eligible += int(known.sum())
            positives += int(frame.loc[known, "label_24h"].eq(1).sum())
    models = []
    for model in ModelRegistry.list_saved(Path(root) / config.get("paths", {}).get("models", "models")):
        manifest = json.loads((Path(model["path"]) / "manifest.json").read_text())
        if manifest["metadata"].get("provenance", {}).get("dataset") == dataset:
            models.append(model)
    return {"participants": processed.report["participants"], "contact_records": exploration.rows,
            "valid_pairs": len(exploration.pairs), "observation_days": options["last_day"] - options["first_day"] + 1,
            "positive_rate": positives / eligible if eligible else None, "eligible_samples": eligible,
            "label_policy_available": len(label_sources) == 1, "saved_models": len(models), "exploration": exploration}
