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

## Standing publication authorization

The user subsequently instructed: “以后做完全部推送” (push all completed work going forward). After each authorized task is complete and verified, review and commit only safe task files, push all unpublished completed-task commits on the current development branch to origin, and verify synchronization. This standing authorization includes publishing the completed T28 research-v2.2 branch. Do not ask again for ordinary branch pushes. A later explicit no-push instruction overrides this default for its scope. Never upload raw/private data, individual predictions, model artifacts or credentials; never force-push, merge into main, or publish unrelated branches without authorization. This rule overrides earlier historical no-push notes in project documents; it does not authorize starting another task.

## Current authorized range

T30 only was authorized and is DONE on research-v2.2 after e1fe901. Fixed-model as-of audit run7521ebdeb40f0b55 covers already published Study Days24–27, not a pristine test.38,005 past-only candidates,37,913 T28-valid predictions,27,820 known labels/10,185 Unknown; metrics use27,802 common known/predicted rows. OldT22's25,569-row cohort/probabilities/labels/metrics reproduce.49 focused and258 full local tests pass;444 old artifact hashes and5 raw checksums unchanged. No model refit/tuning/download. Safely publish only reviewed code/docs/aggregate reports, verify remote SHA, then STOP. T31–T34 remain TODO; next:T31 multiple-dataset exploratory research. Never merge main.

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
- Reports remain ignored except the five T17, fifteen T18–T22, nine T23–T27 and seven T30 reviewed aggregate deliverables explicitly whitelisted by filename in .gitignore. Do not broaden that whitelist to per-run private manifests, individual samples, large HTML bundles or model files.

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
- Case Explorer must generate candidates from[t-1d,t) contacts and bounded features from raw pre-t contacts/observations, never a future-filtered evaluation bank. Use times strictly after every saved training/selection-label deadline. Actual outcomes belong to the separate explicit-backtest reveal API; unreliable absence stays Unknown.
- DatasetAdapter namespaces every source, validates schema/time/IDs and keeps calendar capacity separate from reliable observation. Unknown processed tick units must not become seconds/days. Missing contacts must not become negatives.
- New public source downloads require verified license/real URL and a bounded schema probe first. Do not infer data license from a site's source-code footer, or infer access restriction from an outage. No bypass of restricted sources.
- Manual imports validate before publishing and refuse replacement of existing raw files. Schema/time/license policy changes invalidate adapter caches. Parsed data and manifests are local except reviewed aggregate deliverables.
- Full verification uses project .venv pytest, window_verify, research_delivery and real UI/export checks. Ten navigation pages are delivered. Research interfaces use hidden bounded-window model registries; legacy model UI contracts remain intact.

## T28 as-of inference contract

- Use as_of_candidates/as_of_features/predict_as_of; no evaluation cohort, eligibility field, future scan coverage or stored evaluation-bank membership may determine inference inputs. All reads constructing inputs are clipped strictly beforet.
- Verify namespace, source time origin,24h target, bounded_window_v1 feature/window identity, saved model checksum/calibration identity and training/validation/threshold/calibration label endpoints. Unknown provenance or any endpoint>=t rejects. Existing metadata is adapted read-only; do not edit old manifests to invent earlier cutoffs.
- historical_blind_replay is historical simulation, with an already time-valid model. prospective_inference requires an independently verified aware UTC anchor and fresh pre-t observations for both devices; file mtime/download date is not evidence. Static archives without an anchor reject live mode.
- reveal_outcome is a separate explicit backtest action, never called by blind inference. Only adequately observed complete horizons justify negative outcomes; unique observed bins, not duplicate row counts, determine coverage.
- Expanded as-of membership is not covered by old future-filtered-cohort performance/calibration guarantees. Re-evaluation and trusted live clock/feed provenance are suggested future work, not started by T28.

## T29 Time Machine contract

- Use pages/10_Time_Machine.py and time_machine.py/time_machine_ui.py. Inference uses T28 directly; no old future-filtered case/feature bank or offline study prerequisite.
- Prediction succeeds before Freeze is enabled; Freeze precedes independent Reveal. Serialized frozen probability/input/model-version records remain immutable; reveal never recomputes probabilities. Outcomes remain Contact/No Contact/Unknown with coverage/completeness reasons.
- Date/hour, pair, dataset, mode, selected windows/models and normal data/model/evidence file-version edits reset active prediction/freeze/reveal state. Future edits may invalidate a version but cannot change the stored frozen record or pre-t features/probabilities on re-prediction.
- Records are session-only and private, not Git artifacts. Model provenance and label deadlines are shown. Static archives reject live mode via T28 clock/freshness guards.
- Version metadata checks before/after actions are not atomic ingestion snapshots or proof of historical upload availability. Those concerns/performance caches belong to T32; new population-quality audit belongs to T30. Do not implement those tasks during T29.

## T29-FIX label coverage contract

- Read each selected model's min_scan_coverage through unchanged T28 read_model_contract, not freely supplied row/widget values. Selected window policies must agree for a unified prediction/reveal; reject mixed policies before inference/outcome access.
- Freeze common future_label_policy and per-model verified_min_scan_coverage alongside probabilities; the existing full frozen JSONSHA protects these fields. Reveal validates consistency and passes the frozen threshold explicitly to reveal_outcome. Missing/invalid legacy policy never falls back to0.5.
- Prediction schema2 is included in context identity to invalidate old sessions, including cached pre-fix revealed outcomes. New Predict/Freeze is required. Coverage-policy metadata is known before prediction; actual future scan evidence is still read only by explicitReveal.

## T30 audit interpretation

- asof_audit.py freezes all pre-t candidate probabilities before any outcome/old-cohort read. Common prediction validity is past-only; future known/Unknown and strict covered populations are separate.
- Observed positive evidence is known even with low future coverage; absent events need complete sufficiently scanned horizons. Unknown never becomes0 and never enters binary metrics. Reliable-subset metrics do not identify unbiased performance of all candidates.
- Extra candidates have strongly selective positive-only known labels; AP=1 in added known-only samples is degenerate, not perfect prediction. Compare population/prevalence/Unknown rates alongside model metrics.
- Four dates and repeated participants/pairs allow descriptive differences/leave-one-day sensitivity only, no significance/CI claim. No threshold/parameter/calibration selection on these exposed dates.
- Individual predictions/labels/errors/HTML stay under ignored data/processed/asof_audit/<run_id>. Seven aggregate report files are explicitly whitelisted; no broad report/data whitelist. --verify-only recomputes metrics/funnels/groups/reliability/errors from local frozen samples.
