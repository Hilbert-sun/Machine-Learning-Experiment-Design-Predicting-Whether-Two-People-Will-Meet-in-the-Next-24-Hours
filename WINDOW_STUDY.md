# T22 —1/3/7d comparison and temporal robustness

Run: `102140b8cf3df83f`. Genuine Copenhagen. Date:2026-10-10 (Asia/Kuala_Lumpur).

All windows use the same full7d-span cohort, strict1d candidate pool, labels, coverage and purged splits. Test:25,569 rows on4 prediction days (Study Days24–27), prevalence21.38136%. Fixed seed42 and identical model hyperparameters/budget; only historical inputs differ. Raw models;3 validation dates cannot support strict independent calibration plus>=2 threshold dates. T17 and primary T21 outputs were preserved.

| Window | Model | AP | ROC-AUC | Brier | Log Loss | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|1d|historical_frequency|0.209642|0.487299|0.710701|24.793340|0.213814|1.000000|0.352301|
|1d|logistic_regression|0.510617|0.750177|0.139615|0.444968|0.593994|0.361807|0.449699|
|1d|xgboost|0.588723|0.770656|0.128026|0.415109|0.603148|0.455643|0.519121|
|3d|historical_frequency|0.332908|0.641837|0.229018|3.000395|0.476156|0.241083|0.320097|
|3d|logistic_regression|0.571497|0.780480|0.131895|0.424873|0.637807|0.404244|0.494850|
|3d|xgboost|0.627494|0.799719|0.120801|0.394671|0.643180|0.494238|0.558957|
|7d|historical_frequency|0.519329|0.775063|0.139351|0.974339|0.575941|0.453631|0.507521|
|7d|logistic_regression|0.644780|0.824048|0.119159|0.389749|0.712062|0.468630|0.565251|
|7d|xgboost|0.691366|0.841494|0.109107|0.360995|0.680299|0.599415|0.637301|

XGBoost7d-minus1d pooled AP difference:+0.102644; positive on4/4 primary test dates. This supports an effect in these observed periods; it does not establish stable long-term generalization.3d is an intermediate fixed control, not a window selected from test performance.

## Paired day-block sensitivity

| Model | Pooled delta AP | Leave-one-day-out descriptive range | CI status |
| --- | --- | --- | --- |
|historical_frequency|+0.309687|[+0.293131, +0.333018]|insufficient_days_for_ci|
|logistic_regression|+0.134164|[+0.115073, +0.149480]|insufficient_days_for_ci|
|xgboost|+0.102644|[+0.093727, +0.112168]|insufficient_days_for_ci|

Only4 test-day blocks, below the prespecified8-day minimum for bootstrap CIs. Ranges above delete an entire paired day, keeping all remaining paired rows; they are **not confidence intervals**. No row-wise bootstrap, p-value or significance claim. Participants/pairs recur and adjacent days may be correlated. Per-day differences and leave-one-day-out values are exported in JSON.

## Prespecified expanding chronological folds

All folds were planned before T21 scores, and evaluate2 future days before the primary holdout. Each has3 validation dates and strict24h boundary purge; raw models and thresholds fit separately using only each fold's earlier train/validation. Folds are descriptive robustness evidence; they do not choose features, windows or parameters, and their expanding train sets are dependent.

| Test starts Study Day | AP1d | AP3d | AP7d | Delta7d−1d |
| --- | --- | --- | --- | --- |
|16|0.657627|0.664410|0.742147|+0.084520|
|19|0.515926|0.568654|0.602845|+0.086919|
|22|0.817755|0.835532|0.862609|+0.044854|

- Fold starts Day16: ready; train 9,008 rows /3 dates [8, 9, 10]; validation 24,386 rows /3 dates [12, 13, 14]; test 7,326 rows /2 dates [16, 17].
- Fold starts Day19: ready; train 31,036 rows /6 dates [8, 9, 10, 11, 12, 13]; validation 7,928 rows /3 dates [15, 16, 17]; test 13,325 rows /2 dates [19, 20].
- Fold starts Day22: ready; train 41,345 rows /9 dates [8, 9, 10, 11, 12, 13, 14, 15, 16]; validation 20,005 rows /3 dates [18, 19, 20]; test 1,608 rows /2 dates [22, 23].

## Subgroup and candidate reach diagnostics

Sensitivity CSV exports every model/window by common1d contact-bin frequency (1,2–5,>5), historical1d minimum reporter coverage (unknown,<0.5,0.5–0.75,>=0.75), and prediction Study Day. Groups are fixed from common1d history; future target quality never enters model inputs. Empty groups are omitted, single-class ROC-AUC is null. Differences in group prevalence must accompany AP comparisons.

Across all20 eligible snapshot dates, separate7d candidates provide474,339 coverage-eligible rows versus100,485 common1d rows (extra373,854). Per-day pool/class counts are in JSON. No expanded-pool model or AP is reported: changing candidate populations cannot be interpreted as a pure historical-feature effect. This reach count includes pre-split eligible dates, including boundary-purged dates.

## Reproducibility and limitations

`python -m src.window_study` reuses/verifies T21; `python -m src.window_robustness` reuses/verifies T22. The original T18 freeze verifies T17 artifacts. Local ignored Parquet probabilities/labels and model artifacts allow metric recomputation; aggregate CSV/JSON/Markdown/standalone HTML contain no individual IDs. No raw datasets/models/predictions are committed or pushed.

T17 already exposed overlapping days: this is a same-source fixed-protocol temporal comparison, not pristine external validation. Full7d span is not continuous scanning; recorded symmetrized bins and50% coverage are observation proxies. The target is recorded device proximity, not conversation. Only4 primary test days and6 forward-fold test dates; repeated users/pairs, short calibration support and unknown weekdays/communications limit inference.1d frequency degeneracy and its poor probability scores remain reported without post-test repair. No T23 UI or new source download was started.


## T23–T27 research edition interface

Open History Window Study in the top navigation. The default Copenhagen/coverage0.5/seed42/no-calibration configuration displays the frozen window study after Run Study verification. Changed coverage/seed/model/window settings produce separate validation-only cached jobs. New external sources are selectable for diagnosis but cannot train until observation evidence and date gates are verified. Candidate-pool expansion remains a separate reach-only analysis. No changed setting silently overwrites a frozen experiment or treats a new report as pristine test evidence.

Case Explorer selects only common historical pairs and times strictly after saved validation information deadlines. Its future mode reads no target columns; enable historical backtest explicitly for available actual outcomes. Unknown targets stay Unknown. Registry feature inputs are bounded_window_v1, with matching1/3/7d histories; legacy14d E2 banks are not substituted.

T27 verified10-page AppTest routing, actual frozen study charts/downloads/model cases, a genuine changed-seed validation job with recomputed metrics, full frozen36-model prediction equivalence, source/processed hashes and actual CSV/HTML export structure. Exact command results are in PROGRESS.md and reports/T27_VERIFICATION.json. Data/model/private predictions stay local and ignored.
