"""T40 Hawkes baseline with a wider, prespecified half-life grid down to 5 minutes, on the frozen T35 folds.

T36 selected its smallest half-life (0.5h) on every fold. T40 extends the grid below that and again
chooses per fold on validation AP only. Short half-lives overflow T36's cumulative form, so the
excitation sum uses a log-sum-exp recursion; on the shared grid it must reproduce T36 scores.
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
from src.hawkes_baseline import HAWKES_PROTOCOL, select_per_fold
from src.preprocessing import preprocess_contacts
from src.rolling_validation import ROLLING_PROTOCOL, summarize
from src.window_cohort import DAY, KEYS, row_hash

HOUR = 3600
GRID_MINUTES = [5, 10, 15, 30, 60, 120, 480, 1440]
GRID = [minutes / 60 for minutes in GRID_MINUTES]
SHORT_PROTOCOL = {
    "version": 1, "task": "T40", "fold_plan": "frozen T35 run", "model": "T36 per-(t, pair) Hawkes MLE, unchanged",
    "half_life_minutes_grid": GRID_MINUTES,
    "grid_reason": "T36 chose its 30-minute lower boundary on every fold's validation set; 5 minutes is the scan-bin resolution",
    "selection": "per fold, maximum pooled validation AP; ties take the shorter half-life",
    "threshold": "maximum validation F1", "numerics": "log-sum-exp excitation recursion; equals T36 on shared half-lives",
    "contrasts": [["hawkes_wide", 7, "hawkes", 7], ["xgboost", 7, "hawkes_wide", 7]],
    "exposure": "Grid extension was motivated by T36 validation selections; T36 test scores had also been seen. Reported as a follow-up, not a pristine test.",
    "test_used_for_selection": False,
}


def excitation(events, beta):
    """A_i = sum_{j<i} exp(-beta(t_i - t_j)), stable for any beta."""
    log_cumulative = np.logaddexp.accumulate(beta*events)
    previous = np.concatenate([[-np.inf], log_cumulative[:-1]])
    return np.exp(previous - beta*events)


def fit_pair(events, end, beta):
    events = np.asarray(events, dtype=float)
    excite = beta*excitation(events, beta)
    compensator = np.sum(1 - np.exp(-beta*(end - events)))

    def negative(params):
        mu, alpha = params
        lam = mu + alpha*excite
        return (-(np.sum(np.log(lam)) - mu*end - alpha*compensator),
                -np.array([np.sum(1/lam) - end, np.sum(excite/lam) - compensator]))

    result = minimize(negative, [max(len(events)/end*0.5, 1e-3), 0.5], jac=True, method="L-BFGS-B", bounds=[(1e-6, None), (0.0, 0.99)])
    return float(result.x[0]), float(result.x[1])


def forecast(events, end, beta, horizon=24.0):
    mu, alpha = fit_pair(events, end, beta)
    age = end - np.asarray(events, dtype=float)
    return float(1 - np.exp(-(mu*horizon + alpha*np.sum(np.exp(-beta*age) - np.exp(-beta*(age + horizon))))))


def scores(contacts_path, rows, grid=GRID, days=7, progress=print):
    out = rows[KEYS].copy().reset_index(drop=True)
    values = {hours: np.full(len(out), np.nan) for hours in grid}
    source = ds.dataset(contacts_path)
    for t, index in out.groupby("timestamp").groups.items():
        t = int(t)
        frame = source.to_table(columns=["timestamp", "user_min", "user_max"],
                                filter=(ds.field("timestamp") >= t - days*DAY) & (ds.field("timestamp") < t)).to_pandas()
        history = frame.drop_duplicates().sort_values("timestamp").groupby(["user_min", "user_max"]).timestamp.apply(np.asarray)
        for i in index:
            events = (history.loc[(int(out.at[i, "user_min"]), int(out.at[i, "user_max"]))] - (t - days*DAY))/HOUR
            for hours in grid:
                values[hours][i] = forecast(events, days*24.0, float(np.log(2)/hours))
        if progress:
            progress(f"t={t} scored {len(index)} candidates")
    for hours in grid:
        out[f"hawkes_{hours}h"] = values[hours]
    return out


def run(root, public_dir, verify_only=False):
    root = Path(root)
    t35 = json.loads((root/"studies/rolling_validation/T35_RESULTS.json").read_text())
    t36 = json.loads((root/"studies/hawkes_baseline/T36_RESULTS.json").read_text())
    rolling, hawkes_dir = root/"data/processed/rolling"/t35["run_id"], root/"data/processed/hawkes"/t36["run_id"]
    receipt = json.loads((rolling/"RUN_RECEIPT.json").read_text())
    if sha256(rolling/"predictions.parquet") != receipt["predictions_sha256"]:
        raise ValueError("Frozen T35 predictions changed.")
    t36_path = hawkes_dir/"hawkes_scores.parquet"
    if sha256(t36_path) != json.loads((hawkes_dir/"RUN_RECEIPT.json").read_text())["scores_sha256"]:
        raise ValueError("Frozen T36 Hawkes scores changed.")
    folds = receipt["folds"]
    cohort = pd.read_parquet(root/"data/processed/window_study"/json.loads((root/"data/processed/window_study/T19_COHORT_MANIFEST.json").read_text())["split_filename"])
    t36_scores = pd.read_parquet(t36_path)
    rows = cohort.loc[cohort.timestamp.isin(t36_scores.timestamp.unique())]
    record = {"protocol": SHORT_PROTOCOL, "t35_run_id": t35["run_id"], "t36_run_id": t36["run_id"], "rows_sha256": row_hash(rows, labels=True),
              "code_hashes": {name: sha256(root/name) for name in ("src/hawkes_short.py", "src/hawkes_baseline.py", "src/rolling_validation.py")}}
    run_id = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    directory = root/"data/processed/hawkes_short"/run_id
    immutable_json(directory/"PROTOCOL_FROZEN.json", {**record, "run_id": run_id})
    path = directory/"scores.parquet"
    if verify_only:
        if sha256(path) != json.loads((directory/"RUN_RECEIPT.json").read_text())["scores_sha256"]:
            raise ValueError("Local T40 scores changed.")
        wide = pd.read_parquet(path)
    else:
        processed = preprocess_contacts(root/"data/raw/copenhagen/bt_symmetric.csv", "Copenhagen", root/"data/processed")
        wide = scores(processed.directory/"contacts.parquet", rows)
        if path.exists():
            pd.testing.assert_frame_equal(pd.read_parquet(path), wide)
        else:
            wide.to_parquet(path, index=False)
    renamed = t36_scores.rename(columns={f"hawkes_{hours}h": f"t36_{hours}" for hours in HAWKES_PROTOCOL["half_life_hours_grid"]})
    shared = renamed.merge(wide, on=KEYS, validate="one_to_one")
    parity = {}
    for hours in HAWKES_PROTOCOL["half_life_hours_grid"]:
        difference = float(np.max(np.abs(shared[f"t36_{hours}"] - shared[f"hawkes_{float(hours)}h"])))
        parity[str(int(hours*60))] = difference
        if difference > 1e-6:
            raise ValueError(f"Stable recursion differs from T36 at {hours}h: {difference}")
    if not verify_only:
        immutable_json(directory/"RUN_RECEIPT.json", {"scores_sha256": sha256(path), "rows": len(wide), "t36_parity_max_abs": parity})
    selected, selections = select_per_fold(wide, rows, folds, grid=GRID)
    selected = selected.rename(columns={"p_7d_hawkes": "p_7d_hawkes_wide", "threshold_7d_hawkes": "threshold_7d_hawkes_wide"})
    original, _ = select_per_fold(t36_scores, rows, folds)
    combined = (pd.read_parquet(rolling/"predictions.parquet").merge(original, on=KEYS, validate="one_to_one")
                .merge(selected, on=KEYS, validate="one_to_one"))
    protocol = {**ROLLING_PROTOCOL, "windows": [7], "base_protocol": {**ROLLING_PROTOCOL["base_protocol"], "models": ["hawkes_wide", "hawkes", "xgboost"]},
                "contrasts": SHORT_PROTOCOL["contrasts"]}
    summary = summarize(combined, protocol)
    summary.pop("per_day")
    for item in selections:
        item["selected_half_life_minutes"] = round(item.pop("selected_half_life_hours")*60)
        item["validation_ap_by_half_life_minutes"] = {str(round(float(h)*60)): v for h, v in item.pop("validation_ap_by_half_life").items()}
    result = {"task": "T40", "run_id": run_id, "dataset_id": "copenhagen", "source_kind": "real_public_dataset", "protocol": SHORT_PROTOCOL,
              "t35_run_id": t35["run_id"], "t36_run_id": t36["run_id"], "t36_parity_max_abs": parity, "scored_rows": len(wide),
              "fold_selections": selections, "code_hashes": record["code_hashes"], **summary}
    target = Path(public_dir)/"T40_RESULTS.json"
    if verify_only:
        if json.loads(target.read_text()) != json.loads(json.dumps(result, allow_nan=False)):
            raise ValueError("Public T40 aggregates differ from recomputation.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--public-dir", type=Path, default=Path("studies/hawkes_short"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.root/args.public_dir, args.verify_only)
    print(json.dumps({"selections": [s["selected_half_life_minutes"] for s in result["fold_selections"]], "parity": result["t36_parity_max_abs"],
                      "contrasts": [{k: c[k] for k in ("contrast", "pooled_delta_ap", "confidence_interval_95", "days_positive")} for c in result["contrasts"]]}, indent=1))


if __name__ == "__main__":
    main()
