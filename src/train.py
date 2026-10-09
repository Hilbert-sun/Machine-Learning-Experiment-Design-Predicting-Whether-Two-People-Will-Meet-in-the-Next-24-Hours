"""Train on the train partition, select thresholds on validation, keep test untouched."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from uuid import uuid4

import numpy as np
from sklearn.model_selection import ParameterGrid

from src.evaluate import binary_metrics, choose_threshold
from src.calibration import calibrate_model, reliability_points
from src.feature_engineering import FEATURE_NAMES
from src.model_registry import ModelRegistry
from src.temporal_split import TrainingDataError, validation_partition


@dataclass
class TrainingRun:
    models: dict
    report: dict


def train_models(split, names, *, seed=42, parameters=None, parameter_grids=None, calibration=None, feature_window_days=None, progress=None):
    if len(np.unique(split.train.label_24h)) != 2:
        raise TrainingDataError("训练段必须包含正负两类可靠标签。")
    if not names or len(set(names)) != len(names):
        raise TrainingDataError("请选择至少一个不重复的模型。")
    X_train, y_train = split.train.loc[:, FEATURE_NAMES], split.train.label_24h
    if calibration not in {None, "sigmoid", "isotonic"}:
        raise TrainingDataError("不支持的校准方法。")
    calibration_frame, validation = validation_partition(split.validation) if calibration else (None, split.validation)
    X_validation, y_validation = validation.loc[:, FEATURE_NAMES], validation.label_24h
    models, summaries = {}, {}
    for index, name in enumerate(names):
        if progress:
            progress(index, len(names), name)
        start = time.monotonic()
        trials, best = [], None
        grid = list(ParameterGrid((parameter_grids or {}).get(name, {})))
        if len(grid) > 32:
            raise TrainingDataError("单模型最多32组参数，避免意外的大规模搜索。")
        for candidate in grid:
            options = {**(parameters or {}).get(name, {}), **candidate}
            try:
                raw_model = ModelRegistry.create(name, seed=seed, parameters=options, feature_window_days=feature_window_days)
                raw_model.fit(X_train, y_train)
                model = calibrate_model(raw_model, calibration_frame.loc[:, FEATURE_NAMES], calibration_frame.label_24h, method=calibration) if calibration else raw_model
                probabilities = model.predict_proba(X_validation)[:, 1]
            except Exception as exc:
                raise TrainingDataError(f"{name} 训练/校准失败（{type(exc).__name__}）：{exc}") from exc
            model.threshold = choose_threshold(y_validation, probabilities)
            metrics = binary_metrics(y_validation, probabilities, threshold=model.threshold)
            trials.append({"parameters": model.parameters, "validation": metrics})
            if best is None or metrics["log_loss"] < best[0]:
                best = (metrics["log_loss"], model, probabilities, metrics, raw_model)
        if best is None:
            raise TrainingDataError("参数网格为空。")
        _, model, probabilities, validation_metrics, raw_model = best
        summaries[name] = {
            "parameters": model.parameters, "feature_columns": model.feature_columns, "threshold": model.threshold,
            "train": binary_metrics(y_train, model.predict_proba(X_train)[:, 1], threshold=model.threshold),
            "validation": validation_metrics, "trials": trials,
            "duration_seconds": time.monotonic() - start,
        }
        models[name] = model
        if calibration:
            before = raw_model.predict_proba(X_validation)[:, 1]
            summaries[name]["calibration"] = {
                "method": calibration, "evaluation_scope": "later_validation_only",
                "before": binary_metrics(y_validation, before, threshold=choose_threshold(y_validation, before)),
                "after": validation_metrics,
                "reliability_before": reliability_points(y_validation, before),
                "reliability_after": reliability_points(y_validation, probabilities),
            }
    if progress:
        progress(len(names), len(names), "complete")
    return TrainingRun(models, {"seed": seed, "split": split.report, "models": summaries, "test_evaluated": False,
                                "threshold_selection": "validation F1; ties closest to0.5", "parameter_selection": "minimum validation log loss",
                                "calibration_method": calibration,
                                "feature_window_days": feature_window_days,
                                "validation_partition": {"calibration_rows": len(calibration_frame) if calibration else 0,
                                                         "tuning_rows": len(validation), "purged_rows": len(split.validation) - len(validation) - (len(calibration_frame) if calibration else 0)}})


def save_training_run(run, models_directory, reports_directory, *, provenance=None):
    """Save complete pipelines and a reproducible report; preserve previous runs on failure."""
    version = uuid4().hex[:12]
    directory = Path(models_directory) / version
    reports = Path(reports_directory)
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / f"training-{version}.json"
    temporary = None
    try:
        paths = {}
        for name, model in run.models.items():
            saved = ModelRegistry.save(model, directory, metadata={"training": run.report["models"][name], "split": run.report["split"], "provenance": provenance or {}, "test_evaluated": False})
            paths[name] = str(saved)
        record = {**run.report, "run_version": version, "saved_models": paths, "provenance": provenance or {}}
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=reports, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(record, handle, indent=2, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, report_path)
        return record, report_path
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
