# Encounter Lab — Progress

Date:2026-10-10 (Asia/Kuala_Lumpur)

**T30 — DONE**, research-v2.2, after published e1fe901. Only as-of prediction quality/selection-bias audit was authorized. T31–T34 remain TODO. Preserve old experiments/models/statistical modules; no real refit, hyperparameter/threshold/calibration tuning, source acquisition or main merge. Safe current-branch publication after verification, then stop/wait next.

## Protocol and implementation

Added src/asof_audit.py and output-only src/asof_audit_report.py. Protocol fixed original T22 frequency/Logistic Regression/XGBoost,1/3/7d windows, already-published Study Days24–27 at08:00, verified shared0.5 label policy and original classification thresholds before new outcomes/scores. Run7521ebdeb40f0b55. T28 bounded historical inputs/time/namespace/window contracts retained; batched probabilities numerically match single T28 inference. No create/fit/search/select-threshold call in audit execution.

All1d-history candidates retained. Common T28-valid past-input mask gives shared1/3/7d prediction keys. Predictions are saved andSHA-frozen before future outcome queries; oldT22 labels/keys/probabilities are consulted only afterward for reconciliation/distribution analysis. Positive evidence is known; absent events need adequate future scan coverage and complete horizon, otherwiseUnknown. Strict coverage population is reported separately. Per-sample probability/label/error files local ignored, public reports aggregate only.

## Measured populations

All38,005 candidates:7,718 recorded positives,20,102 sufficiently observed negatives,10,185 Unknown (26.7991%).37,913 are predictable using common valid pre-t inputs.92 rejected for historical scan evidence:18 known positives and74 Unknown. Metrics therefore use27,802 common known/predicted rows:7,700 positives/20,102 negatives, prevalence27.69585%,4 distinct dates.

Daily candidate/Unknown counts:Day24 10,995/2,913;Day25 8,127/2,271;Day26 9,342/2,751;Day27 9,541/2,250. OldT22 strict-covered cohort25,569 rows (5,467positive/20,102negative,21.38136% prevalence) exactly matches strictfuture coverage; old per-row probabilities/labels and scores reproduce unchanged.

Added12,436 candidates:2,251 known positives,0 known negatives,10,185Unknown (81.8993%). Old cohort past minimum scan coverage mean0.7561 vs added0.4434; past contact bins mean11.5834 vs12.5515. Added observable labels are not random/representative:added known-only AP1 is degenerate and ROC-AUC unavailable, not perfect prediction.

## Conditional model results (no all-population claim)

| XGBoost window | Common known/predicted N | AP | ROC-AUC | Brier | Log Loss | Precision | Recall |
| --- | --- | --- | --- | --- | --- | --- | --- |
|1d|27,802|0.669281|0.785495|0.150793|0.472404|0.692380|0.479091|
|3d|27,802|0.701926|0.812506|0.142075|0.449366|0.725055|0.513377|
|7d|27,802|0.758930|0.854281|0.128114|0.411076|0.754738|0.615455|

7d−1d AP difference0.089649, leave-one-day sensitivity[0.079589,0.102678];4 days below prespecified8-day interval gate, confidence_interval=null/insufficient_days_for_ci. No significance claim. Compared with old cohort,7d AP0.691366→0.758930 but Brier0.109107→0.128114 and Log Loss0.360995→0.411076, with changed prevalence/observability. No causal or unbiased all-candidate quality improvement is claimed.

Frequency/logistic results,36 scope-specific metric rows, daily/filter funnels, historical1d frequency/scan/date groups, probability reliability bin counts and distributions, confusion/high-confidence error statistics are published. Original validation classification thresholds are unchanged. Conditional reliability is not calibration of Unknown candidates.

## Deliverables and reproducibility

ASOF_AUDIT.md is the quality/bias report; README indexes it. Seven safe files under reports/asof_audit:T30_PROTOCOL.json,T30_RESULTS.json,T30_METRICS.csv,T30_DAILY.csv,T30_GROUPS.csv,T30_ERRORS.csv,T30_SELECTION_BIAS.csv. Only these exact files are newly whitelisted.

Private data/processed/asof_audit/7521ebdeb40f0b55 contains PROTOCOL_FROZEN/PREDICTIONS_FROZEN, predictions.parquet,samples.parquet,error_cases.parquet,RESULTS.json and standalone T30_REPORT.html. Individual error rows match aggregateFP+FN counts. These files remain ignored, never uploaded.

Commands:
`.venv/bin/python -m src.asof_audit`
`.venv/bin/python -m src.asof_audit --verify-only`
Completed same-protocol runs are verified/reused, not refitted; no implicit download. Private samples recompute every metric, funnel, group, reliability/error count and descriptive difference. Public/private result dictionaries match; outcome-phase sample probabilities exactly match pre-outcome frozen predictions.

## Verification and corrected failure

Final focused command:`.venv/bin/python -m pytest -q tests/test_asof_audit.py tests/test_asof_inference.py tests/test_time_machine_coverage.py` — **49 passed in6.06s**.
Full command:`.venv/bin/python -m pytest -q` — **258 passed in15.38s**.
Eight new small offline tests cover batch/single T28 equivalence, future invariance/no evaluation IO, label/Unknown semantics and reveal authorization, common mask/metrics/errors, empty metrics, model deadline/mixed coverage/old-label mismatch, window row alignment and private-export recomputation/tampering/report exports.

Initial focused run46 passed/1 failed at exact single-vs-batch Logistic Regression comparison:0.04790042804910505 vs0.04790042804910507 (~2e-17 floating roundoff). Status stayed IN_PROGRESS; changed only this equivalence assertion to1e-12 tolerance, matching frozen probability reconciliation. Future perturbation frame equality stayed exact; no model/time/label policy weakened. Subsequent47 checks passed; added export/order checks yielded49. No unresolved failures. One report-only patch had a mismatched textual context and was corrected atomically; statistical code/results were unchanged.

Actual frozen model/source/code checks passed. All444 prior local artifact hashes preserved;5 original raw source hashes match frozen source evidence. No existing frozen/T28/T29 statistical source or reports modified. All private outputs ignored; safe public JSON has no participant IDs/home paths/credentials; standalone HTML parses and contains actual bundled Plotly graphs. Verification receipts:/tmp/encounter-t30-before.json and /tmp/encounter-t30-verification.json. Nonfatal sandbox PyArrow warnings persisted.

## Remaining limits, publication and stop

Metrics condition on both past-input validity and future observability, which is outcome-dependent. Unknown actual event rate/full-population AP/ROC/calibration are unidentified; scan bins are proxy evidence, not continuous presence or guaranteed physical negatives. Four exposed dates/repeated pairs are not independent external evidence. Historical event time does not prove actual ingestion availability. No new significance/long-term/generalization claim.

Safe code/docs/aggregate-only commit is pushed to research-v2.2; actual remoteSHA synchronization is verified in execution reply/Git tracking state. No raw/model/individual predictions or large HTML staged; no main merge. **STOP after T30. Next:T31 — 多数据集探索性研究, not started.**
