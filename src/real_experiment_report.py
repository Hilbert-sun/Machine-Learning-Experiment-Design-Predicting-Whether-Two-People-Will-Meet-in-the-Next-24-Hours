"""Render T17 aggregate diagnostics/results; never re-fit or re-select a model."""

import argparse
import json
from pathlib import Path



def _table(rows, fields):
    heading = "| " + " | ".join(label for _, label in fields) + " |"
    lines = [heading, "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        cells = []
        for name, _ in fields:
            value = row.get(name)
            cells.append("unknown" if value is None else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_reports(root):
    root = Path(root).resolve()
    folder = root / "reports"
    result = json.loads((folder / "T17_SAFE_METADATA.json").read_text())
    datasets = result["datasets"]
    lines = ["# T17 — Real Data Diagnostics", "", "Task date: 2026-10-09 (Asia/Kuala_Lumpur). Counts are computed from genuine local files, not synthetic fixtures.", "",
             "## Local inventory and acquisition", "",
             "Initially, local Copenhagen contained only calls/SMS, READMEs and the notebook; the Bluetooth main file was absent. The earlier 8 KB probe is not a training dataset. After diagnostics began, the user explicitly authorized the official complete file download.", "",
             "Official source: [Copenhagen Figshare article 7267433](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433), DOI 10.6084/m9.figshare.7267433. The API returned bt_symmetric.csv; downloaded bytes and MD5 were checked before parsing. Raw data remain excluded from Git.", "",
             _table(datasets, [("dataset", "Dataset"), ("source_path", "Local project-relative path"), ("bytes", "Bytes"), ("participants_with_records", "Valid observed IDs"), ("participants_with_valid_contacts", "IDs with study contacts"), ("valid_contact_records", "Valid contact records")]), ""]
    receipt_path = folder / "T17_DOWNLOAD_RECEIPT_LOCAL.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        lines += [f"Copenhagen official MD5: `{receipt['md5']}`; verified size: {receipt['bytes']:,} bytes.", ""]
    initial_path = folder / "T17_INITIAL_DIAGNOSTICS_LOCAL.json"
    if initial_path.is_file():
        initial = json.loads(initial_path.read_text())
        lines += ["Local Copenhagen communication files are genuine but are not physical-contact labels:", "",
                  _table(initial["local_copenhagen_communications"], [("path", "Path"), ("rows", "Records"), ("participants", "IDs"), ("communication_pairs", "Communication pairs"), ("timestamp_min", "Min relative seconds"), ("timestamp_max", "Max relative seconds")]), ""]
    for data in datasets:
        if data.get("status") == "missing_local_file":
            lines += [f"## {data['dataset']} — not local", "", f"Missing source: {data['source_path']}. No counts or model scores are invented.", ""]
            continue
        lines += [f"## {data['dataset']}", "", f"- SHA-256: `{data['sha256']}`.",
                  f"- Source timestamp range: {data['source_timestamp_range']}; basis: {data['source_time_basis']}. Relative range: {data['relative_timestamp_range']}; recorded origin: {data['time_origin_seconds']}.",
                  f"- Observation span: {data['span_seconds']:,} seconds ({data['span_days']:.6f} days), touching {data['study_days_touched']} Study Days. No calendar dates are invented.",
                  f"- Raw rows: {data['raw_rows']:,}; valid contact records: {data['valid_contact_records']:,}; nonparticipant/sentinel contact rows excluded: {data['excluded_nonparticipant_rows']:,}; self/duplicate rows: {data['self_rows']}/{data['duplicate_rows']}.",
                  f"- Empty-scan rows: {data['empty_scan_rows']:,}; external-device rows: {data['external_device_rows']:,}. These are retained as observation evidence, not mislabeled study contacts.",
                  f"- Full-period observed pairs: {data['full_period_observed_pairs_descriptive_only']:,} (descriptive only). Actual historical candidates appearing in prediction rows: {data['historical_candidate_pairs_across_prediction_rows']:,}; the future-only pairs are not backfilled into candidates.",
                  f"- Complete scheduled snapshots: {data['complete_scheduled_snapshots']}; nonempty candidate snapshots: {data['snapshots_with_candidates']}; candidate sample rows: {data['candidate_sample_rows']:,}.",
                  f"- Positive labels, including ineligible observed positives: {data['positive_labels_including_ineligible']:,}; negative labels: {data['negative_labels']:,}; unknown labels: {data['unknown_labels']:,}.",
                  f"- After coverage filtering: {data['coverage_eligible_samples']:,} samples, {data['positive_eligible']:,} positive / {data['negative_eligible']:,} negative.", "",
                  _table([{"set": name, **count} for name, count in data["split"].items()], [("set", "Set after purge"), ("samples", "Samples"), ("positive", "Positive"), ("negative", "Negative"), ("snapshot_times", "Prediction times")]), "",
                  f"Exclusion reasons: `{json.dumps(data['exclusion_reasons'], sort_keys=True)}`.", "",
                  "Historical candidate counts at each prediction timestamp:", "",
                  _table(data["candidate_counts_by_snapshot"], [("timestamp", "Relative prediction seconds"), ("pairs", "Past-only candidate pairs")]), ""]
        if "split_blocker" in data:
            lines += [f"Split blocker: {data['split_blocker']}", ""]
        if "coverage_sensitivity_counts_not_model_selection" in data:
            lines += ["Coverage sensitivity below is counts-only. No models/test-score searches were run to select these thresholds; the original0.5 remains fixed:", "",
                      _table(data["coverage_sensitivity_counts_not_model_selection"], [("threshold", "Threshold"), ("samples", "Eligible samples"), ("positive", "Positive"), ("negative", "Negative")]), ""]
        if data["dataset"] == "SocioPatterns":
            counterfactuals = [{"hours": row["interval_hours"], "snapshots": row["complete_snapshots"], **row["purged_time_groups"]} for row in data["timeline_counterfactuals_coverage_ignored_only"]]
            lines += ["Timeline-only counterfactuals, ignoring coverage without creating or training on fabricated negatives:", "",
                      _table(counterfactuals, [("hours", "Snapshot interval hours"), ("snapshots", "Complete times"), ("train", "Purged train times"), ("validation", "Purged validation times"), ("test", "Test times")]), ""]
    lines += ["## Exact diagnosis and minimal resolution", "",
              "1. The existing zero-sample result was dataset/policy specific: SocioPatterns supplies positive contacts without independent scan logs, so this code correctly retains unknown absence rather than inventing negative labels. Lowering a numerical coverage threshold cannot create those logs.",
              "2. Separately, its 4.21-day span yields only three daily complete 24h snapshots. Even ignoring coverage, strict chronological label-window purging removes train and validation. Six-hour/hourly snapshots leave validation empty under the original 60/20/20 allocation; they do not create more independent days.",
              "3. Changing the target to no recorded contact, using contact activity as proof of online coverage, or compressing test/calibration boundaries could change the estimand or manufacture a nominal split. These were not used to force metrics.",
              "4. Minimal scientifically defensible resolution: acquire the intended genuine 28-day Copenhagen source with the user's explicit authorization. Keep daily 08:00,24h horizon, Known Pair candidates, coverage 0.5,1/3/7/14-day features, chronological60/20/20 and strict purging unchanged. The resulting cohort supports all requested models.",
              "5. First-history windows may be shorter than14 days; existing completeness flags/missing values remain. No future candidate enumeration, negative downsampling, fake weekdays or unverified communication features were introduced.",
              "6. Engineering-only change: vectorized chunk aggregation scales to 2.43 million contact rows without changing counts/bins/days/RSSI definitions; small-row-group parity and no-future tests verify equivalence.", "",
              "## Measurement limitations", "",
              "Coverage is recorded reporter-bin availability, including empty/external scans and symmetrized data rows, not independent proof of continuous device online status. With 50% coverage, absence can still reflect missed detection. The target is a recorded valid study-device Bluetooth proximity event under the declared coverage assumption, not verified human conversation.",
              "Four positive-RSSI contact rows exist in the genuine file and were retained under the original no-RSSI-threshold protocol; no post-test outlier deletion was performed. Contact records are measurements, not continuous encounters.",
              "Sources: [SocioPatterns official dataset/CC BY-NC-SA](https://sociopatterns.org/datasets/high-school-contact-and-friendship-networks/) (Mastrandrea, Fournet, Barrat 2015); Copenhagen dataset authors Sapiezynski, Stopczynski, Lassen, Lehmann 2019, Figshare MIT data license. Raw files and individual pair rows are not committed.", ""]
    (folder / "T17_DATA_DIAGNOSTICS.md").write_text("\n".join(lines))

    experiment = ["# T17 — First Genuine Real-Data Experiment", "", f"Status: **{result['status']}**. Dataset: genuine Copenhagen Networks Study Bluetooth release. Synthetic samples used: {result.get('synthetic_samples_used', 0)}.", ""]
    if result["status"] != "completed_real_experiment":
        experiment += ["No model scores are reported.", "", result.get("reason", "Feasibility not established."), ""]
    else:
        test = result["metrics"]["test"]
        calibration = result["calibration"]
        fields = [("model", "Model"), ("pr_auc_average_precision", "PR-AUC(AP)"), ("roc_auc", "ROC-AUC"), ("brier_score", "Brier"),
                  ("log_loss", "Log Loss"), ("precision", "Precision"), ("recall", "Recall"), ("f1", "F1"), ("threshold", "Validation-selected threshold")]
        metrics_rows = [{"model": name, **{key: round(value, 6) if isinstance(value, float) else value for key, value in metric.items()}} for name, metric in test.items()]
        experiment += ["## Protocol frozen before model scores", "", "```json", json.dumps(result["protocol"], indent=2), "```", "",
                       "Feasibility gates are engineering checks, not a statistical power claim. No alternative protocol was chosen by looking at test metrics. Coverage/split policies were not relaxed. Only public genuine data were used.", "",
                       "## Cohort and chronology", "", _table([{"set": name, **count} for name, count in result["split"].items()],
                       [("set", "Set"), ("samples", "Rows"), ("positive", "Positive"), ("negative", "Negative"), ("snapshot_times", "Prediction times"), ("first_timestamp", "First relative time"), ("last_timestamp", "Last relative time")]), "",
                       f"Outer split purged {result['purged_rows']:,} rows. Any t+24h touching the next set is excluded. Test set: {result['split']['test']['samples']:,} samples over {result['split']['test']['snapshot_times']} daily prediction times; prevalence {test['constant']['positive_rate']:.6%}.", "",
                       "Constant/historical-frequency/logistic baselines fit train only and choose F1 thresholds on the full validation period. Only after these succeeded was XGBoost trained with the fixed 200-tree/depth4/learning-rate0.05 configuration; no grid search was run.",
                       f"XGBoost calibration: {calibration['method']}, fitted on {calibration['fit_rows']:,} early-validation rows at {calibration['fit_prediction_times']} prediction time; thresholds selected on {calibration['tuning_rows']:,} later-validation rows at {calibration['tuning_prediction_times']} times, with a 24h label-window separation. Baseline and main validation row counts differ and must not be presented as a same-cohort validation ranking.", "",
                       "## One frozen final-test comparison", "", _table(metrics_rows, fields), "",
                       "PR-AUC uses Average Precision. Every row uses the identical frozen test cohort. Precision/recall/F1 use validation-selected thresholds, not test-optimal thresholds. Constant F1-thresholding predicts all positive; its precision equals prevalence and recall is 1. Accuracy is not the primary criterion.", "",
                       "## Probability calibration", ""]
        if "xgboost_sigmoid" in test:
            before, after = test["xgboost_raw"], test["xgboost_sigmoid"]
            experiment += [_table([{"variant": "raw", **before}, {"variant": "sigmoid", **after}], [("variant", "Variant"), ("brier_score", "Test Brier"), ("log_loss", "Test Log Loss"), ("calibration_error_ece", "10-bin ECE")]), "",
                           "Sigmoid was fitted and selected under the predeclared validation-support rule before test scores were computed. It improves probability scores in this experiment; raw and calibrated AP/ROC-AUC are identical. Both variants remain reported, and no post-test selection or retuning occurred.", ""]
        experiment += ["Reliability-bin predicted means and observed fractions are stored in T17_METRICS.json. ECE uses ten equal-width left-closed bins (with 1 included in the last); reliability points use sklearn's uniform-bin convention.", "",
                       "## Findings and limits", "",
                       "- XGBoost shows predictive ranking signal relative to the constant prevalence baseline, and sigmoid improves Brier/Log Loss. This is a first temporal feasibility experiment, not proof of general or multi-year interpersonal forecasting.",
                       "- Historical frequency has useful ranking/Brier but poor Log Loss due to overly extreme probabilities. Logistic Regression has worse test Brier/Log Loss than the constant prior; its low-probability reliability bucket underestimates observed positives. These negative results are retained without a post-test fix.",
                       "- Rows are dependent within participants/pairs/days. There are only 6 test prediction days and 1 calibration day, so hundreds of thousands of rows must not be treated as independent trials. No significance claim or confidence interval is fabricated.",
                       "- The task is within-population temporal prediction of recorded device proximity for historically known pairs; there is no held-out-person/cold-start claim. Rolling features may use earlier test-period observations available before later t, but the fitted models/thresholds never use test targets.",
                       "- Future-window scan coverage selects an observable evaluation cohort and is not a predictor. Partial detection, the 50% proxy assumption, truncated early histories and unconfirmed weekdays/communications limit interpretation.", "",
                       "## Saved artifacts and reproducibility", "",
                       _table([{"model": name, "path": path} for name, path in result["model_artifacts"].items()], [("model", "Model"), ("path", "Ignored local artifact directory")]), "",
                       f"Model save/load probability equivalence: {result['model_roundtrip']}. Raw datasets, individual samples, model weights and private training manifests stay out of Git. Public aggregates contain only relative file paths, dataset hashes, counts, policy/code hashes and measured metrics.", "",
                       "Reproduce deliberately (it re-fits the fixed protocol and overwrites T17 aggregate outputs):", "", "```bash", ".venv/bin/python -m src.real_experiment", ".venv/bin/python -m src.real_experiment_report", "```", "",
                       "The runner does not download implicitly. T17_SAFE_METADATA.json records exact dataset SHA-256, Python/base commit, working-tree algorithm hashes, protocol, cohort counts and local model versions. Existing requirements-lock.txt records the verified package environment. Future tuning must use new validation work rather than repeatedly optimize this reported test set.", ""]
    (folder / "T17_REAL_EXPERIMENT.md").write_text("\n".join(experiment))
    return folder / "T17_DATA_DIAGNOSTICS.md", folder / "T17_REAL_EXPERIMENT.md"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    for path in render_reports(arguments.root):
        print(path)


if __name__ == "__main__":
    main()
