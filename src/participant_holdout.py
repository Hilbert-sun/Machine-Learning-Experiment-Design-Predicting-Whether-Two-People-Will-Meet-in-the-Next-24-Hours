"""T38 leave-participants-out validation on the frozen T35 rolling folds.

Participants are split into groups A/B by a salted hash fixed before fitting. Models are trained and
thresholded on A–A pairs only and tested on B–B (both unseen) and A–B (one unseen) pairs. Test dates
were exposed before; the unseen dimension here is people.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_audit import immutable_json, sha256
from src.hawkes_baseline import select_per_fold
from src.rolling_validation import ROLLING_PROTOCOL, summarize
from src.window_cohort import KEYS, part_summary, row_hash
from src.window_study import PROTOCOL, fit_window, model_input, read_inputs

HOLDOUT_PROTOCOL = {
    "version": 1, "task": "T38", "fold_plan": "frozen T35 run", "window_days": 7,
    "partition": "group = sha256('T38|salt|dataset|participant') mod 2; A=0 trains, B=1 is held out",
    "salts": [0, 1, 2, 3, 4],
    "train_population": "A–A pairs at the fold's train and validation times",
    "test_populations": {"unseen_both": "B–B pairs", "unseen_one": "A–B pairs"},
    "models": PROTOCOL["models"], "parameters": PROTOCOL["parameters"], "seed": PROTOCOL["seed"],
    "threshold": "maximum validation F1 on A–A validation pairs", "calibration": None,
    "minimum_class_rows": 20, "fold_gate": "drop a fold for this partition if train, validation or a test population lacks 20 rows per class",
    "references": {"xgboost_seen": "T35 7d XGBoost trained on all participants", "hawkes": "T36 label-free Hawkes"},
    "contrasts": [["xgboost_holdout", 7, "xgboost", 7], ["xgboost_holdout", 7, "hawkes", 7],
                  ["xgboost_holdout", 7, "logistic_regression_holdout", 7]],
    "features": "frozen T20 7d banks; network features use every participant's past contacts (no labels)",
    "test_used_for_selection": False,
}
MODELS = ["xgboost_holdout", "logistic_regression_holdout", "historical_frequency_holdout", "xgboost", "hawkes"]


def group_of(participant, salt, dataset="copenhagen"):
    digest = hashlib.sha256(f"T38|{salt}|{dataset}|{int(participant)}".encode()).hexdigest()
    return int(digest, 16) % 2


def label_groups(frame, salt):
    a = frame.user_min.map(lambda u: group_of(u, salt))
    b = frame.user_max.map(lambda u: group_of(u, salt))
    return np.select([(a == 0) & (b == 0), (a == 1) & (b == 1)], ["train", "unseen_both"], "unseen_one")


def holdout_predictions(cohort, bank, folds, salt, protocol=HOLDOUT_PROTOCOL, progress=print):
    cohort = cohort.assign(population=label_groups(cohort, salt))
    parts, records = [], []
    for fold in folds:
        if fold["status"] != "evaluated":
            continue
        train = cohort.loc[cohort.timestamp.isin(fold["train_times"]) & cohort.population.eq("train")]
        validation = cohort.loc[cohort.timestamp.isin(fold["validation_times"]) & cohort.population.eq("train")]
        test = cohort.loc[cohort.timestamp.eq(fold["test_time"]) & cohort.population.ne("train")]
        sets = {"train": train, "validation": validation, **{name: test.loc[test.population.eq(name)] for name in protocol["test_populations"]}}
        counts = {name: part_summary(part) for name, part in sets.items()}
        if any(min(c["positive"], c["negative"]) < protocol["minimum_class_rows"] for c in counts.values()):
            records.append({"study_day": fold["study_day"], "status": "insufficient_class_rows",
                            "rows": {name: c["rows"] for name, c in counts.items()}})
            continue
        models, _ = fit_window(bank, train, validation, protocol["window_days"])
        out = test.loc[:, KEYS + ["population"]].sort_values(KEYS).reset_index(drop=True)
        X = model_input(bank, out, protocol["window_days"])
        for name, model in models.items():
            out[f"p_7d_{name}_holdout"] = model.predict_proba(X)[:, 1]
            out[f"threshold_7d_{name}_holdout"] = model.threshold
        parts.append(out)
        records.append({"study_day": fold["study_day"], "status": "evaluated", "rows": {name: c["rows"] for name, c in counts.items()}})
        if progress:
            progress(f"salt={salt} fold study_day={fold['study_day']} evaluated")
    return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=KEYS + ["population"])), records


def comparison_protocol():
    return {**ROLLING_PROTOCOL, "windows": [7], "base_protocol": {**ROLLING_PROTOCOL["base_protocol"], "models": MODELS},
            "contrasts": HOLDOUT_PROTOCOL["contrasts"]}


def across_partitions(by_salt):
    rows = []
    for population in HOLDOUT_PROTOCOL["test_populations"]:
        for model in MODELS:
            values = [next(m for m in by_salt[s][population]["metrics"] if m["model"] == model) for s in by_salt]
            rows.append({"population": population, "model": model, **{
                f"{key}_{stat}": float(fn([v[key] for v in values]))
                for key in ("pr_auc_average_precision", "roc_auc", "brier_score", "ndcg_at_5", "precision_at_5")
                for stat, fn in (("mean", np.mean), ("min", np.min), ("max", np.max))}})
        for contrast in HOLDOUT_PROTOCOL["contrasts"]:
            name = f"{contrast[1]}d {contrast[0]} - {contrast[3]}d {contrast[2]}"
            values = [next(c for c in by_salt[s][population]["contrasts"] if c["contrast"] == name) for s in by_salt]
            rows.append({"population": population, "contrast": name,
                         "pooled_delta_ap_by_salt": [v["pooled_delta_ap"] for v in values],
                         "intervals_excluding_zero": int(sum(v["confidence_interval_95"] is not None and
                                                             (v["confidence_interval_95"][0] > 0 or v["confidence_interval_95"][1] < 0) for v in values)),
                         "partitions": len(values)})
    return rows


def run(root, public_dir, verify_only=False):
    root = Path(root)
    cohort, banks, manifest, _ = read_inputs(root)
    cohort = cohort.drop(columns="split")
    t35 = json.loads((root/"studies/rolling_validation/T35_RESULTS.json").read_text())
    t36 = json.loads((root/"studies/hawkes_baseline/T36_RESULTS.json").read_text())
    rolling, hawkes_dir = root/"data/processed/rolling"/t35["run_id"], root/"data/processed/hawkes"/t36["run_id"]
    receipt = json.loads((rolling/"RUN_RECEIPT.json").read_text())
    if sha256(rolling/"predictions.parquet") != receipt["predictions_sha256"]:
        raise ValueError("Frozen T35 predictions changed.")
    if sha256(hawkes_dir/"hawkes_scores.parquet") != json.loads((hawkes_dir/"RUN_RECEIPT.json").read_text())["scores_sha256"]:
        raise ValueError("Frozen T36 Hawkes scores changed.")
    folds = receipt["folds"]
    record = {"protocol": HOLDOUT_PROTOCOL, "t35_run_id": t35["run_id"], "t36_run_id": t36["run_id"],
              "cohort_rows_sha256": manifest["label_hash"],
              "code_hashes": {name: sha256(root/name) for name in ("src/participant_holdout.py", "src/rolling_validation.py", "src/window_study.py")}}
    run_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    directory = root/"data/processed/participant_holdout"/run_id
    immutable_json(directory/"PROTOCOL_FROZEN.json", {**record, "run_id": run_id})
    seen = pd.read_parquet(rolling/"predictions.parquet")[KEYS + ["label_24h", "p_7d_xgboost", "threshold_7d_xgboost"]]
    hawkes, _ = select_per_fold(pd.read_parquet(hawkes_dir/"hawkes_scores.parquet"), cohort, folds)
    by_salt, fold_records = {}, {}
    for salt in HOLDOUT_PROTOCOL["salts"]:
        path = directory/f"predictions_salt{salt}.parquet"
        if verify_only:
            stored = json.loads((directory/"RUN_RECEIPT.json").read_text())
            if sha256(path) != stored["predictions_sha256"][str(salt)]:
                raise ValueError("Local T38 predictions changed.")
            predictions, fold_records[salt] = pd.read_parquet(path), stored["folds"][str(salt)]
        else:
            predictions, fold_records[salt] = holdout_predictions(cohort, banks[7], folds, salt)
            if path.exists():
                pd.testing.assert_frame_equal(pd.read_parquet(path), predictions)
            else:
                predictions.to_parquet(path, index=False)
        combined = predictions.merge(seen, on=KEYS, validate="one_to_one").merge(hawkes, on=KEYS, validate="one_to_one")
        by_salt[salt] = {population: summarize(combined.loc[combined.population.eq(population)], comparison_protocol())
                         for population in HOLDOUT_PROTOCOL["test_populations"]}
    if not verify_only:
        immutable_json(directory/"RUN_RECEIPT.json", {"predictions_sha256": {str(s): sha256(directory/f"predictions_salt{s}.parquet") for s in by_salt},
                                                      "folds": {str(s): r for s, r in fold_records.items()}})
    for salt in by_salt:
        for population in by_salt[salt]:
            by_salt[salt][population].pop("per_day")
    result = {"task": "T38", "run_id": run_id, "dataset_id": "copenhagen", "source_kind": "real_public_dataset", "protocol": HOLDOUT_PROTOCOL,
              "t35_run_id": t35["run_id"], "t36_run_id": t36["run_id"], "code_hashes": record["code_hashes"],
              "fold_records": {str(s): r for s, r in fold_records.items()}, "by_partition": {str(s): v for s, v in by_salt.items()},
              "across_partitions": across_partitions(by_salt),
              "interpretation": "People in B–B pairs never appear in training labels; test dates were exposed before. "
                                "Day-block intervals per partition describe day-to-day variation; partitions are not independent replications."}
    target = Path(public_dir)/"T38_RESULTS.json"
    if verify_only:
        if json.loads(target.read_text()) != json.loads(json.dumps(result, allow_nan=False)):
            raise ValueError("Public T38 aggregates differ from recomputation.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--public-dir", type=Path, default=Path("studies/participant_holdout"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.root/args.public_dir, args.verify_only)
    print(json.dumps([r for r in result["across_partitions"] if "contrast" in r or r["model"] in ("xgboost_holdout", "xgboost", "hawkes")], indent=1))


if __name__ == "__main__":
    main()
