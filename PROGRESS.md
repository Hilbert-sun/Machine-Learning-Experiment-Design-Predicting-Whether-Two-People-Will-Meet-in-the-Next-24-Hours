# Encounter Lab — Progress

Date:2026-10-10 (Asia/Kuala_Lumpur)

**T29-FIX — DONE** on research-v2.2, baseline4bad994. Only the accepted Time Machine label-coverage propagation defect was fixed. T30–T34 remain TODO. Safe commit/push current research branch after verification; no main merge, production model retraining or data acquisition.

## Defect and fix

reveal_prediction() previously omitted min_scan_coverage, silently taking reveal_outcome's default0.5 even when a selected model used0.25/0.75. This could produce incorrect No Contact vsUnknown outcomes.

make_prediction() now obtains each selected model's verified contract via unchanged T28 read_model_contract(). It checks dataset/window binding and requires all selected models' label coverage policies to agree; mixed policies raise label_coverage_policy_mismatch before any probabilities or outcome read. Arbitrary descriptor/widget threshold fields are ignored.

The common future_label_policy (verified threshold,24h horizon, interval, verification source) and each model's verified_min_scan_coverage are stored in the prediction packet. Existing Freeze serializes the entire record and hashes it, so actual policy participates in integrity verification. Reveal validates the frozen policy/model/window consistency and forwards min_scan_coverage explicitly to T28 reveal_outcome; no freely provided/default threshold is used. Missing legacy policy rejects with a request toPredict/Freeze again. No future contact/scan data are needed to choose the policy.

Prediction schema2 participates in context identity, invalidating pre-fix sessions and cached Reveal outcomes. UI displays the verified label threshold and exposes it in frozen model/selection details. Old session records are not silently relabeled under a new default.

## Tests

Focused command:
`.venv/bin/python -m pytest -q tests/test_time_machine_coverage.py tests/test_time_machine.py tests/test_time_machine_ui.py tests/test_asof_inference.py tests/test_asof_ui.py`
Result:**53 passed in5.71s**.

Full command:`.venv/bin/python -m pytest -q`
Result:**250 passed in14.07s**. All tests passed; no failure was hidden or a threshold weakened. Nonfatal PyArrow CPU-probe/bare Streamlit warnings persisted.

New16 regression cases cover the full0.25/0.5/0.75 x future0.4/0.6 no-contact matrix at service and Streamlit levels, both-endpoint minimum rather than averaging, freely supplied descriptor values ignored, mixed verified policies rejected before inference/reveal, frozen-policy tampering detected before future access, legacy missing-policy rejection and cached old-session invalidation.288 daily bins represent nominal0.4/0.6 by nearest115/173 bins; actual ratios are checked, not invented.

Expected matrix:~0.4 future coverage gives No Contact under0.25 only;~0.6 gives No Contact under0.25/0.5. Other combinations are Unknown. Both endpoints must meet the model-specific frozen threshold and the horizon must be complete. Positive-event behavior, as-of candidate/feature/time/future-label isolation are unchanged.

Actual Copenhagen saved-model UI check:three0.5 contracts were independently verified, the rule recorded/displayed/frozen, Reveal completed with unchanged frozenJSON/digest. This is a read-only compatibility check, not new training or research metrics.

## Preservation and files

All444 pre-existing files in models/reports/processed/features retain identicalSHA256 and inventory. All5 original raw-source hashes match frozen catalog evidence. Git diff confirms T17–T27 frozen statistical/report files and T28 APIs unchanged. No production weights/manifests/data/individual predictions modified or uploaded. Preservation receipt:/tmp/encounter-t29-fix-before.json.

Runtime changes:src/time_machine.py and src/time_machine_ui.py only. Added tests/test_time_machine_coverage.py. Updated TIME_MACHINE.md plus AGENTS/TASKS/PROGRESS. No dependency or unrelated feature change.

## Remaining limits and stop

Existing source scan coverage remains an availability proxy; old models were trained on future-observation-eligible populations and are not newly validated/calibrated for all as-of candidates. Static archives lack live anchors and ingestion logs; ordinary file-version guards are not atomic snapshots. These previously documented limits are unchanged by this policy fix.

Task verification is complete; safe current-branch commit/push and actual remoteSHA match are reported in the execution reply/Git tracking state. **STOP after T29-FIX. Next:T30 — 预测质量与选择偏差审计, not started; wait for next.**
