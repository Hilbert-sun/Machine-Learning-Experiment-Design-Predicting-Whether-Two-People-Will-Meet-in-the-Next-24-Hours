# Encounter Lab — Progress

Date:2026-10-10 (Asia/Kuala_Lumpur)

**T28 — DONE** on `research-v2.2`, created from published main`820d080`; initial worktree clean. Only independent as-of-time inference was authorized. All T17–T27 frozen reports/models/statistical sources and evaluation artifacts preserved; no real model refit, network/download or push. Prior task progress remains available in820d080. Stop and wait for next.

## Problem and smallest change

The old window_ui.case_keys read an evaluation feature bank whose rows already passed future target-coverage filtering. Omitting label columns did not eliminate candidate-selection leakage. Old window_ui/predict/features/registry/evaluation code is preserved for frozen reproduction; active Case Explorer no longer calls its case_keys/predict_case.

Added src/asof_inference.py and src/asof_ui.py. Case Explorer uses the independent bridge and is available without Run Study. Offline metric/chart/download behavior remains within the original evaluation scope. Interface details are in ASOF_INFERENCE.md.

## Interfaces and guards

- as_of_candidates(processed,t,dataset_id=...):canonical dataset/time/pair keys exclusively from[t-1d,t) contacts, independent of all scans/labels/eligibility.
- as_of_features(...,windows=(1,3,7)):reuse frozen snapshot_features bounded computation directly. Full selected past span required; no future horizon required. No evaluation cohort/bank/label table read or new inference cache.
- read_model_contract and predict_as_of:verify dataset namespace/source time origin,24h target, feature/window contract, registry checksum and loaded calibration identity. Native manifest time metadata or exact unchanged study-record identity/time metadata is required. Training, validation, threshold and calibration label endpoints all participate in the max deadline; endpoint>=t or unverifiable provenance rejects. Existing study metadata is read-only; no old manifest is rewritten.
- historical_blind_replay:simulate a specified study time with an already-valid model. prospective_inference:require independently verified aware clock anchor plus recent pre-t scans for both devices (default600s,max permitted3600s); no file-mtime/Study-Day guessing. Current archives have no verified live anchor and are explicitly rejected as live predictions.
- reveal_outcome(...,backtest=True):separate future evidence query over(t,t+24h]. Explicit authorization is required before any read. Positive evidence is Contact; absent event is No Contact only with complete horizon/sufficient unique observed bins. Missing/low coverage or incomplete absence is Unknown. Outcome data never enter inference membership or features.

## Verification

Focused offline command:
`.venv/bin/python -m pytest -q tests/test_asof_inference.py tests/test_asof_ui.py tests/test_window_ui.py tests/test_prediction.py tests/test_ui.py`
Result:**48 passed in3.83s**. T28 adds27 small offline tests; existing compatibility tests retained. No unit test depends on network, large datasets or production models.

Full command:`.venv/bin/python -m pytest -q`
Result:**223 passed in10.22s**.

Tests cover t/future contact/observation and source-end perturbations with identical candidates, all bounded features and probabilities; deletion of all future rows; strict pre-t data-read filters; no evaluation-file IO; changed past histories allowing different inputs/probabilities;1d boundaries; wrong namespace/window/origin/hash; every label deadline including equality; missing provenance/scans and old-only/unknown pairs; unsupported target/test-selection provenance; fresh/stale/UTC prospective clocks; explicit reveal, endpoint labels and duplicated-scan Unknown negatives; independent page access and archive-live rejection.

Read-only genuine Copenhagen check at Study Day24:10,995 direct historical candidates vs7,482 old evaluation rows,3,513 formerly excluded candidates. An excluded pair received actual1/3/7d probabilities from unchanged saved models. This is inference verification, not a new experiment/performance claim. Actual page without Run Study displayed3 blind probabilities; prospective mode rejected with verified_clock_required. No production model fit/save was called.

Preservation:all**444** existing files in models/reports/data processed/features match pre-task SHA256 and inventory; all**5** original local raw source files match frozen catalog SHA256. Git diff confirms all existing statistical sources and frozen research reports unchanged. Local verification receipts are in /tmp/encounter-t28-before.json, encounter-t28-real-check.json and encounter-t28-final-check.json; no private sample/probability report was added to Git.

## Corrected failure

Extended initial run:26 passed/1 UI test failed before app execution because AppTest resolved relative app.py against tests/app.py. Switched the test entrypoint to an absolute path and made new model-catalog path resolution independent of report-root/CWD. Rerun27 passed, then additional horizon/UTC guards and full compatibility48/full223 passed. T28 remained IN_PROGRESS until all final checks succeeded. Nonfatal PyArrow CPU-probe and bare Streamlit warnings persisted.

## Changed files

New:src/asof_inference.py, src/asof_ui.py, tests/test_asof_inference.py, tests/test_asof_ui.py, ASOF_INFERENCE.md.
Modified:pages/8_History_Window_Study.py (independent explorer route), AGENTS.md, TASKS.md, PROGRESS.md.
No dependency changes, old statistical module edits, frozen report/model/evaluation data changes, refits or remote push.

## Residual risks and next suggestion

Current models were still trained on future-coverage-eligible offline populations; new candidate coverage may shift distribution and calibration. Old AP/ROC/Brier must not be applied as guarantees for all as-of candidates. Source scan coverage is an availability proxy, not continuous presence. Model-time and live-clock authenticity depend on trustworthy producer provenance; source snapshots must remain consistent during a call, and actual ingestion availability under delayed uploads/revisions needs upstream provenance. Relative static archives do not supply live wall-clock evidence. The frozen old case APIs remain legacy only and are not used by the active page.

Recommended next task (not started):independent evaluation of the as-of population plus auditable model/live-clock/source manifests. **STOP after T28; wait for next.** Local commit, if made, is identified in the final reply/Git history; no push authorized.


## Subsequent publication authorization

The user then instructed “以后做完全部推送”. Completed and verified tasks now default to safe commits and pushing all unpublished completed-task commits on their current development branch. This includes the completed T28 research-v2.2 branch; main remains820d080 unless separately authorized. The earlier no-push statements describe implementation-time scope and are superseded by this later instruction. No new task starts. Publication is verified in the execution reply/Git tracking state. Future explicit no-push instructions take precedence; raw/private/model artifacts remain excluded.
