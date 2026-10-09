# T21 —1d vs7d window experiment

Run ID: `102140b8cf3df83f`. Source: `real_public_dataset`. Date:2026-10-10 (Asia/Kuala_Lumpur).

Fixed-protocol same-source Copenhagen temporal comparison. T17 already exposed overlapping test dates; this is not a pristine independent holdout. Prediction target is recorded anonymous-device Bluetooth proximity, not conversation. All windows share1d candidates, keys, labels and dates. Only4 distinct test days; repeated pairs/participants are dependent. Parameters and threshold/calibration rules were frozen before new test scores; no test-driven tuning. Calibration is disabled because3 validation dates cannot support independent calibration plus>=2 threshold-selection dates after24h purge. Recorded-bin coverage>=0.5 is an observation proxy, not proof that no contact was missed.

Train54,677 rows/11 dates; validation14,816/3; test25,569/4. See T19 manifest for exact dates/purge. Test positive prevalence:21.381360%; the constant-score AP equals this prevalence. No negative sampling.

| Window | Model | AP | ROC-AUC | Brier | Log Loss | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|1d|historical_frequency|0.209642|0.487299|0.710701|24.793340|0.213814|1.000000|0.352301|
|1d|logistic_regression|0.510617|0.750177|0.139615|0.444968|0.593994|0.361807|0.449699|
|1d|xgboost|0.588723|0.770656|0.128026|0.415109|0.603148|0.455643|0.519121|
|7d|historical_frequency|0.519329|0.775063|0.139351|0.974339|0.575941|0.453631|0.507521|
|7d|logistic_regression|0.644780|0.824048|0.119159|0.389749|0.712062|0.468630|0.565251|
|7d|xgboost|0.691366|0.841494|0.109107|0.360995|0.680299|0.599415|0.637301|

## Prespecified paired contrast

- historical_frequency: AP_1d=0.209642, AP_7d=0.519329, delta_AP_7d_minus_1d=+0.309687.
- logistic_regression: AP_1d=0.510617, AP_7d=0.644780, delta_AP_7d_minus_1d=+0.134164.
- xgboost: AP_1d=0.588723, AP_7d=0.691366, delta_AP_7d_minus_1d=+0.102644.

Full fixed protocol and source/cohort/feature/code hashes are in the run's PROTOCOL_FROZEN.json; validation metrics, thresholds, runtimes, fitted feature lists and local model paths are in T21_RESULTS.json. Models use the existing registry estimators/persistence with a separate bounded_window_v1 input contract. Hidden local models/.window_study prevents accidental selection in legacy UI. Raw probabilities and reliability curves are reported; no fitted calibrator is claimed.1d historical frequency often predicts1 conditional on the shared previous-day-contact candidate rule; unknown historical coverage falls back to the train prior. Poor results remain reported.

Individual probabilities, labels and stable keys are local ignored Parquet files under `reports/window_study/102140b8cf3df83f/`. `verify_exported_metrics` recomputes every reported binary metric from these exports and verifies checksums. T17 baseline artifact verification and model save/load checks passed. Run `python -m src.window_study` to verify/reuse this completed fixed-protocol run; it does not refit a completed run. No download or UI action is implicit.
