# T17 — First Genuine Real-Data Experiment

Status: **completed_real_experiment**. Dataset: genuine Copenhagen Networks Study Bluetooth release. Synthetic samples used: 0.

## Protocol frozen before model scores

```json
{
  "seed": 42,
  "snapshot_hour": 8,
  "horizon_hours": 24,
  "min_scan_coverage": 0.5,
  "candidate_mode": "Known Pair; contacts strictly before t",
  "historical_windows_days": [
    1,
    3,
    7,
    14
  ],
  "maximum_feature_history_days": 14,
  "chronological_fractions": [
    0.6,
    0.2,
    0.2
  ],
  "strict_label_window_purge": true,
  "negative_downsampling": false,
  "communications_enabled": false,
  "weekday_origin": null,
  "minimum_train_rows": 200,
  "minimum_class_rows_each_set": 20,
  "minimum_snapshot_times_each_set": 2,
  "baseline_parameters": {
    "logistic_regression": {
      "max_iter": 2000
    }
  },
  "xgboost_parameters": {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.05
  },
  "calibration_rule": "sigmoid on early validation if both classes>=20 and later validation has>=2 snapshot times; otherwise no fitted calibrator",
  "threshold_rule": "validation F1 only; raw XGBoost threshold uses the same later-validation period as calibrated XGBoost",
  "test_policy": "one final frozen-model comparison after all fitting; no hyperparameter search"
}
```

Feasibility gates are engineering checks, not a statistical power claim. No alternative protocol was chosen by looking at test metrics. Coverage/split policies were not relaxed. Only public genuine data were used.

## Cohort and chronology

| Set | Rows | Positive | Negative | Prediction times | First relative time | Last relative time |
| --- | --- | --- | --- | --- | --- | --- |
| train | 269757 | 30619 | 239138 | 15 | 28800 | 1238400 |
| validation | 155368 | 18289 | 137079 | 4 | 1411200 | 1670400 |
| test | 260170 | 26594 | 233576 | 6 | 1843200 | 2275200 |

Outer split purged 84,332 rows. Any t+24h touching the next set is excluded. Test set: 260,170 samples over 6 daily prediction times; prevalence 10.221778%.

Constant/historical-frequency/logistic baselines fit train only and choose F1 thresholds on the full validation period. Only after these succeeded was XGBoost trained with the fixed 200-tree/depth4/learning-rate0.05 configuration; no grid search was run.
XGBoost calibration: sigmoid, fitted on 35,666 early-validation rows at 1 prediction time; thresholds selected on 81,830 later-validation rows at 2 times, with a 24h label-window separation. Baseline and main validation row counts differ and must not be presented as a same-cohort validation ranking.

## One frozen final-test comparison

| Model | PR-AUC(AP) | ROC-AUC | Brier | Log Loss | Precision | Recall | F1 | Validation-selected threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| constant | 0.102218 | 0.5 | 0.091897 | 0.330581 | 0.102218 | 1.0 | 0.185477 | 0.113506 |
| historical_frequency | 0.30904 | 0.703795 | 0.083377 | 0.73076 | 0.320484 | 0.376702 | 0.346326 | 0.230769 |
| logistic_regression | 0.245216 | 0.652128 | 0.095737 | 0.445783 | 0.163578 | 0.373092 | 0.227438 | 0.017183 |
| xgboost_raw | 0.381491 | 0.750717 | 0.088394 | 0.380844 | 0.380099 | 0.417989 | 0.398145 | 0.032902 |
| xgboost_sigmoid | 0.381491 | 0.750717 | 0.077673 | 0.27891 | 0.380099 | 0.417989 | 0.398145 | 0.217845 |

PR-AUC uses Average Precision. Every row uses the identical frozen test cohort. Precision/recall/F1 use validation-selected thresholds, not test-optimal thresholds. Constant F1-thresholding predicts all positive; its precision equals prevalence and recall is 1. Accuracy is not the primary criterion.

## Probability calibration

| Variant | Test Brier | Test Log Loss | 10-bin ECE |
| --- | --- | --- | --- |
| raw | 0.08839424317495514 | 0.3808438391489658 | 0.0792442273061261 |
| sigmoid | 0.07767315693245937 | 0.2789101115588304 | 0.010393397802240061 |

Sigmoid was fitted and selected under the predeclared validation-support rule before test scores were computed. It improves probability scores in this experiment; raw and calibrated AP/ROC-AUC are identical. Both variants remain reported, and no post-test selection or retuning occurred.

Reliability-bin predicted means and observed fractions are stored in T17_METRICS.json. ECE uses ten equal-width left-closed bins (with 1 included in the last); reliability points use sklearn's uniform-bin convention.

## Findings and limits

- XGBoost shows predictive ranking signal relative to the constant prevalence baseline, and sigmoid improves Brier/Log Loss. This is a first temporal feasibility experiment, not proof of general or multi-year interpersonal forecasting.
- Historical frequency has useful ranking/Brier but poor Log Loss due to overly extreme probabilities. Logistic Regression has worse test Brier/Log Loss than the constant prior; its low-probability reliability bucket underestimates observed positives. These negative results are retained without a post-test fix.
- Rows are dependent within participants/pairs/days. There are only 6 test prediction days and 1 calibration day, so hundreds of thousands of rows must not be treated as independent trials. No significance claim or confidence interval is fabricated.
- The task is within-population temporal prediction of recorded device proximity for historically known pairs; there is no held-out-person/cold-start claim. Rolling features may use earlier test-period observations available before later t, but the fitted models/thresholds never use test targets.
- Future-window scan coverage selects an observable evaluation cohort and is not a predictor. Partial detection, the 50% proxy assumption, truncated early histories and unconfirmed weekdays/communications limit interpretation.

## Saved artifacts and reproducibility

| Model | Ignored local artifact directory |
| --- | --- |
| constant | models/T17/193387315b5b/constant-ff9a40f43272 |
| historical_frequency | models/T17/193387315b5b/historical_frequency-bdb8b460786f |
| logistic_regression | models/T17/193387315b5b/logistic_regression-ed32f364e66e |
| xgboost_raw | models/T17/raw_xgboost/xgboost-51f3a5ee59a3 |
| xgboost_sigmoid | models/T17/87c5d0cc8e77/xgboost-f788627b3aa2 |

Model save/load probability equivalence: passed. Raw datasets, individual samples, model weights and private training manifests stay out of Git. Public aggregates contain only relative file paths, dataset hashes, counts, policy/code hashes and measured metrics.

Reproduce deliberately (it re-fits the fixed protocol and overwrites T17 aggregate outputs):

```bash
.venv/bin/python -m src.real_experiment
.venv/bin/python -m src.real_experiment_report
```

The runner does not download implicitly. T17_SAFE_METADATA.json records exact dataset SHA-256, Python/base commit, working-tree algorithm hashes, protocol, cohort counts and local model versions. Existing requirements-lock.txt records the verified package environment. Future tuning must use new validation work rather than repeatedly optimize this reported test set.
