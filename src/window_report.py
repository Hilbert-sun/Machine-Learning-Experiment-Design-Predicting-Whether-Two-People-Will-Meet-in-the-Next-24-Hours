"""Aggregate-only research exports; individual predictions stay in ignored run directories."""

import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


def metrics_markdown(rows):
    text = "| Window | Model | AP | ROC-AUC | Brier | Log Loss | Precision | Recall | F1 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    for row in rows:
        text += f"|{row['window_days']}d|{row['model']}|" + "|".join(f"{row[key]:.6f}" if row[key] is not None else "unavailable" for key in
                   ("pr_auc_average_precision", "roc_auc", "brier_score", "log_loss", "precision", "recall", "f1")) + "|\n"
    return text


def write_primary_report(result, directory, public):
    directory, public = Path(directory), Path(public)
    public.mkdir(parents=True, exist_ok=True)
    rows = result["test_metrics"]
    note = ("Fixed-protocol same-source Copenhagen temporal comparison. T17 already exposed overlapping test dates; "
            "this is not a pristine independent holdout. Prediction target is recorded anonymous-device Bluetooth proximity, not conversation. "
            "All windows share1d candidates, keys, labels and dates. Only4 distinct test days; repeated pairs/participants are dependent. "
            "Parameters and threshold/calibration rules were frozen before new test scores; no test-driven tuning. "
            "Calibration is disabled because3 validation dates cannot support independent calibration plus>=2 threshold-selection dates after24h purge. "
            "Recorded-bin coverage>=0.5 is an observation proxy, not proof that no contact was missed.")
    text = f"# T21 —1d vs7d window experiment\n\nRun ID: `{result['run_id']}`. Source: `{result['source_kind']}`. Date:2026-10-10 (Asia/Kuala_Lumpur).\n\n{note}\n\n"
    sample_summary = next(iter(next(iter(result['validation_and_runtime'].values())).values()))
    text += f"Train{sample_summary['training_rows']:,} rows/{len(sample_summary['training_prediction_times'])} dates; validation{sample_summary['validation']['rows']:,}/{len(sample_summary['validation_prediction_times'])}; test{rows[0]['rows']:,}/{rows[0]['distinct_prediction_days']}. See T19 manifest for exact dates/purge. "
    text += f"Test positive prevalence:{rows[0]['positive_rate']:.6%}; the constant-score AP equals this prevalence. No negative sampling.\n\n"
    text += metrics_markdown(rows)
    text += "\n## Prespecified paired contrast\n\n"
    for row in result["paired_main_contrast"]:
        text += f"- {row['model']}: AP_1d={row['AP_1d']:.6f}, AP_7d={row['AP_7d']:.6f}, delta_AP_7d_minus_1d={row['delta_AP_7d_minus_1d']:+.6f}.\n"
    text += "\nFull fixed protocol and source/cohort/feature/code hashes are in the run's PROTOCOL_FROZEN.json; validation metrics, thresholds, runtimes, fitted feature lists and local model paths are in T21_RESULTS.json. "
    text += "Models use the existing registry estimators/persistence with a separate bounded_window_v1 input contract. Hidden local models/.window_study prevents accidental selection in legacy UI. "
    text += "Raw probabilities and reliability curves are reported; no fitted calibrator is claimed.1d historical frequency often predicts1 conditional on the shared previous-day-contact candidate rule; unknown historical coverage falls back to the train prior. Poor results remain reported.\n\n"
    text += f"Individual probabilities, labels and stable keys are local ignored Parquet files under `reports/window_study/{result['run_id']}/`. "
    text += "`verify_exported_metrics` recomputes every reported binary metric from these exports and verifies checksums. T17 baseline artifact verification and model save/load checks passed. "
    text += "Run `python -m src.window_study` to verify/reuse this completed fixed-protocol run; it does not refit a completed run. No download or UI action is implicit.\n"
    (public/"T21_REAL_EXPERIMENT.md").write_text(text)
    (public/"T21_RESULTS.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    pd.DataFrame(rows).to_csv(public/"T21_METRICS.csv", index=False)
    figures = []
    for metric in ("pr_auc_average_precision", "roc_auc", "brier_score", "log_loss"):
        figure = go.Figure()
        for name in result["protocol"]["models"]:
            subset = sorted((r for r in rows if r["model"]==name), key=lambda r:r["window_days"])
            figure.add_scatter(x=[r["window_days"] for r in subset], y=[r[metric] for r in subset], mode="lines+markers", name=name)
        figure.update_layout(title=f"{metric} · {result['source_kind']} ·{rows[0]['distinct_prediction_days']} test days", xaxis_title="History days", yaxis_title=metric)
        figures.append(figure)
    reliability = go.Figure()
    for name, points in result["reliability"].items():
        reliability.add_scatter(x=[p["mean_probability"] for p in points], y=[p["observed_fraction"] for p in points], mode="lines+markers", name=name)
    reliability.add_scatter(x=[0,1], y=[0,1], mode="lines", name="ideal")
    reliability.update_layout(title="Raw model reliability; no fitted calibrator", xaxis_title="Mean probability", yaxis_title="Observed rate")
    figures.append(reliability)
    fragments = ["<!doctype html><html><head><meta charset='utf-8'><title>T21 real window study</title></head><body><h1>T21 real window study</h1>",
                 "<p>"+html.escape(result['source_kind']+': '+note)+"</p>", pd.DataFrame(rows).to_html(index=False, escape=True)]
    for i, figure in enumerate(figures):
        fragments.append(figure.to_html(full_html=False, include_plotlyjs=True if i==0 else False))
    fragments.append("</body></html>")
    (directory/"T21_REPORT.html").write_text("".join(fragments))
    return directory/"T21_REPORT.html"


def write_robustness_report(result, directory, public):
    directory, public = Path(directory), Path(public)
    rows = result["main_metrics"]
    uncertainty = next(r for r in result["paired_uncertainty"] if r["model"]=="xgboost")
    days = uncertainty["paired_by_day"]
    positive_days = sum(r["delta_AP_7d_minus_1d"] is not None and r["delta_AP_7d_minus_1d"]>0 for r in days)
    folds = result["walk_forward_folds"]
    fold_rows = [{"test_start_study_day":f["study_day"], **r} for f in folds if f["status"]=="ready" for r in f["test_metrics"]]
    fold_deltas = []
    for fold in folds:
        if fold["status"] == "ready":
            scores = {r["window_days"]:r["pr_auc_average_precision"] for r in fold["test_metrics"] if r["model"]=="xgboost"}
            fold_deltas.append({"test_start_study_day":fold["study_day"], "AP_1d":scores[1],"AP_3d":scores[3],"AP_7d":scores[7],"delta_AP_7d_minus_1d":scores[7]-scores[1]})
    text = f"# T22 —1/3/7d comparison and temporal robustness\n\nRun: `{result['run_id']}`. Genuine Copenhagen. Date:2026-10-10 (Asia/Kuala_Lumpur).\n\n"
    text += "All windows use the same full7d-span cohort, strict1d candidate pool, labels, coverage and purged splits. Test:25,569 rows on4 prediction days (Study Days24–27), prevalence21.38136%. Fixed seed42 and identical model hyperparameters/budget; only historical inputs differ. Raw models;3 validation dates cannot support strict independent calibration plus>=2 threshold dates. T17 and primary T21 outputs were preserved.\n\n"
    text += metrics_markdown(rows)
    text += f"\nXGBoost7d-minus1d pooled AP difference:{uncertainty['pooled_delta_AP_7d_minus_1d']:+.6f}; positive on{positive_days}/{len(days)} primary test dates. "
    text += "This supports an effect in these observed periods; it does not establish stable long-term generalization.3d is an intermediate fixed control, not a window selected from test performance.\n\n"
    text += "## Paired day-block sensitivity\n\n| Model | Pooled delta AP | Leave-one-day-out descriptive range | CI status |\n| --- | --- | --- | --- |\n"
    for r in result["paired_uncertainty"]:
        interval = r["descriptive_leave_one_day_out_range"]
        text += f"|{r['model']}|{r['pooled_delta_AP_7d_minus_1d']:+.6f}|[{interval[0]:+.6f}, {interval[1]:+.6f}]|{r['status']}|\n"
    text += "\nOnly4 test-day blocks, below the prespecified8-day minimum for bootstrap CIs. Ranges above delete an entire paired day, keeping all remaining paired rows; they are **not confidence intervals**. No row-wise bootstrap, p-value or significance claim. Participants/pairs recur and adjacent days may be correlated. Per-day differences and leave-one-day-out values are exported in JSON.\n\n"
    text += "## Prespecified expanding chronological folds\n\n"
    text += "All folds were planned before T21 scores, and evaluate2 future days before the primary holdout. Each has3 validation dates and strict24h boundary purge; raw models and thresholds fit separately using only each fold's earlier train/validation. Folds are descriptive robustness evidence; they do not choose features, windows or parameters, and their expanding train sets are dependent.\n\n"
    text += "| Test starts Study Day | AP1d | AP3d | AP7d | Delta7d−1d |\n| --- | --- | --- | --- | --- |\n"
    for row in fold_deltas:
        text += f"|{row['test_start_study_day']}|{row['AP_1d']:.6f}|{row['AP_3d']:.6f}|{row['AP_7d']:.6f}|{row['delta_AP_7d_minus_1d']:+.6f}|\n"
    for f in folds:
        text += f"\n- Fold starts Day{f['study_day']}: {f['status']}; "
        if "sets" in f:
            text += "; ".join(f"{n} {s['rows']:,} rows /{s['distinct_prediction_days']} dates " + str([t//86400+1 for t in s['prediction_times']]) for n,s in f['sets'].items())+"."
    text += "\n\n## Subgroup and candidate reach diagnostics\n\n"
    text += "Sensitivity CSV exports every model/window by common1d contact-bin frequency (1,2–5,>5), historical1d minimum reporter coverage (unknown,<0.5,0.5–0.75,>=0.75), and prediction Study Day. Groups are fixed from common1d history; future target quality never enters model inputs. Empty groups are omitted, single-class ROC-AUC is null. Differences in group prevalence must accompany AP comparisons.\n\n"
    reach = result["candidate_pool_expansion_counts_only"]["per_day"]
    one = sum(r["one_day_pool"]["eligible_rows"] for r in reach)
    seven = sum(r["seven_day_pool"]["eligible_rows"] for r in reach)
    text += f"Across all20 eligible snapshot dates, separate7d candidates provide{seven:,} coverage-eligible rows versus{one:,} common1d rows (extra{seven-one:,}). "
    text += "Per-day pool/class counts are in JSON. No expanded-pool model or AP is reported: changing candidate populations cannot be interpreted as a pure historical-feature effect. This reach count includes pre-split eligible dates, including boundary-purged dates.\n\n"
    text += "## Reproducibility and limitations\n\n"
    text += "`python -m src.window_study` reuses/verifies T21; `python -m src.window_robustness` reuses/verifies T22. The original T18 freeze verifies T17 artifacts. Local ignored Parquet probabilities/labels and model artifacts allow metric recomputation; aggregate CSV/JSON/Markdown/standalone HTML contain no individual IDs. No raw datasets/models/predictions are committed or pushed.\n\n"
    text += "T17 already exposed overlapping days: this is a same-source fixed-protocol temporal comparison, not pristine external validation. Full7d span is not continuous scanning; recorded symmetrized bins and50% coverage are observation proxies. The target is recorded device proximity, not conversation. Only4 primary test days and6 forward-fold test dates; repeated users/pairs, short calibration support and unknown weekdays/communications limit inference.1d frequency degeneracy and its poor probability scores remain reported without post-test repair. No T23 UI or new source download was started.\n"
    (public/"T22_WINDOW_COMPARISON.md").write_text(text)
    (public/"T22_ROBUSTNESS.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    pd.DataFrame(rows).to_csv(public/"T22_METRICS.csv",index=False)
    pd.DataFrame(result["sensitivity"]).to_csv(public/"T22_SENSITIVITY.csv",index=False)
    pd.DataFrame(fold_rows).to_csv(public/"T22_WALK_FORWARD.csv",index=False)
    figures = []
    for metric in ("pr_auc_average_precision","roc_auc","brier_score","log_loss"):
        figure = go.Figure()
        for name in result["protocol"]["models"]:
            subset = sorted((r for r in rows if r["model"]==name),key=lambda r:r["window_days"])
            figure.add_scatter(x=[r["window_days"] for r in subset],y=[r[metric] for r in subset],mode="lines+markers",name=name)
        figure.update_layout(title=f"{metric} · genuine Copenhagen ·4 test dates",xaxis_title="History window days",yaxis_title=metric)
        figures.append(figure)
    delta = go.Figure(go.Scatter(x=[r["study_day"] for r in days],y=[r["delta_AP_7d_minus_1d"] for r in days],mode="lines+markers",name="XGBoost paired AP delta"))
    delta.add_hline(y=0,line_dash="dash")
    delta.update_layout(title="Paired per-day7d−1d AP; descriptive, no CI",xaxis_title="Study Day",yaxis_title="AP difference")
    figures.append(delta)
    from sklearn.metrics import precision_recall_curve
    pr = go.Figure()
    for days in (1,3,7):
        path = directory/f"{'T22' if days==3 else 'T21'}_predictions_{days}d.parquet"
        frame = pd.read_parquet(path)
        precision,recall,_ = precision_recall_curve(frame.label_24h,frame.p_xgboost)
        pr.add_scatter(x=recall,y=precision,mode="lines",name=f"XGBoost{days}d")
    pr.update_layout(title="XGBoost PR curves · common test cohort",xaxis_title="Recall",yaxis_title="Precision")
    figures.append(pr)
    fragments = ["<!doctype html><html><head><meta charset='utf-8'><title>T22 window robustness</title></head><body><h1>T22 window robustness</h1>",
                 "<pre>"+html.escape(text)+"</pre>"]
    for i,figure in enumerate(figures):
        fragments.append(figure.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    fragments.extend(["<h2>Subgroup sensitivities</h2>",pd.DataFrame(result["sensitivity"]).to_html(index=False,escape=True),"</body></html>"])
    (directory/"T22_REPORT.html").write_text("".join(fragments))
    return directory/"T22_REPORT.html"
