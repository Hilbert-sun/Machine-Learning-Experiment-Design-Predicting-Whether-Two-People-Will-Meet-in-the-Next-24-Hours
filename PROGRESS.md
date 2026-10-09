# Encounter Lab — Progress

Date: 2026-10-10 (Asia/Kuala_Lumpur)

Authorized scope: T18–T22 from RESEARCH_SPEC.md. Complete sequentially and stop after T22. No push/download/new UI. T17 remains immutable at f116951; its complete original progress is available in that commit.

## T18 — DONE

Added baseline_audit.py, immutable T18_BASELINE_MANIFEST.json, T18_AUDIT.md and freeze/E2 tests. Verified original sources/model/report hashes and baseline source hashes at f116951. Eligible769,627 minus Day16 purge37,735 and Day21 purge46,597 equals685,295 retained rows; all losses explained. Legacy E2 masks long columns but uses all-history candidates and masks14d frequency into a constant: insufficient for a strict information-budget comparison. Original full tests plus new tests:173 passed in7.77s. No T17 file changed.

Remaining risk: few dates, scan-bin proxy, existing T17 test exposure. New results must not be described as pristine external validation or use test scores for tuning.

## T19 — DONE

Added window_cohort.py and common-cohort tests. Genuine strict1d candidates/full7d-span cohort:100,485 eligible rows across20 days,54,677/14,816/25,569 train/validation/test rows over11/3/4 dates. Purge5,423 (Day19:4,775; Day23:648). Stored common Parquet/split assignments locally and aggregate hashes/day funnel publicly. Existing0.5 future coverage preserved. Independent calibration plus>=2 threshold dates is unsupported; raw models fixed for all windows.25 focused tests passed in0.89s; real construction and cache replay succeeded. T17 preserved.

## T20 — DONE

Added window_features.py and isolation/cache tests. Every feature is explicitly clipped to its1/3/7d interval; legacy T17 source contracts unchanged. Real banks each100,485 rows and identical common keys; private content-hash receipt saved. SHA source/window/feature/cohort keys and per-snapshot recoverable caches implemented.14 tests passed in1.30s, covering t-5d/t-10d/t/future perturbations, unknown scans and interrupted-cache reuse. T17 immutable artifact verification passes.

## T21 — DONE

Added bounded WindowModel using existing registry estimators/persistence, fixed-protocol study and aggregate report renderer. Real run102140b8cf3df83f freezes source/cohort/feature/code/package hashes and future T22 rules before test scores.1d/7d share25,569 test samples with21.38136% positives. XGBoost AP0.5887225→0.6913660 (delta+0.1026435), Brier0.1280261→0.1091068; frequency/logistic results including poor1d-frequency probabilities retained. All models/thresholds frozen before evaluating test; raw calibration policy preserved. Individual probability/label Parquet and hidden local models ignored; safe aggregate CSV/JSON/Markdown and standalone local HTML generated.18 focused tests passed in1.90s; real exported metrics recompute and save/load/code-freeze/T17 checks passed. No pristine-independent-test or significance claim.

## T22 — DONE

Added window_robustness.py and robustness tests; extended the output-only renderer. Same study run adds3d with identical cohort/parameters. XGBoost AP1d/3d/7d =0.5887225/0.6274940/0.6913660; ROC-AUC0.7706562/0.7997190/0.8414945; Brier0.1280261/0.1208013/0.1091068. Test prevalence21.38136%. Logistic/frequency comparators and poor frequency probability scores are fully reported.

7d−1d XGBoost delta+0.1026435, positive on all4 primary test days; leave-one-day-out descriptive range[+0.0937274,+0.1121683]. Four dates are below the predeclared8-day gate: confidence_interval=null, insufficient_days_for_ci. This is a descriptive sensitivity range, not a confidence interval or significance claim.

Prespecified forward folds test Days16–17,19–20,22–23, with3/6/9 train dates and3 validation dates each, strict24h boundary purge. XGBoost7d−1d AP deltas+0.084520,+0.086919,+0.044854. These expanding folds are dependent and choose no primary parameters/windows. All their test dates precede primary Days24–27; earlier T17 exposure remains disclosed.

Exported contact-frequency/scan-quality/day sensitivity for all9 model/window combinations. Separate7d candidate reach across all20 cohort dates:474,339 eligible rows versus100,485 for1d (extra373,854). No expanded-pool AP or pure-window-effect claim. No new source/UI.

## Final verification and corrected failures

- T18 full original/new freeze tests:173 passed in7.77s.
- T19 focused cohort/temporal/label tests:25 passed in0.89s; real common cohort and cached replay succeeded.
- T20 focused feature/cohort tests:14 passed in1.30s; real banks and t-5d/t-10d/t/future invariance passed.
- T21 focused model/window tests:18 passed in1.90s; actual probability exports reproduce metrics, saved model probes match.
- T22 focused robustness/cohort/model/temporal tests:17 passed in2.14s.
- Final full `.venv/bin/python -m pytest -q`: **185 passed in9.36s**.
- `.venv/bin/python -m src.window_verify`: five actual stages (primary,3d,three folds) recompute all binary metrics;36 saved models reproduce their complete exported predictions; T17 artifacts unchanged; T21 statistical hashes and frozen T22 implementation match.
- Standalone T21/T22 HTML files parse and contain bundled Plotly code/actual graphs; safe JSON parses and CSVs contain actual model scores. These large HTML bundles stay ignored locally.
- Initial T22 collection/CLI import failed at window_robustness.py:88 with SyntaxError (missing subgroup dictionary delimiter); fixed before any T22 fit and17 relevant tests passed afterward.
- Initial final read-only verifier failed at window_verify.py:39 AssertionError: a flat single3d model manifest was compared with a window-indexed multi-bank map. Normalized this metadata shape in the verifier only; full36-model probability equivalence then passed. Frozen statistical code/results were unchanged.
- Nonfatal PyArrow sandbox CPU-probe warnings persisted. No remaining implementation blocker. Calibration/CI/data-source limits are explicitly reported, not silently relaxed.

## Files and safe artifacts

Added RESEARCH_SPEC.md (supplied research requirements), eight audit/cohort/window/model/experiment/report/verification source modules and five focused test modules. Updated AGENTS/TASKS/PROGRESS/README and exact-file ignore exceptions. No existing T17 statistical source changed; no existing UI file changed. New aggregate reports live in reports/window_study; exactly15 reviewed filenames are eligible for Git. Per-run predictions, feature/label Parquet, private model manifests, model weights and large standalone HTML remain ignored. Original T17 report/model/data hashes still match.

Local private run: `reports/window_study/102140b8cf3df83f/`; models:`models/.window_study/102140b8cf3df83f/` (hidden from legacy UI registry lists). Public metrics:`T21_METRICS.csv`,`T22_METRICS.csv`,`T22_SENSITIVITY.csv`,`T22_WALK_FORWARD.csv`; aggregate JSON includes run/protocol/source/cohort/feature/code checksums and every actual distinct prediction date. T17 original progress remains in f116951.

## Commands and reuse

Implemented sequentially, verifying and marking each task before advancing. Ran `python -m src.baseline_audit`, cohort/feature generation APIs, `python -m src.window_study`, `python -m src.window_robustness`, focused pytest files as above, full pytest and `python -m src.window_verify`. Use project-local .venv/bin/python. No implicit downloads or uploads. Later reruns of completed study commands reuse the completed run; use window_verify for complete read-only code/data/model/result checks. New clones require the matching ignored local artifacts and must not substitute mismatched inputs.

## Remaining risk and stop

Same-source fixed-protocol temporal evidence supports7d over1d in the evaluated periods. Only4 primary dates, prior T17 date exposure, dependent recurring users/pairs, uncalibrated probabilities, scan coverage proxy and device-proximity target limit generalization. It is not pristine independent validation. Different cohort prevalence means new AP cannot be compared directly with T17 as identical-cohort model improvement. Do not retune these reported test sets.

**Requested T18–T22 all DONE. Next recommended task:T23 (History Window Study UI), not started. STOP.** Safe local commit only; no remote push. Commit ID is reported in the execution reply/Git history.
