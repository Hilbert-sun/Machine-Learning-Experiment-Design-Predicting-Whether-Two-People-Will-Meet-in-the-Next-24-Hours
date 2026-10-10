# Encounter Lab — Progress

Date:2026-10-10 (Asia/Kuala_Lumpur)

**T29 — DONE** on research-v2.2, baseline541804c with T28 DONE. Initial worktree clean and branch tracking origin/research-v2.2. Only Time Machine was authorized. T30–T34 were registered TODO, not implemented. Safe current-branch commit/push follows verification; never merge main. Stop after T29 and wait for next.

## Actual functionality

New independent pages/10_Time_Machine.py (eleventh navigation page), src/time_machine.py and src/time_machine_ui.py reuse unchanged T28 candidate/prediction/reveal APIs and metadata discovery. No offline Window Study or old case_keys/predict_case call is required. Dataset/model family/date/hour/A/B/1d3d7d controls show actual saved-model probabilities, historical contact/bin/recency/network/coverage statistics, model versions and label-information deadlines. Invalid sources/models/times produce explanatory empty/error states.

Select→Predict→Freeze→Reveal is enforced in both UI and state controller. Predict does not read future outcomes. Freeze requires a completed prediction and serializes an immutable private record plusSHA256, binding selection version/model artifact versions and actual predictions. Reveal requires valid frozen integrity, independently calls explicit T28 backtest, and displays Contact/No Contact/Unknown with reason. Repeated Reveal reuses the same result; frozen probabilities/digest stay unchanged. Missing numeric historical fields serialize asnull, not fabricated zeros.

All relevant selection, source/data/model/evidence versions participate in context invalidation. Edits clear current prediction/freeze/outcome; actions recheck versions before/after and reject changed context. Future-data edits preserve an already frozen record, invalidate the active version, and give identical historical features/probabilities when re-predicted under the new version. Static archives cannot supply a credible live clock; prospective mode delegates to T28 and rejects verified_clock_required with no displayed probabilities.

Only session memory stores individual prediction/outcome records. No production model fit/save, new dataset acquisition or individual prediction export/upload. Old frozen statistical sources and T28 APIs are unchanged.

## Tests and evidence

Focused command:
`.venv/bin/python -m pytest -q tests/test_time_machine.py tests/test_time_machine_ui.py tests/test_asof_inference.py tests/test_asof_ui.py`
Result:**37 passed in3.65s**. Small offline synthetic fixtures only; no network/private source/model needed. Tests cover ordering and backend rejection, immutable copied payload/integrity, reveal-only future access, version/time/pair/window/model/mode/data invalidation, future perturbations with equal pre-t predictions,3 outcome states/explanations, archival realtime rejection and T28 leakage guards. Initial35 checks passed; adding complete model/version packets and Contact/No Contact UI cases brought focused total37.

Full command:`.venv/bin/python -m pytest -q`
Result:**234 passed in11.95s**, including11-page navigation and all existing tests. No test failed during T29. Nonfatal PyArrow CPU-probe/bare Streamlit warnings remain.

Manual real Copenhagen AppTest:Time Machine opens independently;1/3/7d Predict succeeds; Reveal disabled beforeFreeze; Freeze digest/probabilities unchanged after real outcome reveal; date changes clear active outputs; static prospective request refuses. This is local interface/inference evidence, not a new model-performance experiment. Receipt:/tmp/encounter-t29-check.json.

Preservation:all444 existing models/reports/processed/features files retain pre-taskSHA256 and inventory;5 original raw files match frozen source catalog checksums. Git diff confirms frozen evaluation/statistical modules and T28 source unchanged. Before receipt:/tmp/encounter-t29-before.json. Existing main remains820d080; no merge authorized.

## Changed files

New:pages/10_Time_Machine.py, src/time_machine.py, src/time_machine_ui.py, tests/test_time_machine.py, tests/test_time_machine_ui.py, TIME_MACHINE.md.
Updated:src/ui.py navigation;README operation link;AGENTS.md/TASKS.md/PROGRESS.md instructions and complete T29–T34 checklist. No dependency changes or alterations to old frozen reports/model weights/statistical code.

## Remaining limitations and next task

Current models were trained on future-observation-eligible populations; the enlarged as-of population has not been independently quality/calibration-audited. Known historical labels do not become unseen external validation simply because the UI uses blind ordering. Static archives lack trustworthy live UTC anchors and ingestion-arrival logs. Filesystem version markers catch normal edits/replacements; atomic snapshots and adversarial same-metadata edits are separate future work. Source snapshots must be stable during a call; event time alone does not prove actual past upload availability. Session-only frozen records do not survive session loss.

These are disclosed limits, not relaxed guards. T29 delivers no newAP/ROC or source applicability claim. Next authorized-by-plan task:T30 — 预测质量与选择偏差审计, **not started**. T31–T34 also TODO. **STOP; wait for next.**

## Publication

Per explicit user instructions and standing authorization, safe completed T29 code/docs/tests are committed and pushed to research-v2.2 only after checks. Final commit and actual remoteSHA synchronization are reported in the execution reply/Git tracking state. Raw/model/individual/credential artifacts stay excluded; main is not merged.
