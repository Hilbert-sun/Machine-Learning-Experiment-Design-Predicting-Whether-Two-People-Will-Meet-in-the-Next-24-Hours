# Encounter Lab — Progress

Date:2026-10-10 (Asia/Kuala_Lumpur)

**T31 — DONE**, research-v2.2, baseline fa6c965. Only multi-source descriptive networks/observed-positive retrieval authorized. T32–T34 TODO. No refit, changed thresholds, invented negatives, or alteration to frozen T17–T30 statistical source/results/models. Safe branch publication and remote SHA verification, then STOP.

## Implementation and real evidence

New src/positive_retrieval.py, multisource_exploration.py, multisource_report.py, multisource_ui.py, pages/11_Multi_Dataset_Exploration.py; now12 navigation pages. Reused DatasetAdapter v3, verified read-only catalog caches, Arrow time-filtered chunk IO, NetworkX and Plotly. No source acquisition. Copenhagen binary evidence remains frozen/separate.

Run **6d5df52b7fd76419**, real_public_dataset. Publisher pages rechecked: Workplaces seconds/20s intervals/CC0; HighSchool UNIXctime seconds/20s intervals/CC BY-NC-SA; Mendeley processed CC BY4.0 but no verified tick conversion. SocialEvolution overview/dictionary returned502; no actual lawful source/license/header/timezone/raw-only interpolation provenance verified. No bypass/download or successful integration claim. SourceSummary gives relative paths, hashes, schema, unit/origin and independent source status.

| Source | Contact IDs | Valid records | Unique canonical records | Pairs | Span days | Status |
| --- | --- | --- | --- | --- | --- | --- |
|Workplace2013|92|9,827|9,827|755|11.430787|positive_retrieval_ready; descriptive_ready|
|Workplace2015|217|78,249|78,249|4,274|11.499306|positive_retrieval_ready; descriptive_ready|
|HighSchool2013|327|188,508|188,508|5,818|4.207870|insufficient_history; descriptive_ready|
|RealityMining processed|96|1,086,403|27,572|2,539|unknown|time_unit_unverified; descriptive_ready|
|SocialEvolution|unknown|unknown|unknown|unknown|unknown|source_unavailable|

Each Workplace has2 dates without contact records (not proven contact-free days). Complete1/3/7d+24h times9/7/3, nonempty candidates7/5/3, positive-pool times6/4/3. HighSchool times2/0/0. MIT ticks0–233 unconverted;1,058,831 exact repeats diagnosed, no time-based retrieval. No identity merging; exact canonical timestamp/pair repeats count once only in new analysis. Records are not physical meetings or conversations.

## Fixed retrieval protocol and results

Fixed daily08:00 source-clock snapshots, K5/10/20, frequency/last-recency/common-neighbors, descending score/ascending namespace/minID/maxID ties. Source/processed/code hashes, versions, times and rules freeze first. Candidates only[t-1d,t), scoring/graphs only[t-window,t). Scores saved and rankings fixed BEFORE explicit backtest reads(t,t+24h]. No fitted estimator or implicit negative labels.

Capture@K divides observed hits by observed future positives IN the pool; capture-all and candidate reach separately use ALL future recorded positives. Empty denominator=null. Absent recorded contacts remain Unknown; no Accuracy/Precision/F1/AP/ROC/Brier/LogLoss. Public actual_k sums selected ranks across snapshots; private rows retain min(K,candidate_count) per time. Per_window dates differ; common_7d shares dates and1d candidates across windows.

Common_7d covers only3 dates per Workplace. Snapshot-pair totals (not distinct persons or independent trials):

| Source | Candidates | All observed future positives | In-pool | Outside-pool | Frequency Top20 hits1/3/7d | Capture@20 1/3/7d |
| --- | --- | --- | --- | --- | --- | --- |
|Workplace2013|458|469|147|322|31/34/35|0.210884/0.231293/0.238095|
|Workplace2015|2,349|2,143|533|1,610|31/35/34|0.058161/0.065666/0.063790|

Candidate reach31.3433%/24.8717%. Outside-pool does not mean first-ever appearance. No significance/generalization or cross-source leaderboard. HighSchool two-date1d results flagged insufficient;3/7d skipped. Network components/density, broad degree/pair-frequency histograms, daily/repeat activity and mean bounded historical density are real aggregates.

## Deliverables and reproduction

MULTISOURCE_STUDY.md and README index. Five exact reviewed reports/multisource files: T31_SOURCE_SUMMARY.json, T31_NETWORK_METRICS.csv, T31_RETRIEVAL_METRICS.csv, T31_FEASIBILITY.json, T31_PROTOCOL.json. Only these filenames newly whitelisted; no participant/pair IDs. Small nonzero count/ratio families and histogram groups suppressed; this is not a formal anonymity guarantee.

Ignored data/processed/multisource/6d5df52b7fd76419 contains frozen protocol, per-time/window scores, future positive pairs, retrieval_rows.parquet, RESULTS.json and standalone T31_REPORT.html. All522 private time/window/method/K rows exactly recompute117 public aggregate rows. Public/private JSON agree; CSV agrees within1e-12 serialization tolerance after column alignment. Source/code hashes match protocol. Every private file Git-ignored. Real AppTest across all5 sources passed, including SocialEvolution with no placeholder metrics.

```bash
.venv/bin/python -m src.multisource_exploration
.venv/bin/python -m pytest -q tests/test_positive_retrieval.py tests/test_multisource_exploration.py tests/test_multisource_ui.py tests/test_asof_inference.py tests/test_asof_ui.py tests/test_time_machine.py tests/test_time_machine_ui.py tests/test_time_machine_coverage.py
.venv/bin/python -m pytest -q
```

## Verification and corrected failures

Final focused **76 passed in7.02s**. Final full **282 passed in17.93s**.23 new T31 tests plus new router case cover future replacement/addition/deletion invariance, history changes, shared1d candidates, exact interval boundaries, dedup/stable ties, explicit reveal, Unknown/empty/disjoint pools, hand-counted Top5/10/20/actual_k, unverified ticks/incomplete windows, namespaces, disclosure, missing required source, corrupted cache, SocialEvolution provenance guard, freeze-before-reveal, repeatability/recomputation, aggregate exports, old sentinel and UI switching/unavailable states.

Initial4 failed/17 passed: empty-window assertion selected a fixture time containing an edge, and three fixtures omitted citation. Corrected fixtures. Next1 failed/20 passed exposed NumPy group-key JSON serialization; normalized declared numeric metadata to Python int. Initial real run hit the same export failure before public results; final version reran successfully. Earlier full280 passed preceded two extra tests. Independent verification first compared sorted JSON column order with CSV insertion order; aligned fields, then all values passed. Status stayed IN_PROGRESS until checks passed. A progress-document patch rejected duplicate Delete/Add operations before changing that file; wrote it with one replacement. No unresolved failures; PyArrow sandbox CPU warnings nonfatal.

Preservation snapshot /tmp/encounter-t31-before.json covers582 prior files. **576 protected files unchanged**, excluding six intentionally maintained workflow/navigation files(.gitignore,AGENTS,PROGRESS,TASKS,README,src/ui.py). Includes prior raw/processed/features/models/reports/statistical code. No old experiment rerun or overwritten. Final real recomputation/UI/safety receipt /tmp/encounter-t31-verification.json.

## Limits, publication and stop

No independent scanner-online logs: Unknown cannot justify binary evaluation. Complete archive span is not continuous coverage or historical ingestion evidence. Only3 complete7d Workplace dates/2 short HighSchool dates; repeated users/pairs and different sensors limit conclusions. MIT units and SocialEvolution legal/raw provenance remain unresolved source-level limitations, not successful time experiments. Both required real Workplace experiments, quality/topology, UI, tests, recomputation and preservation pass within these stated limits; no current T31 task blocker.

Safe code/docs/five aggregate reports only committed/pushed to research-v2.2; actual remote SHA verified in execution reply/tracking state. No raw/model/pair/ranking/private HTML/credentials staged; no main merge. **STOP. Next:T32 — 数据处理和前端性能优化, not started.**
