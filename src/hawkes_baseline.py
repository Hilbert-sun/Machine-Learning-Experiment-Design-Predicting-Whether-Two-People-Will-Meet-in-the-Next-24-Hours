"""T36 per-pair exponential-kernel Hawkes baseline on the frozen T35 rolling fold plan.

Each (t, pair) fits its own background rate and branching ratio by maximum likelihood on the pair's
distinct contact times in [t-7d, t) only; no labels are used for fitting. The decay half-life is
chosen per fold on that fold's validation times only; test scores are never used for a choice.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from scipy.optimize import minimize

from src.baseline_audit import immutable_json, sha256
from src.evaluate import binary_metrics, choose_threshold
from src.preprocessing import preprocess_contacts
from src.rolling_validation import ROLLING_PROTOCOL, summarize
from src.window_cohort import DAY, KEYS, row_hash

HOUR = 3600
HAWKES_PROTOCOL = {
    "version": 1, "task": "T36", "fold_plan": "frozen T35 run (verified receipt and predictions checksum)",
    "history_window_days": 7, "events": "distinct contact timestamps of the pair in [t-7d,t), hours",
    "intensity": "lambda(s) = mu + alpha*beta*sum exp(-beta(s-t_i)); mu >= 1e-6/h, 0 <= alpha <= 0.99",
    "fit": "per (t, pair) concave log-likelihood, L-BFGS-B with analytic gradient; no labels",
    "forecast": "P(>=1 event in (t,t+24h]) = 1-exp(-Lambda); Lambda ignores excitation by future events (lower bound)",
    "half_life_hours_grid": [0.5, 2, 8, 24],
    "selection": "per fold, maximum pooled AP on that fold's validation times; ties take the earlier grid value",
    "threshold": "maximum validation F1 at the selected half-life (same rule as T21/T22)",
    "comparison_window_days": 7, "compared_models": ["hawkes", "xgboost", "logistic_regression", "historical_frequency"],
    "contrasts": [["xgboost", 7, "hawkes", 7], ["hawkes", 7, "historical_frequency", 7], ["hawkes", 7, "logistic_regression", 7]],
    "test_used_for_selection": False,
    "limitations": "Unobserved scan gaps count as no events; contact timestamps are 5-minute scan bins, not continuous time.",
}


def fit_pair(events, end, beta):
    """MLE (mu, alpha) for event times (hours, ascending, < end) observed on [0, end)."""
    events = np.asarray(events, dtype=float)
    # A_i = sum_{j<i} exp(-beta(t_i-t_j)) via an exclusive cumulative sum (t <= 168h keeps exp finite).
    growth = np.exp(beta*events)
    A = np.exp(-beta*events)*np.concatenate([[0.0], np.cumsum(growth)[:-1]])
    excite = beta*A
    compensator = np.sum(1 - np.exp(-beta*(end - events)))

    def negative(params):
        mu, alpha = params
        lam = mu + alpha*excite
        value = -(np.sum(np.log(lam)) - mu*end - alpha*compensator)
        gradient = -np.array([np.sum(1/lam) - end, np.sum(excite/lam) - compensator])
        return value, gradient

    start = [max(len(events)/end*0.5, 1e-3), 0.5]
    result = minimize(negative, start, jac=True, method="L-BFGS-B", bounds=[(1e-6, None), (0.0, 0.99)])
    return float(result.x[0]), float(result.x[1])


def forecast(events, end, beta, horizon=24.0):
    mu, alpha = fit_pair(events, end, beta)
    age = end - np.asarray(events, dtype=float)
    expected = mu*horizon + alpha*np.sum(np.exp(-beta*age) - np.exp(-beta*(age + horizon)))
    return float(1 - np.exp(-expected))


def half_life_beta(hours):
    return float(np.log(2)/hours)


def hawkes_scores(contacts_path, rows, grid=HAWKES_PROTOCOL["half_life_hours_grid"], days=HAWKES_PROTOCOL["history_window_days"], progress=print):
    """Score every (t, pair) row for every half-life using only [t-days, t) contacts."""
    out = rows[KEYS].copy().reset_index(drop=True)
    for hours in grid:
        out[f"hawkes_{hours}h"] = np.nan
    source = ds.dataset(contacts_path)
    for t, index in out.groupby("timestamp").groups.items():
        t = int(t)
        frame = source.to_table(columns=["timestamp", "user_min", "user_max"],
                                filter=(ds.field("timestamp") >= t - days*DAY) & (ds.field("timestamp") < t)).to_pandas()
        history = frame.drop_duplicates().sort_values("timestamp").groupby(["user_min", "user_max"]).timestamp.apply(np.asarray)
        for i in index:
            pair = (int(out.at[i, "user_min"]), int(out.at[i, "user_max"]))
            if pair not in history.index:
                raise ValueError("Candidate pair has no [t-1d,t) contact; cohort contract broken.")
            events = (history.loc[pair] - (t - days*DAY))/HOUR
            for hours in grid:
                out.at[i, f"hawkes_{hours}h"] = forecast(events, days*24.0, half_life_beta(hours))
        if progress:
            progress(f"t={t} scored {len(index)} candidates")
    return out


def select_per_fold(scores, labels, folds, grid=HAWKES_PROTOCOL["half_life_hours_grid"]):
    """Choose half-life and threshold per fold from validation times; return test-time predictions."""
    joined = scores.merge(labels[KEYS + ["label_24h"]], on=KEYS, validate="one_to_one")
    selections, parts = [], []
    for fold in folds:
        if fold["status"] != "evaluated":
            continue
        validation = joined.loc[joined.timestamp.isin(fold["validation_times"])]
        aps = {hours: binary_metrics(validation.label_24h, validation[f"hawkes_{hours}h"])["pr_auc_average_precision"] for hours in grid}
        best = max(grid, key=lambda hours: (aps[hours], -grid.index(hours)))
        threshold = choose_threshold(validation.label_24h, validation[f"hawkes_{best}h"])
        test = joined.loc[joined.timestamp.eq(fold["test_time"]), KEYS].copy()
        test["p_7d_hawkes"] = joined.loc[test.index, f"hawkes_{best}h"].to_numpy()
        test["threshold_7d_hawkes"] = threshold
        parts.append(test)
        selections.append({"study_day": fold["study_day"], "selected_half_life_hours": best, "threshold": threshold,
                           "validation_ap_by_half_life": {str(h): aps[h] for h in grid}})
    return pd.concat(parts, ignore_index=True), selections


def comparison_protocol():
    return {**ROLLING_PROTOCOL, "windows": [HAWKES_PROTOCOL["comparison_window_days"]],
            "base_protocol": {**ROLLING_PROTOCOL["base_protocol"], "models": HAWKES_PROTOCOL["compared_models"]},
            "contrasts": HAWKES_PROTOCOL["contrasts"]}


def run(root, public_dir, verify_only=False):
    root = Path(root)
    t35 = json.loads((root/"studies/rolling_validation/T35_RESULTS.json").read_text())
    rolling = root/"data/processed/rolling"/t35["run_id"]
    receipt = json.loads((rolling/"RUN_RECEIPT.json").read_text())
    if sha256(rolling/"predictions.parquet") != receipt["predictions_sha256"]:
        raise ValueError("Frozen T35 predictions changed.")
    predictions = pd.read_parquet(rolling/"predictions.parquet")
    folds = receipt["folds"]
    processed = preprocess_contacts(root/"data/raw/copenhagen/bt_symmetric.csv", "Copenhagen", root/"data/processed")
    contacts = processed.directory/"contacts.parquet"
    cohort = pd.read_parquet(root/"data/processed/window_study"/json.loads((root/"data/processed/window_study/T19_COHORT_MANIFEST.json").read_text())["split_filename"])
    needed = sorted({t for f in folds if f["status"] == "evaluated" for t in f["validation_times"] + [f["test_time"]]})
    rows = cohort.loc[cohort.timestamp.isin(needed)]
    record = {"protocol": HAWKES_PROTOCOL, "t35_run_id": t35["run_id"], "t35_predictions_sha256": receipt["predictions_sha256"],
              "contacts_sha256": sha256(contacts), "scored_rows_sha256": row_hash(rows, labels=True),
              "code_hashes": {name: sha256(root/name) for name in ("src/hawkes_baseline.py", "src/rolling_validation.py", "src/evaluate.py")}}
    run_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    directory = root/"data/processed/hawkes"/run_id
    immutable_json(directory/"PROTOCOL_FROZEN.json", {**record, "run_id": run_id})
    path = directory/"hawkes_scores.parquet"
    if verify_only:
        if sha256(path) != json.loads((directory/"RUN_RECEIPT.json").read_text())["scores_sha256"]:
            raise ValueError("Local Hawkes scores changed.")
        scores = pd.read_parquet(path)
    else:
        scores = hawkes_scores(contacts, rows)
        if path.exists():
            pd.testing.assert_frame_equal(pd.read_parquet(path), scores)
        else:
            scores.to_parquet(path, index=False)
        immutable_json(directory/"RUN_RECEIPT.json", {"scores_sha256": sha256(path), "rows": len(scores)})
    hawkes, selections = select_per_fold(scores, rows, folds)
    combined = predictions.merge(hawkes, on=KEYS, how="left", validate="one_to_one")
    if combined.p_7d_hawkes.isna().any():
        raise ValueError("Hawkes predictions missing for T35 test rows.")
    summary = summarize(combined, comparison_protocol())
    result = {"task": "T36", "run_id": run_id, "dataset_id": "copenhagen", "source_kind": "real_public_dataset",
              "protocol": HAWKES_PROTOCOL, "t35_run_id": t35["run_id"], "fold_selections": selections,
              "scored_rows": len(scores), "code_hashes": record["code_hashes"], **summary,
              "interpretation": "Same frozen T35 folds and previously exposed test dates; per-pair point-process baseline without labels. "
                                "Day-block intervals describe day-to-day variation only; participants/pairs repeat."}
    target = Path(public_dir)/"T36_RESULTS.json"
    if verify_only:
        if json.loads(target.read_text()) != json.loads(json.dumps(result, allow_nan=False)):
            raise ValueError("Public T36 aggregates differ from recomputation.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--public-dir", type=Path, default=Path("studies/hawkes_baseline"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.root/args.public_dir, args.verify_only)
    print(json.dumps({"run_id": result["run_id"], "selections": [s["selected_half_life_hours"] for s in result["fold_selections"]],
                      "contrasts": [{k: c[k] for k in ("contrast", "pooled_delta_ap", "confidence_interval_95", "days_positive")} for c in result["contrasts"]]}, indent=1))


if __name__ == "__main__":
    main()
