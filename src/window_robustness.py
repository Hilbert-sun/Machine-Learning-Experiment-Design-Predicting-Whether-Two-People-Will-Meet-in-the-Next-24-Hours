"""T22 intermediate window, predeclared forward folds and paired temporal diagnostics."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_audit import immutable_json, sha256, verify_frozen
from src.evaluate import binary_metrics
from src.label_builder import build_labels
from src.model_registry import ModelRegistry
from src.preprocessing import preprocess_contacts
from src.window_cohort import DAY, KEYS, past_pairs, part_summary, row_hash
from src.window_study import PROTOCOL, read_inputs, fit_window, evaluate_windows, verify_exported_metrics


def forward_folds(cohort, policy):
    times = np.sort(cohort.timestamp.unique())
    folds = []
    for study_day in policy["test_start_study_days"]:
        start = (study_day-1)*DAY + 8*3600
        validation_times = times[times+DAY < start][-policy["validation_days"]:]
        if len(validation_times) < policy["validation_days"]:
            folds.append({"study_day": study_day, "status": "insufficient_days"})
            continue
        train = cohort.loc[cohort.timestamp+DAY < validation_times[0]].copy()
        validation = cohort.loc[cohort.timestamp.isin(validation_times)].copy()
        test = cohort.loc[cohort.timestamp.ge(start) & cohort.timestamp.lt(start+policy["test_days"]*DAY)].copy()
        parts = {"train":train, "validation":validation, "test":test}
        summaries = {name:part_summary(p) for name,p in parts.items()}
        ready = (summaries["train"]["distinct_prediction_days"] >= policy["minimum_train_days"]
                 and summaries["test"]["distinct_prediction_days"] == policy["test_days"]
                 and all(min(s["positive"],s["negative"]) >= policy["minimum_class_rows"] for s in summaries.values()))
        if ready:
            assert train.timestamp.max()+DAY < validation.timestamp.min()
            assert validation.timestamp.max()+DAY < test.timestamp.min()
        folds.append({"study_day":study_day, "status":"ready" if ready else "insufficient_days", "sets":summaries,
                      "parts":parts if ready else None})
    return folds


def paired_uncertainty(first, second, model, policy, *, seed=42):
    first, second = (p.sort_values(KEYS).reset_index(drop=True) for p in (first,second))
    if row_hash(first, labels=True) != row_hash(second, labels=True):
        raise ValueError("Paired window predictions have different keys/labels.")
    name = f"p_{model}"
    def delta(index):
        a = binary_metrics(first.label_24h.iloc[index], first[name].iloc[index])["pr_auc_average_precision"]
        b = binary_metrics(second.label_24h.iloc[index], second[name].iloc[index])["pr_auc_average_precision"]
        return None if a is None or b is None else b-a
    days = sorted(first.timestamp.unique())
    per_day = [{"timestamp":int(t), "study_day":int(t//DAY+1), "rows":int(first.timestamp.eq(t).sum()),
                "delta_AP_7d_minus_1d":delta(np.flatnonzero(first.timestamp.eq(t)))} for t in days]
    leave_one_out = [{"removed_study_day":int(t//DAY+1), "delta_AP_7d_minus_1d":delta(np.flatnonzero(~first.timestamp.eq(t)))} for t in days] if len(days)>1 else []
    ranges = [r["delta_AP_7d_minus_1d"] for r in leave_one_out if r["delta_AP_7d_minus_1d"] is not None]
    result = {"model":model, "distinct_prediction_days":len(days), "pooled_delta_AP_7d_minus_1d":delta(np.arange(len(first))),
              "paired_by_day":per_day, "leave_one_day_out":leave_one_out,
              "descriptive_leave_one_day_out_range":[min(ranges),max(ranges)] if ranges else None,
              "confidence_interval":None, "status":"insufficient_days_for_ci",
              "interpretation":"Days/participants/pairs are dependent; descriptive sensitivity is not a confidence interval or significance test."}
    if len(days) >= policy["minimum_days_for_bootstrap_ci"]:
        rng = np.random.default_rng(seed)
        blocks = {t:np.flatnonzero(first.timestamp.eq(t)) for t in days}
        differences = [delta(np.concatenate([blocks[t] for t in rng.choice(days,size=len(days),replace=True)])) for _ in range(policy["bootstrap_repetitions"])]
        differences = [d for d in differences if d is not None]
        if differences:
            result.update(status="paired_day_block_bootstrap", confidence_interval=np.quantile(differences,[0.025,0.975]).tolist())
    return result


def sensitivity_tables(predictions, one_day_bank):
    reference = next(iter(predictions.values()))
    groups = reference[KEYS].merge(one_day_bank[KEYS+["pair_contact_bins","scan_coverage_a","scan_coverage_b"]], on=KEYS, validate="one_to_one")
    bins = groups.pair_contact_bins
    groups["contact_frequency_1d_bins"] = np.where(bins<=1,"1",np.where(bins<=5,"2-5",">5"))
    coverage = groups[["scan_coverage_a","scan_coverage_b"]].min(axis=1,skipna=False)
    groups["historical_1d_scan_quality"] = np.where(coverage.isna(),"unknown",np.where(coverage<0.5,"below0.5",np.where(coverage<0.75,"0.5-0.75",">=0.75")))
    groups["prediction_study_day"] = (groups.timestamp//DAY+1).astype(str)
    rows = []
    for days, frame in predictions.items():
        joined = frame.merge(groups[KEYS+["contact_frequency_1d_bins","historical_1d_scan_quality","prediction_study_day"]], on=KEYS, validate="one_to_one")
        for dimension in ("contact_frequency_1d_bins","historical_1d_scan_quality","prediction_study_day"):
            for group, subset in joined.groupby(dimension):
                for name in PROTOCOL["models"]:
                    rows.append({"window_days":days,"model":name,"dimension":dimension,"group":str(group),
                                 **binary_metrics(subset.label_24h,subset[f"p_{name}"],threshold=float(subset[f"threshold_{name}"].iloc[0]))})
    return rows


def candidate_expansion(root, timestamps):
    root = Path(root)
    processed = preprocess_contacts(root/"data/raw/copenhagen/bt_symmetric.csv","Copenhagen",root/"data/processed")
    labels = build_labels(processed,root/"data/processed/labels")
    original = pd.read_parquet(labels.path)
    rows = []
    for t in timestamps:
        counts = {}
        for days in (1,7):
            selected = past_pairs(processed,int(t),days).merge(original.loc[original.timestamp.eq(t)],on=["user_min","user_max"],validate="one_to_one")
            eligible = selected.loc[selected.eligible_for_evaluation & selected.label_24h.notna()]
            counts[days] = {"candidate_rows":len(selected),"eligible_rows":len(eligible),"positive":int(eligible.label_24h.eq(1).sum()),"negative":int(eligible.label_24h.eq(0).sum())}
        rows.append({"timestamp":int(t),"study_day":int(t//DAY+1),"one_day_pool":counts[1],"seven_day_pool":counts[7],
                     "extra_eligible_rows":counts[7]["eligible_rows"]-counts[1]["eligible_rows"],"ap_reported":False})
    return {"analysis":"Separate reach/coverage counts, not a pure historical feature effect; no expanded-pool AP compared.","per_day":rows}


def run_robustness(root):
    root = Path(root)
    primary = json.loads((root/"reports/window_study/T21_RESULTS.json").read_text())
    run_id = primary["run_id"]
    directory = root/"reports/window_study"/run_id
    verify_exported_metrics(directory)
    frozen = json.loads((directory/"PROTOCOL_FROZEN.json").read_text())
    if frozen["protocol"] != PROTOCOL or any(sha256(root/p)!=v for p,v in frozen["code_hashes"].items()):
        raise ValueError("T21 statistical protocol/code changed after test exposure.")
    if (directory/"T22_ROBUSTNESS.json").exists():
        return json.loads((directory/"T22_ROBUSTNESS.json").read_text()),directory
    cohort,banks,manifest,receipt = read_inputs(root)
    planned = forward_folds(cohort,PROTOCOL["walk_forward"])
    immutable_json(directory/"T22_PROTOCOL_FROZEN.json",{"parent_protocol_sha256":sha256(directory/"PROTOCOL_FROZEN.json"),
                    "parent_results_sha256":sha256(directory/"T21_RESULTS.json"),"implementation_sha256":sha256(Path(__file__)),
                    "fold_plan":[{k:v for k,v in f.items() if k!="parts"} for f in planned],"protocol":PROTOCOL})
    parts = {name:cohort.loc[cohort.split.eq(name)].copy() for name in ("train","validation","test")}
    print("T22 fit fixed3d intermediate; preserve all1d/7d primary models",flush=True)
    models,summaries = fit_window(banks[3],parts["train"],parts["validation"],3)
    paths = {name:str(ModelRegistry.save(m,root/"models/.window_study"/run_id/"3d",metadata={"run_id":run_id,"stage":"T22","feature_contract":"bounded_window_v1"}).relative_to(root)) for name,m in models.items()}
    immutable_json(directory/"T22_MODELS_FROZEN.json",{"models":summaries,"model_artifacts":paths,"test_scores_read":False})
    intermediate = evaluate_windows(root,directory,run_id,parts["test"],banks,{3:models},{3:summaries},{3:paths},"T22",source_kind="real_public_dataset")
    verify_exported_metrics(directory,"T22")
    predictions = {int(d):pd.read_parquet(directory/v["filename"]) for d,v in primary["predictions_local_ignored"].items()}
    predictions[3] = pd.read_parquet(directory/intermediate["predictions_local_ignored"]["3"]["filename"])
    assert len({row_hash(p,labels=True) for p in predictions.values()}) == 1
    uncertainty = [paired_uncertainty(predictions[1],predictions[7],n,PROTOCOL["uncertainty"]) for n in PROTOCOL["models"]]
    folds = []
    for fold in planned:
        report = {k:v for k,v in fold.items() if k!="parts"}
        if fold["status"] == "ready":
            print(f"T22 forward fold test starts StudyDay{fold['study_day']}",flush=True)
            fold_models,fold_summaries,fold_paths = {},{},{}
            for days in (1,3,7):
                fitted,summary = fit_window(banks[days],fold["parts"]["train"],fold["parts"]["validation"],days)
                fold_models[days],fold_summaries[days] = fitted,summary
                fold_paths[days] = {n:str(ModelRegistry.save(m,root/"models/.window_study"/run_id/f"fold{fold['study_day']}"/f"{days}d",metadata={"run_id":run_id,"stage":"T22_forward_fold","test_start_study_day":fold["study_day"]}).relative_to(root)) for n,m in fitted.items()}
            stage = f"T22_fold{fold['study_day']}"
            immutable_json(directory/f"{stage}_MODELS_FROZEN.json",{"models":fold_summaries,"model_artifacts":fold_paths,"test_scores_read":False})
            evaluation = evaluate_windows(root,directory,run_id,fold["parts"]["test"],banks,fold_models,fold_summaries,fold_paths,stage,source_kind="real_public_dataset")
            verify_exported_metrics(directory,stage)
            report["test_metrics"] = evaluation["test_metrics"]
            report["prediction_exports"] = evaluation["predictions_local_ignored"]
        folds.append(report)
    result = {"run_id":run_id,"stage":"T22","source_kind":"real_public_dataset","protocol":PROTOCOL,
              "main_metrics":sorted(primary["test_metrics"]+intermediate["test_metrics"],key=lambda r:(r["window_days"],r["model"])),
              "paired_uncertainty":uncertainty,"sensitivity":sensitivity_tables(predictions,banks[1]),"walk_forward_folds":folds,
              "candidate_pool_expansion_counts_only":candidate_expansion(root,sorted(cohort.timestamp.unique())),
              "primary_results_preserved_sha256":sha256(directory/"T21_RESULTS.json"),"test_used_for_selection":False,
              "inference_limit":"Four primary test days and dependent participants/pairs; no significance, CI, long-term or independent external validation claim."}
    immutable_json(directory/"T22_ROBUSTNESS.json",result)
    verify_frozen(root,root/"reports/window_study/T18_BASELINE_MANIFEST.json")
    return result,directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path.cwd())
    args = parser.parse_args()
    result,directory = run_robustness(args.root)
    from src.window_report import write_robustness_report
    write_robustness_report(result,directory,args.root/"reports/window_study")
    print(json.dumps({"run_id":result["run_id"],"main_metrics":result["main_metrics"],"uncertainty":result["paired_uncertainty"]},indent=2),flush=True)


if __name__ == "__main__":
    main()
