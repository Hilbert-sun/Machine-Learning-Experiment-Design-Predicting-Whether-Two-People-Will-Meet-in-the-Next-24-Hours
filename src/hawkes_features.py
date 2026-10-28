"""T37 XGBoost with the four T36 Hawkes scores as extra inputs, on the frozen T35 rolling folds.

Inputs are the 7d bounded features plus every Hawkes grid score (no half-life selection). Parameters,
seed, threshold rule and fold plan are unchanged; no test score is used for any choice.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_audit import immutable_json, sha256
from src.evaluate import choose_threshold
from src.hawkes_baseline import HAWKES_PROTOCOL, hawkes_scores, select_per_fold
from src.model_registry import ModelRegistry
from src.preprocessing import preprocess_contacts
from src.rolling_validation import ROLLING_PROTOCOL, summarize
from src.window_cohort import KEYS, row_hash
from src.window_features import WINDOW_FEATURES
from src.window_study import PROTOCOL, read_inputs

HAWKES_COLUMNS = [f"hawkes_{hours}h" for hours in HAWKES_PROTOCOL["half_life_hours_grid"]]
FEATURE_PROTOCOL = {
    "version": 1, "task": "T37", "fold_plan": "frozen T35 run", "window_days": 7,
    "inputs": "7d bounded_window_v1 features + all Hawkes grid scores " + ", ".join(HAWKES_COLUMNS),
    "model": "xgboost", "parameters": PROTOCOL["parameters"]["xgboost"], "seed": PROTOCOL["seed"],
    "preprocessing": "drop columns all-null in train; registry median imputer with indicators",
    "threshold": "maximum validation F1", "calibration": None, "hyperparameter_search": False,
    "hawkes_reuse": "T36 scores reused after checksum; missing train times scored with the same function",
    "compared_models": ["xgboost_hawkes", "xgboost", "hawkes", "logistic_regression"],
    "contrasts": [["xgboost_hawkes", 7, "xgboost", 7], ["xgboost_hawkes", 7, "hawkes", 7]],
    "test_used_for_selection": False,
}


def fit_predict(train, validation, test, columns, protocol=FEATURE_PROTOCOL):
    columns = [name for name in columns if train[name].notna().any()]
    model = ModelRegistry.create("xgboost", seed=protocol["seed"], parameters=protocol["parameters"]).estimator
    model.fit(train.loc[:, columns], train.label_24h)
    threshold = choose_threshold(validation.label_24h, model.predict_proba(validation.loc[:, columns])[:, 1])
    return model.predict_proba(test.loc[:, columns])[:, 1], threshold, columns


def fold_predictions(frame, folds, columns, progress=print):
    parts = []
    for fold in folds:
        if fold["status"] != "evaluated":
            continue
        sets = [frame.loc[frame.timestamp.isin(times)] for times in (fold["train_times"], fold["validation_times"], [fold["test_time"]])]
        p, threshold, _ = fit_predict(*sets, columns)
        test = sets[2].loc[:, KEYS].copy()
        test["p_7d_xgboost_hawkes"] = p
        test["threshold_7d_xgboost_hawkes"] = threshold
        parts.append(test)
        if progress:
            progress(f"fold study_day={fold['study_day']} evaluated")
    return pd.concat(parts, ignore_index=True)


def comparison_protocol():
    return {**ROLLING_PROTOCOL, "windows": [7], "base_protocol": {**ROLLING_PROTOCOL["base_protocol"], "models": FEATURE_PROTOCOL["compared_models"]},
            "contrasts": FEATURE_PROTOCOL["contrasts"]}


def run(root, public_dir, verify_only=False):
    root = Path(root)
    cohort, banks, _, _ = read_inputs(root)
    t35 = json.loads((root/"studies/rolling_validation/T35_RESULTS.json").read_text())
    t36 = json.loads((root/"studies/hawkes_baseline/T36_RESULTS.json").read_text())
    rolling, hawkes_dir = root/"data/processed/rolling"/t35["run_id"], root/"data/processed/hawkes"/t36["run_id"]
    receipt = json.loads((rolling/"RUN_RECEIPT.json").read_text())
    if sha256(rolling/"predictions.parquet") != receipt["predictions_sha256"]:
        raise ValueError("Frozen T35 predictions changed.")
    if sha256(hawkes_dir/"hawkes_scores.parquet") != json.loads((hawkes_dir/"RUN_RECEIPT.json").read_text())["scores_sha256"]:
        raise ValueError("Frozen T36 Hawkes scores changed.")
    folds = receipt["folds"]
    cohort = cohort.drop(columns="split")
    needed = sorted({t for f in folds if f["status"] == "evaluated" for t in f["train_times"] + f["validation_times"] + [f["test_time"]]})
    rows = cohort.loc[cohort.timestamp.isin(needed)].reset_index(drop=True)
    record = {"protocol": FEATURE_PROTOCOL, "t35_run_id": t35["run_id"], "t36_run_id": t36["run_id"], "rows_sha256": row_hash(rows, labels=True),
              "code_hashes": {name: sha256(root/name) for name in ("src/hawkes_features.py", "src/hawkes_baseline.py", "src/rolling_validation.py", "src/model_registry.py")}}
    run_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    directory = root/"data/processed/hawkes_features"/run_id
    immutable_json(directory/"PROTOCOL_FROZEN.json", {**record, "run_id": run_id})
    path = directory/"predictions.parquet"
    if verify_only:
        if sha256(path) != json.loads((directory/"RUN_RECEIPT.json").read_text())["predictions_sha256"]:
            raise ValueError("Local T37 predictions changed.")
        predictions = pd.read_parquet(path)
    else:
        reused = pd.read_parquet(hawkes_dir/"hawkes_scores.parquet")
        missing = rows.merge(reused[KEYS], on=KEYS, how="left", indicator=True).query("_merge == 'left_only'")[KEYS]
        processed = preprocess_contacts(root/"data/raw/copenhagen/bt_symmetric.csv", "Copenhagen", root/"data/processed")
        check_time = int(reused.timestamp.min())
        check = hawkes_scores(processed.directory/"contacts.parquet", reused.loc[reused.timestamp.eq(check_time)], progress=None)
        pd.testing.assert_frame_equal(check.reset_index(drop=True), reused.loc[reused.timestamp.eq(check_time)].reset_index(drop=True))
        scores = pd.concat([reused, hawkes_scores(processed.directory/"contacts.parquet", missing)], ignore_index=True)
        frame = rows.merge(banks[7], on=KEYS, validate="one_to_one")
        frame = frame.merge(scores, on=KEYS, how="left", validate="one_to_one")
        if frame[HAWKES_COLUMNS].isna().any().any():
            raise ValueError("Hawkes scores missing for fold rows.")
        columns = list(WINDOW_FEATURES) + HAWKES_COLUMNS
        predictions = fold_predictions(frame, folds, columns)
        if path.exists():
            pd.testing.assert_frame_equal(pd.read_parquet(path), predictions)
        else:
            predictions.to_parquet(path, index=False)
        immutable_json(directory/"RUN_RECEIPT.json", {"predictions_sha256": sha256(path), "recomputed_hawkes_rows": len(missing),
                                                      "reuse_check_time": check_time})
    t35_predictions = pd.read_parquet(rolling/"predictions.parquet")
    hawkes, _ = select_per_fold(pd.read_parquet(hawkes_dir/"hawkes_scores.parquet"), cohort, folds)
    combined = t35_predictions.merge(hawkes, on=KEYS, validate="one_to_one").merge(predictions, on=KEYS, validate="one_to_one")
    summary = summarize(combined, comparison_protocol())
    reference = {m["model"]: m["pr_auc_average_precision"] for m in t36["metrics"]}
    for metric in summary["metrics"]:
        if metric["model"] in reference and not np.isclose(metric["pr_auc_average_precision"], reference[metric["model"]], rtol=0, atol=1e-12):
            raise ValueError("Reference model metrics differ from T36.")
    result = {"task": "T37", "run_id": run_id, "dataset_id": "copenhagen", "source_kind": "real_public_dataset", "protocol": FEATURE_PROTOCOL,
              "t35_run_id": t35["run_id"], "t36_run_id": t36["run_id"], "code_hashes": record["code_hashes"], **summary,
              "interpretation": "Same frozen T35 folds and previously exposed test dates; no tuning. Day-block intervals describe day-to-day variation only."}
    target = Path(public_dir)/"T37_RESULTS.json"
    if verify_only:
        if json.loads(target.read_text()) != json.loads(json.dumps(result, allow_nan=False)):
            raise ValueError("Public T37 aggregates differ from recomputation.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--public-dir", type=Path, default=Path("studies/hawkes_features"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.root/args.public_dir, args.verify_only)
    print(json.dumps({"run_id": result["run_id"], "contrasts": [{k: c[k] for k in ("contrast", "pooled_delta_ap", "confidence_interval_95", "days_positive")} for c in result["contrasts"]]}, indent=1))


if __name__ == "__main__":
    main()
