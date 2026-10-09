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

T01–T16 software tasks are complete and verified. T16 included full testing, documented startup, raw-scan integration and source-only GitHub delivery. Stop; do not download full datasets, train a study model or invent new development work without a new user instruction. Research-data limitations in DELIVERY.md remain in force.

## Prediction data contract

- T07 candidates use contacts strictly before t; labels use (t, t+24h]. Unknown/low-coverage samples are excluded from primary evaluation, and absent events without adequate scans keep a null label.
- T08 features use [t-window, t) only. Join labels/features by timestamp, user_min and user_max; never include future label coverage or eligibility fields in model inputs.
- Communication, RSSI, weekday and coverage fields unavailable from reliable sources remain null, not zero. Default weekday origin is unconfirmed. SocioPatterns currently has no samples eligible for the primary evaluation policy.
- T09 splits whole prediction times chronologically and purges labels with t+24h >= the next set's start. Calibration uses early validation, tuning uses later validation, with the same strict label-window separation.
- Fit preprocessing/models on train only; all-null train columns are removed. Parameters, calibration and thresholds use validation only. Keep final test scores for the final evaluation task.
- Phase-three native model/calibration/persistence verification used explicitly synthetic test fixtures. No real study model was trained: current SocioPatterns has zero eligible primary samples. Do not relabel unknowns or present fixture metrics as research results.
- Prediction Lab requires t strictly after the saved model's validation-label information deadline. Future mode must not read/display actual outcomes. Feature-window policy must match the saved model; preserve legacy full-bank models with a null window contract.
- Evaluation uses frozen models/thresholds and exact saved input signatures. All window/communication ablations run on validation only. E3 stays unavailable without verified communication availability; never fabricate scores.
- Native TreeSHAP applies to XGBoost/LightGBM base raw margins, not calibrated probabilities. Other local sensitivity methods must not be labeled SHAP or causal. Keep synthetic-fixture provenance in pages, figures and exports.

## Local environment

- Use Python 3.11 and the project-local `.venv`.
- Run focused tests with `.venv/bin/python -m pytest`.
- Treat dataset and model directories as local artifacts; never commit data, trained models, secrets, or the virtual environment.
- The GitHub destination authorized by the user is `https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours` (renamed from `Hilbert-sun/-24-` during publication); preserve existing remote history and never force-push.
