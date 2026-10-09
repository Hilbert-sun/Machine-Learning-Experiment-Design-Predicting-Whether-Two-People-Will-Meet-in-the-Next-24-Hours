# Encounter Lab — Research Report

Date:2026-10-10 (Asia/Kuala_Lumpur). T17–T27 research/engineering work is complete within verified source limits. The target remains recorded anonymous-device proximity in(t,t+24h], not romance, friendship, conversation or long-term relationships.

The genuine Copenhagen fixed-protocol common-cohort study found higher AP with7d than1d history in the measured periods;3d was intermediate. This is preliminary temporal evidence, not a statistical-significance, long-term, new-person or independent-external-validation claim. T17 had already exposed overlapping dates before the new study was declared.

## Actual main model evidence

| Experiment/cohort | Window | AP | ROC-AUC | Brier | Log Loss | Positive prevalence |
| --- | --- | --- | --- | --- | --- | --- |
|T17 · xgboost_sigmoid|14d|0.381491|0.750717|0.077673|0.278910|10.221778%|
|T21-T22 · xgboost|1d|0.588723|0.770656|0.128026|0.415109|21.381360%|
|T21-T22 · xgboost|3d|0.627494|0.799719|0.120801|0.394671|21.381360%|
|T21-T22 · xgboost|7d|0.691366|0.841494|0.109107|0.360995|21.381360%|

T17 uses the older all-past candidate pool and14d feature bank, with769,627 eligible rows; train/validation/test269,757/155,368/260,170. Its84,332-row split loss is exactly Day16/21 purge. T18 froze its source/report/model/code evidence at f116951. New raw AP must not be compared to T17 as an identical-cohort improvement: candidate populations, history completeness and prevalence differ.

T21–T22 run102140b8cf3df83f shares strict[t-1d,t) candidates, full7d source span, exact dataset/time/pair keys and labels, original0.5 recorded-bin coverage, and strict24h chronological purge.100,485 eligible rows become54,677 train/14,816 validation/25,569 test over11/3/4 dates;5,423 boundary rows purged. No downsampling, random-row split or future features. Same seed42 and XGBoost200 trees/depth4/rate0.05; Logistic Regression and Historical Frequency also fitted at each window.3 validation dates cannot support independent calibration plus>=2 threshold dates after purge; raw probabilities/reliability are disclosed. Thresholds use validation only. Poor1d frequency probabilities remain reported.

XGBoost7d−1d AP difference:+0.102644; positive on4/4 primary test dates. Leave-one-day-out descriptive range[+0.093727,+0.112168] is not a confidence interval; only4 day blocks, below the prespecified8-day bootstrap gate. Three predeclared expanding folds produce positive differences+0.084520,+0.086919,+0.044854, but share users/pairs/training history and are not independent trials. Subgroup/date sensitivity and separate7d-candidate reach counts are available. Expanded candidate-population AP is not claimed as a pure window effect.

## Research interface and reproduction

History Window Study includes setup, cohort audit, metric/PR/reliability/date/paired-difference charts, CSV/JSON/HTML downloads and saved-model case comparisons. Default settings reuse frozen results; changed settings execute cached validation-only jobs without reopening the reported test for selection. Future case predictions read historical feature banks only; actual outcomes require explicit backtest and a matching exported target. Unsupported calibration, missing files/coverage or too few dates give specific blockers.

Dataset Catalog independently reports each source's access/license/schema/hashes/IDs/time/missingness and1/3/7d date capacity. New adapters preserve old loaders/downloaders. Dataset status outcomes appear in [DATASET_CATALOG.md](DATASET_CATALOG.md); they are not fabricated training successes. Only Copenhagen currently supports actual primary prediction metrics.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.window_verify
.venv/bin/python -m src.research_delivery
.venv/bin/streamlit run app.py
```

The research delivery command only reads/diagnoses local evidence and generates aggregate reports; it neither fits models nor downloads sources. The original local ignored artifacts are required for full frozen verification; a fresh clone must prepare lawful matching source/artifacts rather than substitute mismatched files. See WINDOW_STUDY.md for the model/cohort input contract and prior reports for exact timestamps/hashes.

## Limits and delivery boundary

Recorded symmetrized bins/50% coverage are availability proxies, not proof of continuous device presence or a guaranteed negative. Repeated participants/pairs/days and short observation/test span limit inference. Unverified calendar origin, communications, and static endpoint relationships are excluded. Missing online logs, processed time ticks and interpolated data constrain new sources. Source-specific populations/sensors are never merged for a larger apparent sample. No private/raw datasets, individual predictions, model weights, credentials or large HTML bundles enter Git; no unauthorized remote push.

Machine-readable actual metrics:reports/RESEARCH_METRICS.csv and.json. Source manifests:reports/DATASET_CATALOG.json. Standalone interactive exports stay local under the frozen run; the UI creates downloads from actual result data. Verification details and final test counts are recorded in PROGRESS.md and reports/T27_VERIFICATION.json. No more task starts automatically after T27.
