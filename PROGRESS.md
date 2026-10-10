# Encounter Lab — Progress

Date:2026-10-10 (Asia/Kuala_Lumpur)

**T32 — DONE**, research-v2.2, baseline5c745530e60b3cfda341b1878ebd98175e9aa223. Only performance, safe caching and stable archive snapshots authorized. No refit, downloads, changed scientific rules or frozen result replacement. T33–T34 remain TODO. Safe code/docs/three aggregate reports only; current-branch publication and remote SHA verification, then STOP.

## Baseline first and actual measurements

Before any performance code edits, captured850 original file hashes in ignored data/processed/performance/T32_PRESERVATION.json, generated immutable T32_INPUTS.json and T32_BASELINE.json, then froze its SHA in T32_BASELINE_RECEIPT.json. Verified all preexisting src hashes unchanged at this gate. Baseline covers12 genuine workloads x5 independent Python processes: four source networks; Workplace2013/2015 1/3/7d rankings; Copenhagen candidates/features/saved-model prediction/loading/selection-data preparation; public aggregate loading. All required local real sources/models were present; no synthetic substitution or download.

Same Apple M5/16GiB/Python3.11.15 environment; native ru_maxrss captures Arrow/NumPy allocations, including interpreter/imports. Wall time excludes imports/setup. Cold=empty APPLICATION cache, not a claim to clear OS pages. Warm reference executes immutable T31 git-exported source at5c74553, with the same inputs and priming. Each mode has5 fresh processes, median/min/max reported. Baseline hardware receipt captures actual available-memory proxy3,124,461,568 bytes (free+inactive+speculative, not guaranteed allocatable memory). OS/desktop noise remains explicit.

Final series **optimized_release**; previous optimized/optimized_v2/optimized_final are retained diagnostic iterations, not final reported values. All timed implementation hashes match final code except the untimed report/audit generator. Performance comparisons use exactly identical input metadata/hashes and environments.

| Operation | Cache | Before | After | Change |
| --- | --- | --- | --- | --- |
|RealityMining network peak RSS|cold|439.6875MiB|318.3594MiB|27.5942% reduction; meets25% target|
|Copenhagen1/3/7d features|warm|0.767504s|0.015926s|97.9250% time reduction|
|TimeMachine saved-model prediction|warm|0.782652s|0.039108s|95.0032% time reduction|

Copenhagen features physical Parquet source opens7→3 cold; selected-model prediction9→3. Workplace multi-window ranks3→1. Warm private feature/ranking hits require0 raw Parquet event scans, but still verify opaque source bytes and cached payload hashes. Private payload reads reported separately. Model clones and public aggregate cache have distinct hit counters. No probability cache exists. Report24 cold/warm comparison rows, actual source rows/inventory bytes, processed Parquet rows, read/repeat counts, RSS/time ranges, versions and explicit exceptions.

Cold requests pay for snapshot hashing/copying, private bundle verification and isolated model loading: candidates0.009567→0.026207s, model loading0.01905→~0.0280s, selection-data preparation0.02118→~0.0399s; Workplace cold rankings also slower. These are explicit security exceptions, not hidden gains or comparisons against warm requests. Attribution is inferred from added work, not a separately timed decomposition. Whole Streamlit render/context-hash speed was not benchmarked; selection preparation was. Other measured paths/ranges are in PERFORMANCE_AUDIT.md and CSV. No all-path, cross-machine or significance claim.

## Implemented safeguards and optimization

New snapshot_manager, safe_cache, bounded_history, readonly_models, public_cache, performance_benchmark and performance_audit modules. Relevant T28/T29/T31 data paths updated; frozen window_features/model_registry/evaluate/statistical code unchanged. Incremental exact canonical dedup and streamed graph statistics avoid retaining all repeated MIT rows. Arrow readahead bounded to1; a single max-history pre-t scan feeds independently filtered windows through original T20 math. Real source window/unit rules remain unchanged.

Snapshot contexts copy/hash-verify normalized contacts/scans plus selected model manifest/weights/provenance, bind dataset/report/processing/protocol/timestamp identity, and require nested dependencies to be bound. Complete calculations read pinned bytes; source or active-copy change raises source_snapshot_changed and discards pending cache pointers/results. Corrupt INACTIVE copies re-pin the SAME verified source bytes into a fresh version without overwriting old files. No silent source-version retry.

Private caches use versioned JSON/Parquet, content hashes, final commit manifest and atomic pointer; publishing waits for outer snapshot verification. Keys include relevant namespace/source/t/window/coverage/candidate/feature or algorithm policy. Corrupt/missing/incomplete caches recompute; interrupted writes retain previous valid pointers. Read-only model cache keys manifest/weights, rechecks dependency/object contract and returns clones. Model deadline/window/dataset/calibration/coverage/prospective clock guards always execute on prediction, including cache hits. Public aggregate memoization is hashed and copied; no shared private predictions.

TimeMachine schema3 binds snapshot identity/establishment/event-time and ingestion_time_status=unavailable in frozen records, invalidating old active sessions. Coverage policy and separate Reveal unchanged. Source changes during actions clear active UI state. Metadata/debug counters expose no individual predictions. Actual snapshot establishment/download/mtime/StudyDay are NOT ingestion time. DatasetCatalog explicit scans and frozen HistoryWindowStudy statistical/invalidation flows retained; no measured need justified rewriting them.

## Full real parity and frozen preservation

T28/T29 baseline candidates, each feature column, scores/rank ordering, selected model probabilities, model metadata and future coverage policy reproduce (integer counts/order exact, float rtol=atol=1e-12). Schema3/source-binding fields are intentional new metadata; cases/models/probabilities unchanged. Real Copenhagen Select/Predict/Freeze/Reveal, immutable frozen JSON/hash, date invalidation and static-prospective verified_clock_required rejection passed.

T30: all38,005 candidates over4 dates and9 model/window combinations match saved per-row probabilities/past statistics/validity masks. Future outcomes separately reconciled:27,820 Known/10,185 Unknown; daily funnels, AP/ROC/Brier/LogLoss, reliability/errors/subgroups and all summary fields reproduce. Unknown never becomes0.

T31: all four actual canonical source record sets, per-pair counts, node IDs/edge sets/degrees/components match old full-concat dedup reference exactly.40 saved score files and COMPLETE rankings plus117 aggregate rows/source states/topology/hits/capture/reach reproduce. Optimized research run e9d1fce951d86ca0 writes only data/processed/performance/research/<run_id>/aggregate_export; old T31 reports/root study/old run untouched.

836 protected old files, including106 prior public/private reports, unchanged from original850-file inventory; excluded14 files are explicitly authorized workflow/performance modules. No frozen raw data/model/features/report/statistical source changed. Read-only window_verify independently passes5 statistical stages and36 saved-model full prediction equivalence plus T17 immutability.

## Tests and corrected failures

Final focused **109 passed in20.77s**:
`.venv/bin/python -m pytest -q tests/test_safe_cache.py tests/test_snapshot_consistency.py tests/test_performance_parity.py tests/test_streaming_performance.py tests/test_performance_benchmark.py tests/test_asof_inference.py tests/test_time_machine.py tests/test_time_machine_coverage.py tests/test_asof_audit.py tests/test_positive_retrieval.py tests/test_multisource_exploration.py tests/test_multisource_ui.py tests/test_time_machine_ui.py tests/test_asof_ui.py`

Final full **307 passed in29.22s**: `.venv/bin/python -m pytest -q`.
25 new tests cover exact chunk dedup (same-time different pairs/adjacent legal records), multi-window parity/boundaries, warm/miss equivalence, namespace/source/window/coverage/model changes, valid weight replacement, cached deadline/dependency checks, cloned model isolation, damaged/incomplete caches, interrupted pointer/measurement writes, mid-copy/mid-prediction source changes, deferred publication abort, corrupt inactive snapshot recovery, public same-mtime changes, unavailable ingestion provenance, immutable baseline and independent-process200,000-row synthetic RSS stress (not a real performance result).

Initial T28–T31 regression4 failed/70 passed: empty Arrow batch incorrectly rejected as mixed namespace; two legacy anti-evaluation-read tests saw pandas API used on new private feature-cache payloads; persistent cross-fixture private cache prevented an expected instrumented source read. Fixed empty-batch handling, used direct verified Arrow reads for the NEW private cache (never evaluation banks), and added per-test private cache isolation. Existing leakage assertions remained unchanged; all then passed. One new stress test initially compared differing COLUMN order; aligned reference with the original ContactSource API, preserving exact row/count checks. Warm-reference export first rejected the archive root entry src; safely allowed that directory and reran frozen source export. No frozen measurements replaced. Mid-task full304/306 passes preceded added model-version/repair tests; final307 passes above. No unresolved failure. Nonfatal sandbox PyArrow CPU-probe warnings remain.

## Deliverables, limits and publication

PERFORMANCE_AUDIT.md and exactly three reviewed reports/performance files: T32_BENCHMARK.csv, T32_PARITY.json, T32_SNAPSHOT_AUDIT.json. README/TASKS/AGENTS updated. All raw measurements, host-sensitive input paths, source/model copies, cache bundles, private pickle parity receipts, predictions/scores and UI receipts remain under ignored data/processed/performance or t32_cache. No new dependencies, data acquisition or real fitting.

Guarantee is stable TRUSTED archive consistency, not atomic live acquisition or historical ingestion chronology. An external writer can change files after final verification (TOCTOU); there is no global cross-file live transaction, adversarial same-owner immutability, atomic multi-pointer commit or power-loss durability guarantee. Orphan versions may remain after interruption; no automatic retention/cleanup policy. Full-archive source validation costs cold time; not every operation improves. These explicit limits do not weaken candidates, temporal checks, labels or metrics.

Safe code/docs/aggregate-only current-branch commit/push; remote SHA verified in execution reply/tracking state. No datasets, model weights, per-pair outputs, keys or private paths staged. No main merge. **STOP. Next:T33 — GitHub Actions 自动化测试, not started.**
