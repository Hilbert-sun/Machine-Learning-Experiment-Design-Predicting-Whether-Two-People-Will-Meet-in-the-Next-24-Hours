# Encounter Lab — Session Instructions

Use incremental, task-based development with limited Codex usage.

## Scope and workflow

- Default to one requested task per execution. If the user explicitly authorizes a range, complete it sequentially, verifying and recording each task before the next. Never start a task outside the authorized range.
- Read `PROJECT_SPEC.md` first, then this file, `TASKS.md`, and `PROGRESS.md`. Consult relevant specification sections before implementation.
- Check task dependencies and acceptance criteria. If definitions are missing, document the blocker; never invent requirements.
- Before editing source, inspect only files relevant to the current task.
- Implement the smallest working solution. Reuse existing code, dependencies, configuration, and tests.
- Never regenerate the project or rewrite completed modules unless necessary for the requested task.
- Minimize tool calls, context, and token usage. Do not download large datasets unless the current task explicitly requires them.
- Never invent dataset fields, model scores, or experiment results.
- Run focused tests for the requested task. Mark it DONE only after verification succeeds.
- If tests fail, retain IN_PROGRESS or mark BLOCKED and document the exact failure.
- Maintain `TASKS.md` with the complete checklist, dependencies, statuses, and acceptance criteria. Maintain `PROGRESS.md` with the latest summary, test results, blockers, and next recommended task.
- Report task ID, files changed, tests performed, result, issues/blockers, and next task. Then STOP and wait for the user's instruction.

Valid task statuses: TODO, IN_PROGRESS, DONE, BLOCKED.

## Task boundaries and authorization

The first execution was limited to T01 and is complete. The user subsequently authorized T01–T04 together: reuse T01, implement and verify T02, then T03, then T04, updating status after each; stop after T04. For later requests, default to one task unless the user explicitly authorizes a range. The task board defines T01 as project/dependency initialization and T02 as the Streamlit UI framework; keep these tasks separate even though specification Phase 1 covers both. The user's one-task constraint takes precedence over broader execution instructions embedded in the specification.

## Current authorized range

The user authorized and completed T23–T27 together, following prior T01–T22. All27 task statuses are DONE within explicitly documented source eligibility limits. Stop now; no new task or remote push automatically. Frozen T17–T22 evidence is preserved. T23 adds true backend research UI (new configurations validation-only) and T24 a source catalog. T25/T26 public source diagnostics are complete; that does not mean all sources support training. Reality Mining processed time ticks and scan evidence are unverified; Workplace7d evaluation days/online logs are insufficient; Social Evolution official live access/license/header remain unverified and no real file was acquired. Preserve these outcomes. Read RESEARCH_REPORT.md, WINDOW_STUDY.md, DATASET_CATALOG.md and reports/T27_VERIFICATION.json for delivery. Raw data/per-sample predictions/models stay local; no push was authorized.

## Prediction data contract

- T07 candidates use contacts strictly before t; labels use (t, t+24h]. Unknown/low-coverage samples are excluded from primary evaluation, and absent events without adequate scans keep a null label.
- T08 features use [t-window, t) only. Join labels/features by timestamp, user_min and user_max; never include future label coverage or eligibility fields in model inputs.
- Communication, RSSI, weekday and coverage fields unavailable from reliable sources remain null, not zero. Default weekday origin is unconfirmed. SocioPatterns currently has no samples eligible for the primary evaluation policy.
- T09 splits whole prediction times chronologically and purges labels with t+24h >= the next set's start. Calibration uses early validation, tuning uses later validation, with the same strict label-window separation.
- Fit preprocessing/models on train only; all-null train columns are removed. Parameters, calibration and thresholds use validation only. Keep final test scores for the final evaluation task.
- Phase-three initial verification used synthetic fixtures. T17 subsequently trained genuine Copenhagen models; reports/T17_REAL_EXPERIMENT.md and T17_METRICS.json are the real evidence. SocioPatterns still has zero primary-eligible samples. Never relabel unknowns or present fixture metrics as research results.
- Prediction Lab requires t strictly after the saved model's validation-label information deadline. Future mode must not read/display actual outcomes. Feature-window policy must match the saved model; preserve legacy full-bank models with a null window contract.
- Evaluation uses frozen models/thresholds and exact saved input signatures. All window/communication ablations run on validation only. E3 stays unavailable without verified communication availability; never fabricate scores.
- Native TreeSHAP applies to XGBoost/LightGBM base raw margins, not calibrated probabilities. Other local sensitivity methods must not be labeled SHAP or causal. Keep synthetic-fixture provenance in pages, figures and exports.
- T17's held-out test scores have now been reported. Do not use them to choose new thresholds/features/hyperparameters; later tuning needs a new validation design. Preserve the original T17 results, including worse Logistic Regression probability scores and raw/calibrated XGBoost variants.
- Reports remain ignored except the five T17, fifteen T18–T22 and nine T23–T27 reviewed aggregate deliverables explicitly whitelisted by filename in .gitignore. Do not broaden that whitelist to per-run private manifests, individual samples, large HTML bundles or model files.

## Local environment

- Use Python 3.11 and the project-local `.venv`.
- Run focused tests with `.venv/bin/python -m pytest`.
- Treat dataset and model directories as local artifacts; never commit data, trained models, secrets, or the virtual environment.
- The GitHub destination authorized by the user is `https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours` (renamed from `Hilbert-sun/-24-` during publication); preserve existing remote history and never force-push.

## Research window contract (T18–T22)

- Main cohort is shared1d historical candidates, full7d source span, original0.5 future scan coverage, exact dataset/time/pair keys and labels; all windows share split hashes. Source span is not proof of continuous observation.
- Research features are bounded_window_v1 from window_features.py; never feed legacy E2 banks as equivalent strict budgets. All counts/activity/network/RSSI/scan/frequency/recency use the selected1/3/7d interval only.
- Research WindowModel reuses ModelRegistry estimators/persistence but requires neutral bounded features and matching history_window_days. Local models use models/.window_study to stay out of legacy UI selectors.
- Parameters/seed/split/threshold/calibration/fold/uncertainty rules were frozen before new test scores. Raw models are reported because3 validation dates cannot support independent calibration plus>=2 tuning dates after purge.
- Four primary test days are below the8-day bootstrap-CI gate; paired daily and leave-one-day-out ranges are descriptive, not confidence intervals. Prespecified expanding folds are dependent robustness evidence; no significance or long-term claim.
- Separate7d candidate expansion reports reach counts only; its population differs from the main1d pool. Do not compare expanded-pool AP as a pure history-window effect. Do not compare T17/new raw AP as identical-cohort improvements.

## Research edition delivery (T23–T27)

- History Window Study default settings reuse verified frozen evidence. Altered settings produce separately versioned validation-only jobs. Never use displayed frozen test scores to choose new parameters/windows/coverage.
- Future Case Explorer must read only historical feature banks and use times after the saved selection-information deadline. Read actual targets only on explicit backtest; unavailable target stays Unknown.
- DatasetAdapter namespaces every source, validates schema/time/IDs and keeps calendar capacity separate from reliable observation. Unknown processed tick units must not become seconds/days. Missing contacts must not become negatives.
- New public source downloads require verified license/real URL and a bounded schema probe first. Do not infer data license from a site's source-code footer, or infer access restriction from an outage. No bypass of restricted sources.
- Manual imports validate before publishing and refuse replacement of existing raw files. Schema/time/license policy changes invalidate adapter caches. Parsed data and manifests are local except reviewed aggregate deliverables.
- Full verification uses project .venv pytest, window_verify, research_delivery and real UI/export checks. Ten navigation pages are delivered. Research interfaces use hidden bounded-window model registries; legacy model UI contracts remain intact.
