"""T21/T22 fixed-protocol genuine-data study; no download/UI or test-driven selection."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning

from src.baseline_audit import immutable_json, sha256, verify_frozen
from src.calibration import reliability_points
from src.evaluate import binary_metrics, choose_threshold
from src.model_registry import ModelRegistry
from src.window_cohort import KEYS, DAY, row_hash
from src.window_features import WINDOW_FEATURES
from src.window_models import create_window_model

PROTOCOL = {"version": 1, "windows_planned": [1, 3, 7], "primary_contrast": [1, 7], "seed": 42,
            "models": ["historical_frequency", "logistic_regression", "xgboost"],
            "parameters": {"historical_frequency": {}, "logistic_regression": {"max_iter": 2000},
                           "xgboost": {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05}},
            "candidate_policy": "shared [t-1d,t) contacts", "minimum_history_span_days": 7,
            "future_horizon_hours": 24, "coverage_threshold": 0.5, "chronological_fractions": [0.6, 0.2, 0.2],
            "purge": "t+24h < next_start", "negative_sampling": False, "hyperparameter_search": False,
            "threshold": "maximum validation F1; ties closest to0.5", "calibration": None,
            "calibration_reason": "Only3 validation dates; independent calibration plus>=2 threshold dates is unsupported after strict24h purge.",
            "walk_forward": {"test_start_study_days": [16, 19, 22], "test_days": 2, "validation_days": 3,
                             "minimum_train_days": 3, "minimum_class_rows": 20, "calibration": None,
                             "purpose": "pre-primary-holdout descriptive robustness only; no selection or refitting primary models"},
            "uncertainty": {"block": "one prediction day; all models/windows resample the same days",
                            "minimum_days_for_bootstrap_ci": 8, "bootstrap_repetitions": 1000,
                            "few_days_policy": "paired per-day and leave-one-day-out descriptive ranges; no confidence/significance claim"},
            "prior_exposure": "T17 test dates overlap this study; fixed-protocol same-source temporal comparison, not pristine independent validation.",
            "communications": False, "weekday_origin": None, "test_used_for_selection": False}


def read_inputs(root):
    root = Path(root)
    verify_frozen(root, root/"reports/window_study/T18_BASELINE_MANIFEST.json")
    cohort_manifest = json.loads((root/"data/processed/window_study/T19_COHORT_MANIFEST.json").read_text())
    if cohort_manifest["support"]["status"] != "ready":
        raise ValueError("insufficient_days: cohort does not support chronological evaluation.")
    folder = root/"data/processed/window_study"
    for key in ("cohort", "split"):
        if sha256(folder/cohort_manifest[f"{key}_filename"]) != cohort_manifest[f"{key}_sha256"]:
            raise ValueError("Frozen cohort/split changed.")
    cohort = pd.read_parquet(folder/cohort_manifest["split_filename"])
    if row_hash(cohort, labels=True) != cohort_manifest["label_hash"]:
        raise ValueError("Frozen labels changed.")
    receipt = json.loads((root/"data/features/window_study/T20_FEATURES.json").read_text())
    banks = {}
    for days, record in receipt.items():
        if sha256(root/record["path"]) != record["sha256"]:
            raise ValueError("Frozen feature bank changed.")
        frame = pd.read_parquet(root/record["path"])
        if row_hash(frame) != cohort_manifest["sample_key_hash"] or set(frame.columns) != set(KEYS)|set(WINDOW_FEATURES):
            raise ValueError("Window feature keys/columns differ from common cohort.")
        banks[int(days)] = frame
    return cohort, banks, cohort_manifest, receipt


def model_input(bank, frame, days):
    joined = frame[KEYS].merge(bank, on=KEYS, how="left", validate="one_to_one", indicator=True)
    if not joined._merge.eq("both").all():
        raise ValueError("Model rows missing feature keys.")
    X = joined.loc[:, WINDOW_FEATURES].copy()
    X.attrs["history_window_days"] = days
    return X


def fit_window(bank, train, validation, days, protocol=PROTOCOL):
    models, summaries = {}, {}
    X = model_input(bank, train, days)
    V = model_input(bank, validation, days)
    if len(np.unique(train.label_24h)) != 2 or len(np.unique(validation.label_24h)) != 2:
        raise ValueError("Both training/validation classes required.")
    for name in protocol["models"]:
        started = time.monotonic()
        model = create_window_model(name, days=days, seed=protocol["seed"], parameters=protocol["parameters"][name])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(X, train.label_24h)
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            raise ValueError("Logistic convergence failed under frozen budget; no test scores produced.")
        probabilities = model.predict_proba(V)[:, 1]
        model.threshold = choose_threshold(validation.label_24h, probabilities)
        summaries[name] = {"parameters": model.parameters, "threshold": model.threshold,
                           "training_rows": len(train), "training_prediction_times": sorted(int(t) for t in train.timestamp.unique()),
                           "validation_prediction_times": sorted(int(t) for t in validation.timestamp.unique()),
                           "feature_columns": model.feature_columns, "validation": binary_metrics(validation.label_24h, probabilities, threshold=model.threshold),
                           "fit_and_validation_seconds": time.monotonic()-started}
        models[name] = model
    return models, summaries


def freeze_protocol(root, cohort_manifest, receipt):
    root = Path(root)
    sources = ["src/window_study.py", "src/window_cohort.py", "src/window_features.py", "src/window_models.py",
               "src/model_registry.py", "src/evaluate.py", "src/temporal_split.py", "src/baselines.py"]
    record = {"protocol": PROTOCOL, "cohort_manifest_sha256": sha256(root/"data/processed/window_study/T19_COHORT_MANIFEST.json"),
              "sample_key_hash": cohort_manifest["sample_key_hash"], "label_hash": cohort_manifest["label_hash"],
              "splits": cohort_manifest["support"], "feature_hashes": {d: r["sha256"] for d,r in receipt.items()},
              "code_hashes": {name: sha256(root/name) for name in sources},
              "package_versions": {name: version(name) for name in ("numpy", "pandas", "scikit-learn", "xgboost", "pyarrow")}}
    run_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    record["run_id"] = run_id
    directory = root/"reports/window_study"/run_id
    immutable_json(directory/"PROTOCOL_FROZEN.json", record)
    return run_id, directory, record


def run_primary(root):
    root = Path(root)
    cohort, banks, manifest, receipt = read_inputs(root)
    run_id, directory, frozen = freeze_protocol(root, manifest, receipt)
    if (directory/"T21_RESULTS.json").exists():
        return json.loads((directory/"T21_RESULTS.json").read_text()), directory
    train = cohort.loc[cohort.split.eq("train")].copy()
    validation = cohort.loc[cohort.split.eq("validation")].copy()
    test = cohort.loc[cohort.split.eq("test")].copy()
    models, summaries, paths = {}, {}, {}
    for days in (1, 7):
        print(f"Fit frozen {days}d models; test scores not read", flush=True)
        models[days], summaries[days] = fit_window(banks[days], train, validation, days)
        paths[days] = {}
        for name, model in models[days].items():
            path = ModelRegistry.save(model, root/"models/.window_study"/run_id/f"{days}d", metadata={"run_id": run_id, "feature_contract": "bounded_window_v1", "protocol_sha256": sha256(directory/"PROTOCOL_FROZEN.json"), "test_used_for_selection": False})
            paths[days][name] = str(path.relative_to(root))
    immutable_json(directory/"T21_MODELS_FROZEN.json", {"models": summaries, "model_artifacts": paths, "test_scores_read": False})
    print("All1d/7d models/thresholds frozen; evaluate final test once", flush=True)
    results = evaluate_windows(root, directory, run_id, test, banks, models, summaries, paths, "T21", source_kind="real_public_dataset")
    return results, directory


def evaluate_windows(root, directory, run_id, test, banks, models, summaries, paths, stage, *, source_kind):
    root, directory = Path(root), Path(directory)
    rows, curves, prediction_files = [], {}, {}
    for days, window_models in models.items():
        X = model_input(banks[days], test, days)
        exported = test.copy().reset_index(drop=True)
        for name, model in window_models.items():
            p = model.predict_proba(X)[:, 1]
            metrics = binary_metrics(test.label_24h, p, threshold=model.threshold)
            rows.append({"window_days": days, "model": name, **metrics, "ap_over_prevalence": metrics["pr_auc_average_precision"]/metrics["positive_rate"],
                         "distinct_prediction_days": int(test.timestamp.nunique())})
            curves[f"{days}d/{name}"] = reliability_points(test.label_24h, p)
            exported[f"p_{name}"] = p
            exported[f"threshold_{name}"] = model.threshold
            if paths:
                loaded = ModelRegistry.load(root/paths[days][name])
                np.testing.assert_allclose(loaded.predict_proba(X.head(20)), model.predict_proba(X.head(20)))
        filename = f"{stage}_predictions_{days}d.parquet"
        path = directory/filename
        if path.exists():
            pd.testing.assert_frame_equal(pd.read_parquet(path), exported)
        else:
            exported.to_parquet(path, index=False)
        prediction_files[str(days)] = {"filename": filename, "sha256": sha256(path), "key_hash": row_hash(exported), "label_hash": row_hash(exported, labels=True)}
    result = {"run_id": run_id, "stage": stage, "source_kind": source_kind, "dataset_id": "copenhagen",
              "protocol": PROTOCOL, "test_used_for_selection": False, "calibration_method": None, "test_metrics": rows,
              "reliability": curves, "validation_and_runtime": summaries, "model_artifacts": paths,
              "predictions_local_ignored": prediction_files, "model_roundtrip": "passed"}
    if stage == "T21":
        result["paired_main_contrast"] = [{"model": name, "AP_1d": next(r["pr_auc_average_precision"] for r in rows if r["model"]==name and r["window_days"]==1),
                                           "AP_7d": next(r["pr_auc_average_precision"] for r in rows if r["model"]==name and r["window_days"]==7)} for name in PROTOCOL["models"]]
        for row in result["paired_main_contrast"]:
            row["delta_AP_7d_minus_1d"] = row["AP_7d"]-row["AP_1d"]
    immutable_json(directory/f"{stage}_RESULTS.json", result)
    pd.DataFrame(rows).to_csv(directory/f"{stage}_METRICS.csv", index=False)
    return result


def verify_exported_metrics(directory, stage="T21"):
    directory = Path(directory)
    result = json.loads((directory/f"{stage}_RESULTS.json").read_text())
    for window, item in result["predictions_local_ignored"].items():
        path = directory/item["filename"]
        if sha256(path) != item["sha256"]:
            raise ValueError("Prediction export checksum changed.")
        frame = pd.read_parquet(path)
        assert row_hash(frame, labels=True) == item["label_hash"]
        for name in PROTOCOL["models"]:
            actual = binary_metrics(frame.label_24h, frame[f"p_{name}"], threshold=float(frame[f"threshold_{name}"].iloc[0]))
            recorded = next(r for r in result["test_metrics"] if r["window_days"]==int(window) and r["model"]==name)
            for key, value in actual.items():
                if value is None:
                    assert recorded[key] is None
                else:
                    np.testing.assert_allclose(recorded[key], value, rtol=1e-12, atol=1e-12)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result, directory = run_primary(args.root)
    verify_exported_metrics(directory)
    from src.window_report import write_primary_report
    write_primary_report(result, directory, args.root/"reports/window_study")
    print(json.dumps({"run_id": result["run_id"], "metrics": result["test_metrics"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
