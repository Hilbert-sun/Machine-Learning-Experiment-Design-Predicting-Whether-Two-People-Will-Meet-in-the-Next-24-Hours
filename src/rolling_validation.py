"""T35 rolling-origin re-evaluation of the unchanged T21/T22 protocol plus per-participant ranking.

The fold plan and protocol are frozen before any model is fitted. No parameter, threshold rule,
window or fold is chosen from test scores; all test dates were exposed earlier (T17/T21/T22).
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_audit import immutable_json, sha256
from src.evaluate import binary_metrics
from src.window_cohort import DAY, KEYS, part_summary, row_hash
from src.window_study import PROTOCOL, fit_window, model_input, read_inputs

ROLLING_PROTOCOL = {
    "version": 1, "task": "T35",
    "base_protocol": {key: PROTOCOL[key] for key in ("models", "parameters", "seed", "threshold", "calibration",
                                                      "candidate_policy", "coverage_threshold", "future_horizon_hours")},
    "windows": [1, 3, 7], "test_unit": "one prediction time per fold",
    "validation_times": 3, "minimum_train_times": 4, "minimum_class_rows": 20,
    "purge": "every train/validation t+24h strictly before the next set's first t",
    "fold_selection": "every cohort time satisfying the rules; fixed before fitting",
    "fit_failure": "drop that fold for every model and window",
    "uncertainty": {"block": "one test prediction time", "minimum_days_for_bootstrap_ci": 8,
                    "bootstrap_repetitions": 1000, "seed": 42, "statistic": "pooled AP difference"},
    "contrasts": [["xgboost", 7, "xgboost", 1], ["xgboost", 7, "xgboost", 3],
                  ["xgboost", 7, "historical_frequency", 7], ["xgboost", 7, "logistic_regression", 7]],
    "ranking": {"k": [5, 10], "unit": "(prediction time, participant) with >=1 positive reliably labeled candidate",
                "order": "probability descending, partner id ascending", "precision": "hits/K"},
    "exposure": "All candidate test dates were scored earlier as T17 test, T22 walk-forward or T21/T22 primary test; "
                "this is a fixed-protocol re-evaluation with more test days, not a pristine holdout.",
    "test_used_for_selection": False, "unknown_labels": "excluded upstream by the frozen cohort; never zero",
}


def plan_folds(cohort, protocol=ROLLING_PROTOCOL):
    times = np.sort(cohort.timestamp.unique())
    folds = []
    for test_time in times:
        validation_times = times[times + DAY < test_time][-protocol["validation_times"]:]
        train_times = times[times + DAY < validation_times[0]] if len(validation_times) else times[:0]
        record = {"test_time": int(test_time), "study_day": int(test_time // DAY + 1),
                  "validation_times": [int(t) for t in validation_times], "train_times": [int(t) for t in train_times]}
        if len(validation_times) < protocol["validation_times"] or len(train_times) < protocol["minimum_train_times"]:
            folds.append({**record, "status": "insufficient_history"})
            continue
        parts = {"train": cohort.loc[cohort.timestamp.isin(train_times)], "validation": cohort.loc[cohort.timestamp.isin(validation_times)],
                 "test": cohort.loc[cohort.timestamp.eq(test_time)]}
        sets = {name: part_summary(part) for name, part in parts.items()}
        balanced = all(min(s["positive"], s["negative"]) >= protocol["minimum_class_rows"] for s in sets.values())
        assert train_times.max() + DAY < validation_times.min() and validation_times.max() + DAY < test_time
        folds.append({**record, "status": "ready" if balanced else "insufficient_class_rows", "sets": sets})
    return folds


def ranking_metrics(frame, probability, ks=(5, 10)):
    """Mean per-(time, participant) Precision/Recall/NDCG@K over groups with at least one positive."""
    sides = []
    for own, partner in (("user_min", "user_max"), ("user_max", "user_min")):
        sides.append(pd.DataFrame({"timestamp": frame.timestamp.to_numpy(), "participant": frame[own].to_numpy(),
                                   "partner": frame[partner].to_numpy(), "label": frame.label_24h.to_numpy(),
                                   "p": np.asarray(frame[probability], dtype=float)}))
    long = pd.concat(sides, ignore_index=True)
    long = long.sort_values(["timestamp", "participant", "p", "partner"], ascending=[True, True, False, True], kind="mergesort")
    long["rank"] = long.groupby(["timestamp", "participant"]).cumcount() + 1
    groups = long.groupby(["timestamp", "participant"])
    positives = groups.label.sum()
    keep = positives.index[positives > 0]
    result = {"groups": int(len(keep)), "groups_without_positive": int((positives == 0).sum())}
    if not len(keep):
        return {**result, **{f"{m}_at_{k}": None for k in ks for m in ("precision", "recall", "ndcg")}}
    long = long.set_index(["timestamp", "participant"]).loc[keep].reset_index()
    long["gain"] = long.label / np.log2(long["rank"] + 1)
    for k in ks:
        top = long.loc[long["rank"] <= k].groupby(["timestamp", "participant"])
        hits, dcg = top.label.sum(), top.gain.sum()
        ideal = positives.loc[keep].clip(upper=k).map(lambda n: float(np.sum(1 / np.log2(np.arange(2, n + 2)))))
        result[f"precision_at_{k}"] = float((hits / k).mean())
        result[f"recall_at_{k}"] = float((hits / positives.loc[keep]).mean())
        result[f"ndcg_at_{k}"] = float((dcg / ideal).mean())
    return result


def fold_predictions(cohort, banks, folds, protocol=ROLLING_PROTOCOL, progress=print):
    rows, records = [], []
    for fold in folds:
        if fold["status"] != "ready":
            records.append(fold)
            continue
        parts = {name: cohort.loc[cohort.timestamp.isin(times)].copy()
                 for name, times in (("train", fold["train_times"]), ("validation", fold["validation_times"]), ("test", [fold["test_time"]]))}
        try:
            fitted = {days: fit_window(banks[days], parts["train"], parts["validation"], days)[0] for days in protocol["windows"]}
        except ValueError as exc:
            records.append({**fold, "status": "fit_failed", "reason": str(exc)})
            continue
        test = parts["test"].sort_values(KEYS).reset_index(drop=True)
        for days, models in fitted.items():
            X = model_input(banks[days], test, days)
            for name, model in models.items():
                test[f"p_{days}d_{name}"] = model.predict_proba(X)[:, 1]
                test[f"threshold_{days}d_{name}"] = model.threshold
        rows.append(test)
        records.append({**fold, "status": "evaluated"})
        if progress:
            progress(f"fold study_day={fold['study_day']} evaluated")
    predictions = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return predictions, records


def _score_columns(protocol):
    return [(days, name) for days in protocol["windows"] for name in protocol["base_protocol"]["models"]]


def _pooled_ap(frame, column):
    return binary_metrics(frame.label_24h, frame[column])["pr_auc_average_precision"]


def summarize(predictions, protocol=ROLLING_PROTOCOL):
    days = sorted(int(t) for t in predictions.timestamp.unique())
    metrics, per_day = [], []
    for window, name in _score_columns(protocol):
        column = f"p_{window}d_{name}"
        pooled = binary_metrics(predictions.label_24h, predictions[column])
        daily = []
        for t, group in predictions.groupby("timestamp"):
            # Thresholds differ per fold, so thresholded metrics are only reported per day.
            m = binary_metrics(group.label_24h, group[column], threshold=float(group[f"threshold_{window}d_{name}"].iloc[0]))
            daily.append(m["pr_auc_average_precision"])
            per_day.append({"window_days": window, "model": name, "study_day": int(t // DAY + 1), **m})
        metrics.append({"window_days": window, "model": name, "test_days": len(days),
                        **{key: pooled[key] for key in ("rows", "positive_rate", "pr_auc_average_precision", "roc_auc", "brier_score", "log_loss")},
                        "mean_daily_ap": float(np.mean([v for v in daily if v is not None])),
                        "ap_over_prevalence": pooled["pr_auc_average_precision"] / pooled["positive_rate"],
                        **ranking_metrics(predictions, column, protocol["ranking"]["k"])})
    policy = protocol["uncertainty"]
    blocks = {t: np.flatnonzero(predictions.timestamp.eq(t)) for t in days}
    rng = np.random.default_rng(policy["seed"])
    draws = [np.concatenate([blocks[t] for t in rng.choice(days, size=len(days), replace=True)])
             for _ in range(policy["bootstrap_repetitions"])] if len(days) >= policy["minimum_days_for_bootstrap_ci"] else []
    contrasts = []
    for a_name, a_days, b_name, b_days in protocol["contrasts"]:
        a, b = f"p_{a_days}d_{a_name}", f"p_{b_days}d_{b_name}"
        delta = lambda index: _pooled_ap(predictions.iloc[index], a) - _pooled_ap(predictions.iloc[index], b)
        daily = {int(t // DAY + 1): delta(index) for t, index in blocks.items()}
        record = {"contrast": f"{a_days}d {a_name} - {b_days}d {b_name}", "pooled_delta_ap": delta(np.arange(len(predictions))),
                  "daily_delta_ap": daily, "days_positive": int(sum(v > 0 for v in daily.values())), "test_days": len(days),
                  "confidence_interval_95": None, "status": "insufficient_days_for_ci"}
        if draws:
            values = [delta(index) for index in draws]
            record.update(confidence_interval_95=np.quantile(values, [0.025, 0.975]).tolist(), status="paired_day_block_bootstrap")
        contrasts.append(record)
    return {"metrics": metrics, "per_day": per_day, "contrasts": contrasts, "test_study_days": [int(t // DAY + 1) for t in days]}


def freeze(root, cohort_manifest, receipt, folds):
    root = Path(root)
    public_folds = [{key: fold[key] for key in ("study_day", "status", "test_time", "train_times", "validation_times")} for fold in folds]
    record = {"protocol": ROLLING_PROTOCOL, "folds": public_folds, "sample_key_hash": cohort_manifest["sample_key_hash"],
              "label_hash": cohort_manifest["label_hash"], "feature_hashes": {d: r["sha256"] for d, r in receipt.items()},
              "code_hashes": {name: sha256(root/name) for name in ("src/rolling_validation.py", "src/window_study.py", "src/window_models.py",
                                                                   "src/model_registry.py", "src/evaluate.py", "src/baselines.py")}}
    run_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    directory = root/"data/processed/rolling"/run_id
    immutable_json(directory/"PROTOCOL_FROZEN.json", {**record, "run_id": run_id})
    return run_id, directory, record


def public_result(run_id, record, folds, summary):
    status = {key: int(value) for key, value in pd.Series([f["status"] for f in folds]).value_counts().items()}
    return {"task": "T35", "run_id": run_id, "dataset_id": "copenhagen", "source_kind": "real_public_dataset",
            "protocol": ROLLING_PROTOCOL, "fold_status_counts": status,
            "folds": [{key: f[key] for key in ("study_day", "status")} | {"train_days": len(f["train_times"]), "validation_days": len(f["validation_times"])} for f in folds],
            "cohort_rows_sha256": record["sample_key_hash"], "cohort_labels_sha256": record["label_hash"], "feature_hashes": record["feature_hashes"],
            "code_hashes": record["code_hashes"], **summary,
            "interpretation": "Fixed-protocol rolling re-evaluation on previously exposed dates; day-block intervals treat days as "
                              "independent although participants/pairs repeat, so they are descriptive of day-to-day variation, not population inference."}


def run(root, public_dir, verify_only=False):
    root = Path(root)
    cohort, banks, manifest, receipt = read_inputs(root)
    # Rolling folds re-plan all frozen cohort times; the T19 split column is not used.
    cohort = cohort.drop(columns="split").reset_index(drop=True)
    folds = plan_folds(cohort)
    run_id, directory, record = freeze(root, manifest, receipt, folds)
    path = directory/"predictions.parquet"
    if verify_only:
        stored = json.loads((directory/"RUN_RECEIPT.json").read_text())
        if sha256(path) != stored["predictions_sha256"]:
            raise ValueError("Local rolling predictions changed.")
        predictions, folds = pd.read_parquet(path), stored["folds"]
    else:
        predictions, folds = fold_predictions(cohort, banks, folds)
        if path.exists():
            pd.testing.assert_frame_equal(pd.read_parquet(path), predictions)
        else:
            predictions.to_parquet(path, index=False)
        immutable_json(directory/"RUN_RECEIPT.json", {"predictions_sha256": sha256(path), "key_hash": row_hash(predictions),
                                                      "label_hash": row_hash(predictions, labels=True), "folds": folds})
    result = public_result(run_id, record, folds, summarize(predictions))
    public_dir = Path(public_dir)
    target = public_dir/"T35_RESULTS.json"
    if verify_only:
        if json.loads(target.read_text()) != json.loads(json.dumps(result, allow_nan=False)):
            raise ValueError("Public T35 aggregates differ from recomputation.")
    else:
        public_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--public-dir", type=Path, default=Path("studies/rolling_validation"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.root/args.public_dir, args.verify_only)
    print(json.dumps({"run_id": result["run_id"], "folds": result["fold_status_counts"], "contrasts": result["contrasts"]}, indent=1))


if __name__ == "__main__":
    main()
