# Encounter Lab — Progress

Date: 2026-10-09 (Asia/Kuala_Lumpur)

## Result

**T17 — DONE: first genuine real-data feasibility experiment.** T01–T16 engineering remains complete. Diagnosed the previous blocker, acquired official Copenhagen Bluetooth only after explicit user approval, preserved scientific filtering/split rules, trained the requested real baselines and XGBoost, checked calibration, saved local artifacts and generated safe aggregate deliverables. No new UI was added. Stop after the requested safe commit.

## Exactly why training was previously blocked

- Existing full SocioPatterns:327 participants,188,508 records,4.207870 observed days,5,818 full-period pairs,4,602 actual historical candidate pairs and3 daily prediction times. It supplies no scan logs, so all10,742 samples are excluded;4,023 recorded positives remain evidence and6,719 absences remain unknown, not fabricated negatives.
- Independently, three daily time points cannot survive the strict24h train/validation/test purge. Even counterfactual6-hour/1-hour grids with coverage ignored produce13/76 time points but zero purged validation times under60/20/20. More overlapping rows do not create more observation days.
- Copenhagen main Bluetooth file was absent; calls/SMS cannot substitute as physical-contact labels. The earlier8KB probe was never used for training.
- Minimal resolution was data acquisition, not relaxed labels or a weakened test. Downloaded genuine `bt_symmetric.csv` from Figshare API article7267433:98,257,835 bytes, official MD5 `98892459f73e774cf79e7977edfeee3e` verified. All raw/model files remain ignored.

## Genuine Copenhagen cohort

-706 valid recorded device IDs;692 appear in valid study contacts;5,474,289 raw rows →2,426,279 valid contact records. Empty/external rows remain scan evidence. Source relative seconds0–2,418,900, spanning27.996528 days/28 Study Days.
-79,530 pairs observed over the full period (descriptive only);77,172 pairs actually appear as past-only candidates across27 prediction snapshots.
-1,196,828 candidate rows:111,299 observed positive labels including ineligible positives,687,700 negative labels,397,829 unknown. Coverage≥0.5 yields769,627 eligible rows:81,927 positive/687,700 negative.
- Strict purged chronological split: train269,757 (30,619 positive/239,138 negative,15 times); validation155,368 (18,289/137,079,4 times); test260,170 (26,594/233,576,6 times). Purged84,332 rows; test prevalence10.221778%.
- Kept daily08:00,24h horizon, Known Pair, coverage0.5,1/3/7/14-day bank/14-day model history, no negative downsampling, no communications or guessed weekdays,60/20/20 and strict inclusive-window purge. Counts-only0.25/0.5/0.75 sensitivity was not used to choose test-favorable settings.

## First frozen final-test results

| Model | PR-AUC(AP) | ROC-AUC | Brier | Log Loss | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Constant Probability |0.102218|0.500000|0.091897|0.330581|0.102218|1.000000|0.185477|
| Historical Contact Frequency |0.309040|0.703795|0.083377|0.730760|0.320484|0.376702|0.346326|
| Logistic Regression |0.245216|0.652128|0.095737|0.445783|0.163578|0.373092|0.227438|
| XGBoost raw |0.381491|0.750717|0.088394|0.380844|0.380099|0.417989|0.398145|
| XGBoost sigmoid |0.381491|0.750717|0.077673|0.278910|0.380099|0.417989|0.398145|

Baselines fit/threshold-select first; only after success was fixed200-tree/depth4/learning-rate0.05 XGBoost fitted. Sigmoid used35,666 early-validation rows at1 prediction time; thresholds used81,830 later-validation rows at2 times, separated by the same strict24h gap. No grid or post-test model tuning was performed. Baseline validation uses the full validation set; main validation uses the later period, so only the identical test cohort is presented as a same-cohort ranking.

XGBoost ECE improved0.079244→0.010393; raw/calibrated AP and ROC-AUC are identical. Logistic probability scores are worse than the constant prior and are retained, not hidden or repaired after seeing the test. No significance/independent-trial claim is made for six dependent test days.

## Files and deliverables

- Added `src/real_experiment.py`: deterministic diagnostics, predefined sample-support gates, genuine baseline-then-main execution, frozen holdout metrics, safe relative-path aggregate metadata, local model save/load equivalence. No implicit download/UI.
- Added `src/real_experiment_report.py`: renders the requested reports from measured JSON without fitting or selection.
- Optimized only chunk aggregation in `src/feature_engineering.py` to avoid per-pair DataFrame construction at2.43million records, retaining exact record/bin/day/RSSI definitions and time filters. Added optional progress callbacks. Existing semantics/version remain unchanged and parity/no-future tests pass.
- Added `tests/test_real_experiment.py`; isolated existing navigation/UI fixture paths from the now-real user data/model directories. Previous empty-workspace tests must not assume an empty production model registry.
- Public safe deliverables: `reports/T17_DATA_DIAGNOSTICS.md`, `reports/T17_REAL_EXPERIMENT.md`, `reports/T17_METRICS.csv`, `reports/T17_METRICS.json`, `reports/T17_SAFE_METADATA.json`. .gitignore whitelists only these five reports; all other reports remain private/ignored.
- Updated README/DELIVERY/AGENTS/TASKS/PROGRESS to distinguish historical synthetic engineering verification from this first real experiment.
- Local artifacts: three baseline pipelines plus raw/calibrated XGBoost under ignored `models/T17/`; detailed paths in the experiment report. Private training manifests remain ignored. No individual pair rows or dataset contents are committed.

## Verification

- Vectorized-history cross-row-group parity and existing feature/label/delivery/temporal checks:33 passed.
- Relevant T17/feature/label/temporal/model/calibration/navigation checks:68 passed in3.35s.
- Final full `.venv/bin/python -m pytest -q`: **171 passed in8.61s**, with genuine data/models present and test fixtures isolated.
- Every saved model reload matched its actual pre-save test-probe probabilities. Model-generating file hashes still match the pre-test freeze recorded in safe metadata; no statistical code changed after heldout scores.
- Official download size/MD5 verified; public deliverable review found no home paths, credentials or individual samples. Raw data/models/private receipts/manifests remain excluded.
- No relevant test failed in T17. Sandbox PyArrow CPU-probe warnings were nonfatal. A documentation patch initially had out-of-order contexts; corrected without model/code/score changes.

## Interpretation and remaining limitations

The target is a future recorded study-device Bluetooth proximity event under a recorded-bin coverage assumption, not ground truth of human conversation/continuous presence. Symmetrized rows and50% coverage cannot prove full online status or eliminate missed detection. Four positive-RSSI measurements were retained under the prespecified no-threshold rule. Rows repeat participants/pairs/days; calibration covers one day and test six days. Weekdays/communications remain unknown, cold-start/new-person generalization was not tested, and long-term claims are unsupported.

Research feasibility is established for this declared within-population recorded-event task. Future improvements require a new validation design, not optimizing this already-reported test set. No further experiment starts automatically.

## Repository and next task

Commit only reviewed code, docs, tests and the five aggregate T17 reports. Raw datasets, model weights, labels/features, individual samples, private manifests and credentials are excluded. This T17 request requires a commit; no push or new UI is necessary. The final commit identifier is reported in the execution reply/Git history.

No next task is started. Stop after T17.
