"""T39 descriptive per-day analysis of frozen T35 7d predictions; no fitting, no selection.

Each test day is described by its size, prevalence and pre-t activity/coverage profile (from the frozen
T20 7d features), next to AP and AP lift over prevalence. Weekday labels are not used because the
Copenhagen weekday origin is unconfirmed.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.baseline_audit import sha256
from src.evaluate import binary_metrics
from src.hawkes_baseline import select_per_fold
from src.window_cohort import DAY, KEYS
from src.window_study import read_inputs

MODELS = ["xgboost", "logistic_regression", "historical_frequency", "hawkes"]
DESCRIPTORS = {
    "rows": "candidate pairs that day",
    "positive_rate": "share of reliably labeled candidates with a contact in (t,t+24h]",
    "mean_pair_contact_days": "mean distinct contact days in [t-7d,t)",
    "mean_recency_hours": "mean hours since the last contact before t",
    "mean_participant_activity": "mean of both participants' contact rows in [t-7d,t)",
    "mean_min_scan_coverage": "mean of the lower of the two participants' 7d scan coverage",
    "share_contact_days_1": "share of candidates whose only contact day in the window is the last day",
}
PROTOCOL = {"version": 1, "task": "T39", "source": "frozen T35 predictions + T36 per-fold Hawkes + T20 7d features",
            "unit": "one test day (11 days)", "statistics": "per-day AP, AP/prevalence, descriptors; Spearman rho over 11 days",
            "weekday": None, "fitting": False, "selection": False,
            "interpretation_limit": "11 dependent days; correlations are descriptive, not tests"}


def day_table(frame, bank):
    joined = frame.merge(bank, on=KEYS, validate="one_to_one")
    rows = []
    for t, day in joined.groupby("timestamp"):
        record = {"study_day": int(t // DAY + 1), "rows": len(day), "positive_rate": float(day.label_24h.mean()),
                  "mean_pair_contact_days": float(day.pair_contact_days.mean()),
                  "mean_recency_hours": float(day.recency_seconds.mean() / 3600),
                  "mean_participant_activity": float(day[["participant_a_activity", "participant_b_activity"]].mean(axis=1).mean()),
                  "mean_min_scan_coverage": float(day[["scan_coverage_a", "scan_coverage_b"]].min(axis=1).mean()),
                  "share_contact_days_1": float(day.pair_contact_days.eq(1).mean())}
        for model in MODELS:
            ap = binary_metrics(day.label_24h, day[f"p_7d_{model}"])["pr_auc_average_precision"]
            record[f"ap_{model}"] = ap
            record[f"lift_{model}"] = ap / record["positive_rate"]
        rows.append(record)
    return rows


def correlations(rows):
    table = pd.DataFrame(rows)
    out = []
    for target in ("ap_xgboost", "lift_xgboost"):
        for name in DESCRIPTORS:
            rho, _ = spearmanr(table[name], table[target])
            out.append({"target": target, "descriptor": name, "spearman_rho": float(rho)})
    return out


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
    hawkes, _ = select_per_fold(pd.read_parquet(hawkes_dir/"hawkes_scores.parquet"), cohort.drop(columns="split"), receipt["folds"])
    frame = pd.read_parquet(rolling/"predictions.parquet").merge(hawkes, on=KEYS, validate="one_to_one")
    rows = day_table(frame, banks[7])
    table = pd.DataFrame(rows)
    result = {"task": "T39", "dataset_id": "copenhagen", "source_kind": "real_public_dataset", "protocol": PROTOCOL,
              "descriptors": DESCRIPTORS, "t35_run_id": t35["run_id"], "t36_run_id": t36["run_id"], "per_day": rows,
              "correlations": correlations(rows),
              "summary": {"ap_xgboost_range": [float(table.ap_xgboost.min()), float(table.ap_xgboost.max())],
                          "lift_xgboost_range": [float(table.lift_xgboost.min()), float(table.lift_xgboost.max())],
                          "positive_rate_range": [float(table.positive_rate.min()), float(table.positive_rate.max())],
                          "days_xgboost_best_of_models": int(sum(r["ap_xgboost"] >= max(r[f"ap_{m}"] for m in MODELS) for r in rows))},
              "code_sha256": sha256(root/"src/day_analysis.py")}
    target = Path(public_dir)/"T39_RESULTS.json"
    if verify_only:
        if json.loads(target.read_text()) != json.loads(json.dumps(result, allow_nan=False)):
            raise ValueError("Public T39 aggregates differ from recomputation.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--public-dir", type=Path, default=Path("studies/day_analysis"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.root/args.public_dir, args.verify_only)
    print(json.dumps({"per_day": result["per_day"], "correlations": result["correlations"], "summary": result["summary"]}, indent=1))


if __name__ == "__main__":
    main()
