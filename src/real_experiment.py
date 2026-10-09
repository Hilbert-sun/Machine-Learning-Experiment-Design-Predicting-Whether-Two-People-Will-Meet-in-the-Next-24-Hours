"""T17 genuine-data experiment; no UI, implicit download or test-driven tuning."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning

from src.calibration import reliability_points
from src.evaluate import binary_metrics, choose_threshold
from src.feature_engineering import FEATURE_NAMES, build_features
from src.label_builder import build_labels
from src.model_registry import ModelRegistry
from src.pipeline_cache import file_signatures, parquet_frames
from src.preprocessing import preprocess_contacts
from src.temporal_split import TrainingDataError, chronological_split, prepare_cohort, validation_partition
from src.train import save_training_run, train_models

DAY = 86400
PROTOCOL = {"seed": 42, "snapshot_hour": 8, "horizon_hours": 24, "min_scan_coverage": 0.5,
            "candidate_mode": "Known Pair; contacts strictly before t", "historical_windows_days": [1, 3, 7, 14],
            "maximum_feature_history_days": 14, "chronological_fractions": [0.6, 0.2, 0.2], "strict_label_window_purge": True,
            "negative_downsampling": False, "communications_enabled": False, "weekday_origin": None,
            "minimum_train_rows": 200, "minimum_class_rows_each_set": 20, "minimum_snapshot_times_each_set": 2,
            "baseline_parameters": {"logistic_regression": {"max_iter": 2000}},
            "xgboost_parameters": {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05},
            "calibration_rule": "sigmoid on early validation if both classes>=20 and later validation has>=2 snapshot times; otherwise no fitted calibrator",
            "threshold_rule": "validation F1 only; raw XGBoost threshold uses the same later-validation period as calibrated XGBoost",
            "test_policy": "one final frozen-model comparison after all fitting; no hyperparameter search"}


def split_counts(split):
    return {name: {"samples": len(part), "positive": int(part.label_24h.eq(1).sum()), "negative": int(part.label_24h.eq(0).sum()),
                   "snapshot_times": int(part.timestamp.nunique()), "first_timestamp": int(part.timestamp.min()), "last_timestamp": int(part.timestamp.max())}
            for name, part in (("train", split.train), ("validation", split.validation), ("test", split.test))}


def feasibility_reasons(split):
    reasons = []
    for name, counts in split_counts(split).items():
        if counts["snapshot_times"] < PROTOCOL["minimum_snapshot_times_each_set"]:
            reasons.append(f"{name}: fewer than2 prediction times")
        if min(counts["positive"], counts["negative"]) < PROTOCOL["minimum_class_rows_each_set"]:
            reasons.append(f"{name}: fewer than20 samples in one class")
    if len(split.train) < PROTOCOL["minimum_train_rows"]:
        reasons.append("train: fewer than200 reliable samples")
    return reasons


def snapshot_capacity(start, end, interval_hours):
    """Timeline-only counterfactual: ignores coverage, never creates real negatives."""
    anchor = 8 * 3600 if interval_hours == 24 else 0
    times = np.arange(anchor, end + 1, interval_hours * 3600)
    times = times[(times >= start) & (times + DAY <= end)]
    first, second = int(len(times) * 0.6), int(len(times) * 0.8)
    if first < 1 or second <= first or second >= len(times):
        return {"interval_hours": interval_hours, "complete_snapshots": len(times), "purged_time_groups": {"train": 0, "validation": 0, "test": 0}}
    return {"interval_hours": interval_hours, "complete_snapshots": len(times),
            "purged_time_groups": {"train": int((times[:first] + DAY < times[first]).sum()),
                                   "validation": int((times[first:second] + DAY < times[second]).sum()), "test": len(times) - second}}


def diagnose_dataset(root, dataset, source):
    processed = preprocess_contacts(source, dataset, root / "data/processed")
    labels = build_labels(processed, root / "data/processed/labels")
    frame = pd.read_parquet(labels.path)
    eligible = frame.loc[frame.eligible_for_evaluation.eq(True) & frame.label_24h.notna()].copy()
    pairs, contact_participants = set(), set()
    positive_rssi = 0
    for contacts in parquet_frames(processed.directory / "contacts.parquet", ["user_min", "user_max", "rssi"]):
        pairs.update(contacts[["user_min", "user_max"]].drop_duplicates().itertuples(index=False, name=None))
        contact_participants.update(contacts.user_min)
        contact_participants.update(contacts.user_max)
        positive_rssi += int(contacts.rssi.gt(0).sum())
    raw = processed.report
    start, end = raw["source_timestamp_min"] - raw["time_origin_seconds"], raw["source_timestamp_max"] - raw["time_origin_seconds"]
    with Path(source).open("rb") as handle:
        checksum = hashlib.file_digest(handle, "sha256").hexdigest()
    diagnosis = {"dataset": dataset, "source_path": str(Path(source).relative_to(root)), "bytes": Path(source).stat().st_size, "sha256": checksum,
                 "participants_with_records": raw["participants"], "participants_with_valid_contacts": len(contact_participants),
                 "raw_rows": raw["input_rows"], "valid_contact_records": raw["contact_rows"], "excluded_nonparticipant_rows": raw["invalid_id_rows"],
                 "self_rows": raw["self_contact_rows"], "duplicate_rows": raw["duplicate_contact_rows"], "empty_scan_rows": raw["empty_scan_rows"],
                 "external_device_rows": raw["external_device_rows"], "positive_rssi_records_retained_under_original_no_threshold_rule": positive_rssi,
                 "source_timestamp_range": [raw["source_timestamp_min"], raw["source_timestamp_max"]], "relative_timestamp_range": [start, end],
                 "source_time_basis": raw["source_time_basis"], "time_origin_seconds": raw["time_origin_seconds"], "span_seconds": end - start,
                 "span_days": (end - start) / DAY, "study_days_touched": end // DAY - start // DAY + 1,
                 "full_period_observed_pairs_descriptive_only": len(pairs),
                 "historical_candidate_pairs_across_prediction_rows": int(frame[["user_min", "user_max"]].drop_duplicates().shape[0]),
                 "complete_scheduled_snapshots": len(labels.report["snapshot_times"]), "snapshots_with_candidates": int(frame.timestamp.nunique()),
                 "candidate_sample_rows": len(frame), "positive_labels_including_ineligible": int(frame.label_24h.eq(1).sum()),
                 "negative_labels": int(frame.label_24h.eq(0).sum()), "unknown_labels": int(frame.label_24h.isna().sum()),
                 "coverage_eligible_samples": len(eligible), "positive_eligible": int(eligible.label_24h.eq(1).sum()), "negative_eligible": int(eligible.label_24h.eq(0).sum()),
                 "exclusion_reasons": frame.exclusion_reason.fillna("eligible").value_counts().to_dict(),
                 "candidate_counts_by_snapshot": [{"timestamp": int(t), "pairs": int(n)} for t, n in frame.groupby("timestamp").size().items()],
                 "scan_coverage_available": raw["scan_coverage_available"],
                 "timeline_counterfactuals_coverage_ignored_only": [snapshot_capacity(start, end, hours) for hours in (24, 6, 1)]}
    if raw["scan_coverage_available"]:
        positive = frame.label_24h.eq(1)
        diagnosis["coverage_sensitivity_counts_not_model_selection"] = [
            {"threshold": threshold, "samples": int(mask.sum()), "positive": int((mask & positive).sum()), "negative": int((mask & ~positive).sum())}
            for threshold in (0.25, 0.5, 0.75) for mask in [frame[["scan_coverage_a", "scan_coverage_b"]].min(axis=1).ge(threshold)]
        ]
    try:
        split = chronological_split(eligible)
        diagnosis["split"] = split_counts(split)
        diagnosis["purged_rows"] = split.report["purged_rows"]
    except TrainingDataError as exc:
        diagnosis["split"] = {name: {"samples": 0} for name in ("train", "validation", "test")}
        diagnosis["split_blocker"] = "No eligible rows." if eligible.empty else str(exc)
    return processed, labels, diagnosis


def _metrics(model, frame):
    y = frame.label_24h.to_numpy(dtype=int)
    probabilities = model.predict_proba(frame.loc[:, FEATURE_NAMES])[:, 1]
    result = binary_metrics(y, probabilities, threshold=model.threshold)
    groups = np.minimum((probabilities * 10).astype(int), 9)
    result["calibration_error_ece"] = float(sum(np.sum(groups == group) / len(y) * abs(probabilities[groups == group].mean() - y[groups == group].mean()) for group in np.unique(groups)))
    result["reliability"] = reliability_points(y, probabilities)
    return result


def run_real_experiment(root):
    root = Path(root).resolve()
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    diagnostics = []
    primary = None
    for dataset, relative in (("SocioPatterns", "data/raw/sociopatterns/HighSchool2013_proximity_net.csv.gz"), ("Copenhagen", "data/raw/copenhagen/bt_symmetric.csv")):
        source = root / relative
        if not source.is_file():
            diagnostics.append({"dataset": dataset, "source_path": relative, "status": "missing_local_file"})
            continue
        print(f"diagnosing {dataset}", flush=True)
        processed, labels, diagnosis = diagnose_dataset(root, dataset, source)
        diagnostics.append(diagnosis)
        if dataset == "Copenhagen":
            primary = (processed, labels, diagnosis)
    safe = {"task": "T17", "status": "diagnosed", "protocol": PROTOCOL, "datasets": diagnostics, "ui_changed": False}
    (reports / "T17_SAFE_METADATA.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2, allow_nan=False))
    if primary is None:
        safe.update(status="blocked", reason="Full genuine Copenhagen Bluetooth source is missing; no implicit download or unknown-negative relabeling.")
        return safe
    processed, labels, diagnosis = primary
    print("building/reusing strict historical features", flush=True)
    features = build_features(processed, labels, root / "data/features", progress=lambda t, rows: print(f"features day{t//DAY+1}: {rows:,}", flush=True))
    cohort = prepare_cohort(labels, features)
    split = chronological_split(cohort)
    reasons = feasibility_reasons(split)
    if reasons:
        safe.update(status="blocked", reason="; ".join(reasons))
        return safe
    calibration, tuning = validation_partition(split.validation)
    counts = calibration.label_24h.value_counts()
    calibrate = len(counts) == 2 and counts.min() >= 20 and tuning.timestamp.nunique() >= 2
    calibration_method = "sigmoid" if calibrate else None
    provenance = {"dataset": "Copenhagen", "source_kind": "real_public_dataset", "experiment": "T17",
                  "official_dataset_doi": "10.6084/m9.figshare.7267433", "raw_sha256": diagnosis["sha256"],
                  "processed_cache_version": processed.directory.name, "input_signatures": file_signatures([labels.path, features.path]),
                  "label_policy": labels.report["policy"], "feature_policy": features.report, "protocol": PROTOCOL}
    code_files = ["src/real_experiment.py", "src/feature_engineering.py", "src/label_builder.py", "src/preprocessing.py", "src/temporal_split.py", "src/model_registry.py", "src/train.py", "src/calibration.py"]
    safe.update(status="protocol_frozen_before_model_scores", split=split_counts(split), purged_rows=split.report["purged_rows"],
                calibration={"method": calibration_method, "fit_rows": len(calibration) if calibrate else 0,
                             "fit_prediction_times": int(calibration.timestamp.nunique()) if calibrate else 0,
                             "tuning_rows": len(tuning) if calibrate else len(split.validation),
                             "tuning_prediction_times": int(tuning.timestamp.nunique()) if calibrate else int(split.validation.timestamp.nunique()),
                             "reason": "predeclared validation-support gate; not selected using test improvement"},
                code_hashes={name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in code_files},
                software_base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(), python=platform.python_version())
    (reports / "T17_SAFE_METADATA.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2, allow_nan=False))
    started = time.monotonic()
    print("training genuine baselines; no final-test model scores read", flush=True)
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always", ConvergenceWarning)
        baselines = train_models(split, ["constant", "historical_frequency", "logistic_regression"], seed=42, feature_window_days=14,
                                 parameters=PROTOCOL["baseline_parameters"], progress=lambda done, total, name: print(f"baseline {done}/{total}: {name}", flush=True))
    if any(issubclass(warning.category, ConvergenceWarning) for warning in recorded):
        raise TrainingDataError("Logistic Regression did not converge under the prespecified optimizer budget; no test scores produced.")
    base_record, base_path = save_training_run(baselines, root / "models/T17", reports, provenance=provenance)
    print("baselines succeeded; training genuine XGBoost with fixed parameters", flush=True)
    main = train_models(split, ["xgboost"], seed=42, feature_window_days=14, parameters={"xgboost": PROTOCOL["xgboost_parameters"]},
                        calibration=calibration_method, progress=lambda done, total, name: print(f"main {done}/{total}: {name}", flush=True))
    calibrated = main.models["xgboost"]
    raw = getattr(calibrated, "base", calibrated)
    raw_threshold_data = tuning if calibrate else split.validation
    raw.threshold = choose_threshold(raw_threshold_data.label_24h, raw.predict_proba(raw_threshold_data.loc[:, FEATURE_NAMES])[:, 1])
    main_record, main_path = save_training_run(main, root / "models/T17", reports, provenance=provenance)
    raw_path = ModelRegistry.save(raw, root / "models/T17/raw_xgboost", metadata={"split": split.report, "provenance": provenance, "training": {"threshold_source": "later_validation" if calibrate else "validation"}, "test_evaluated": False})
    models = {**baselines.models, "xgboost_raw": raw}
    if calibrate:
        models["xgboost_sigmoid"] = calibrated
    print("all model choices frozen; now computing the one final-test comparison", flush=True)
    test_results = {name: _metrics(model, split.test) for name, model in models.items()}
    validation_results = {name: _metrics(model, split.validation if name in baselines.models else raw_threshold_data) for name, model in models.items()}
    paths = {**base_record["saved_models"], "xgboost_raw": str(raw_path)}
    if calibrate:
        paths["xgboost_sigmoid"] = main_record["saved_models"]["xgboost"]
    X_probe = split.test.loc[:, FEATURE_NAMES].head(20)
    for name, path in paths.items():
        np.testing.assert_allclose(ModelRegistry.load(path).predict_proba(X_probe), models[name].predict_proba(X_probe))
    safe.update(status="completed_real_experiment", metrics={"validation": validation_results, "test": test_results},
                model_artifacts={name: str(Path(path).relative_to(root)) for name, path in paths.items()},
                private_training_reports=[str(base_path.relative_to(root)), str(main_path.relative_to(root))],
                elapsed_training_and_evaluation_seconds=time.monotonic()-started, model_roundtrip="passed", test_used_for_selection=False,
                split_policy_changed=False, coverage_policy_changed=False, synthetic_samples_used=0)
    return safe


def write_results(root, result):
    reports = Path(root) / "reports"
    (reports / "T17_SAFE_METADATA.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    metrics = result.get("metrics", {})
    (reports / "T17_METRICS.json").write_text(json.dumps({"status": result["status"], "protocol": result["protocol"], "metrics": metrics}, ensure_ascii=False, indent=2, allow_nan=False))
    rows = [{"dataset": "Copenhagen", "source_kind": "real_public_dataset", "scope": scope, "model": name, **{key: value for key, value in values.items() if key != "reliability"}}
            for scope, models in metrics.items() for name, values in models.items()]
    pd.DataFrame(rows).to_csv(reports / "T17_METRICS.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    result = run_real_experiment(arguments.root)
    write_results(arguments.root, result)
    print(json.dumps({"status": result["status"], "test": result.get("metrics", {}).get("test", {})}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
