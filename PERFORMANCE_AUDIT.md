# T32 — Performance, Safe Caching & Snapshot Audit

Actual local measurements on the same machine and identical hash-bound real inputs;5 independent processes per operation/cache state. Cold means empty APPLICATION cache, not forced cold OS pages. Wall time excludes imports/setup; RSS includes interpreter/imports and native allocations (resource.ru_maxrss, not tracemalloc). Warm RSS includes priming. CPU Apple M5, physical memory16GiB. Baseline available-memory proxy(free+inactive+speculative pages)=3124461568 bytes, not guaranteed allocatable RAM. OS cache and other desktop activity are uncontrolled; ranges expose variation. Warm reference executes exported immutable T31 commit5c74553 code; initial cold baseline was frozen BEFORE performance edits. Intermediate optimized/optimized_v2 runs are diagnostic only; final comparisons use optimized_release.

| Operation | Cache | Before seconds | After seconds | Before RSS MiB | After RSS MiB | Time reduction % | RSS reduction % |
| --- | --- | --- | --- | --- | --- | --- | --- |
|network:highschool2013|cold|0.085883|0.089425|299.02|323.08|-4.12|-8.05|
|network:reality_mining_mendeley|cold|0.088080|0.080918|439.69|318.36|8.13|27.59|
|network:workplace2015|cold|0.041433|0.040672|274.97|287.98|1.84|-4.73|
|network:workplace2013|cold|0.009195|0.008963|258.52|259.75|2.52|-0.48|
|retrieval:workplace2013|cold|0.014816|0.021063|260.78|261.67|-42.16|-0.34|
|retrieval:workplace2015|cold|0.037182|0.049818|270.09|277.27|-33.98|-2.66|
|candidates|cold|0.009567|0.026207|268.02|267.81|-173.91|0.08|
|features|cold|0.768109|0.839252|398.16|427.62|-9.26|-7.40|
|predict_models|cold|0.826240|0.884102|406.52|433.77|-7.00|-6.70|
|model_load|cold|0.019047|0.027962|257.84|260.27|-46.80|-0.94|
|page_prepare|cold|0.021182|0.039876|268.41|268.05|-88.25|0.13|
|public_reports|cold|0.002008|0.003161|251.84|252.05|-57.40|-0.08|
|network:highschool2013|warm|0.082954|0.081763|305.58|328.72|1.44|-7.57|
|network:reality_mining_mendeley|warm|0.071231|0.073426|477.36|323.19|-3.08|32.30|
|network:workplace2015|warm|0.040576|0.034179|280.47|291.12|15.77|-3.80|
|network:workplace2013|warm|0.007844|0.006551|259.38|260.94|16.48|-0.60|
|retrieval:workplace2013|warm|0.012799|0.003822|262.08|261.91|70.13|0.07|
|retrieval:workplace2015|warm|0.034355|0.005068|273.98|277.52|85.25|-1.29|
|candidates|warm|0.007872|0.009950|270.56|267.94|-26.40|0.97|
|features|warm|0.767504|0.015926|410.03|435.27|97.92|-6.15|
|predict_models|warm|0.782652|0.039108|418.62|424.53|95.00|-1.41|
|model_load|warm|0.009808|0.011404|257.92|260.31|-16.28|-0.93|
|page_prepare|warm|0.021270|0.023280|270.55|268.23|-9.45|0.85|
|public_reports|warm|0.001174|0.000836|251.83|252.17|28.84|-0.14|

Performance target achieved on cold paths: network:reality_mining_mendeley. Negative reductions are regressions, not gains. Cold feature/retrieval/candidate requests now pay for cryptographic source binding, verified copied snapshots, private bundle validation/publication and model isolation; >10% regressions are explicit security exceptions, not hidden or compared with warm hits. Attribution to additional checks is an inference from code, not a separately timed stage decomposition. Very short operations have large relative noise; no cross-machine or significance claim. Raw5-repeat records, source hashes/input sizes, CPU/memory receipt and immutable baseline digest remain in ignored data/processed/performance.

Optimized modules: ContactSource incremental canonical dedup and streaming graph aggregation; Arrow readahead bounded to1; bounded_history reuses pre-t raw scans but frozen T20 math remains unchanged for independent1/3/7d budgets. As-of candidate/features use content-version private cache; Time Machine primes multi-window inputs once but verifies every model/time/coverage/clock contract on every prediction. Model clones prevent caller/session mutation. Only aggregate public JSON/CSV parsing is memoized process-wide with content hashes. DatasetCatalog already scans only on explicit action; HistoryWindowStudy statistical/evaluation and broad invalidation logic remain unchanged because no measured reason justified rewriting frozen study paths. Small JSON metadata parsing reuses exact bytes. Cache debug counters and explicit unavailable ingestion status appear in Time Machine.

Parquet counts are logical physical source opens through chunk IO/pandas Parquet reads; virtual bounded-history slices are not additional physical scans. Private SafeCache Arrow payload verification reads are counted separately in after_private_payload_reads. materialized_rows reports rows yielded by physical Parquet source scans, not JSON/CSV rows, opaque full-file hash reads, disk bytes or all row-group decoding. Input rows/bytes are complete normalized-source inventory (or public aggregate inventory), not actual filtered workload or physical IO bytes; model-load rows describe its associated dataset, not rows fed to an estimator. Page preparation measures saved-model discovery, processed-source selection and candidate preparation; full Streamlit rendering/context hashing is tested for correctness, not a measured whole-page speedup. Final CSV includes filtered materialized rows, repeats/ranges, hits/misses and exceptions.

Cache keys bind object type, namespace, relevant content hashes, source/version/start/origin/coverage availability, t, windows, candidate policy and feature/algorithm version. Feature keys omit unrelated model settings; model load keys bind manifest/weight bytes, with dependency/object checks preserved. No probabilities are cached. Future byte edits may invalidate caches conservatively, but candidate/features/probabilities are verified invariant. Corrupt/incomplete payloads are not accepted; valid old pointers survive interrupted writes. Corrupted inactive pinned copies are re-established from the same verified live source hashes in a fresh version, without replacing any copy already in use. Snapshot objects bind all needed source/model/evidence files and report/protocol identity. Inputs are verified copied read-only archives, not size/mtime snapshots. Pending feature/ranking cache publication is delayed until outer source/copy verification; changes raise source_snapshot_changed and clear active UI state.

Guarantee limits: read-only copies plus byte checks require stable trusted archive files, not adversarial same-owner mutation protection or an atomic live feed. Source/check/publication TOCTOU remains after final verification; no cross-file atomic acquisition, cross-process transaction, atomic multi-pointer commit or power-loss durability is claimed. Orphan content versions may persist after crashes; no automatic cleanup or retention policy. event_time comes from recorded events; ingestion_time_status=unavailable. Download time, mtime, snapshot establishment and Study Day are never ingestion evidence. T28 prospective clock/freshness guards remain mandatory. Reveal remains independent and coverage policies unchanged. Prediction schema3 invalidates old active sessions; frozen historical cases/probabilities are unchanged.

Real parity: 38005 T30 candidates/4 dates/9 model-window combinations, all per-row probabilities and Known/Unknown/funnels/metrics checked against unchanged frozen samples; T31 40 score files and complete rankings, all117 aggregates, topology/availability states match. Optimized full research reproduction writes ONLY a new data/processed/performance/research/<run_id> directory, never frozen T31 files. All protected report/data/model hashes unchanged; exact count/order checks and1e-12 float tolerance. Full evidence in T32_PARITY.json.

Reproduction (matching lawful LOCAL sources/models required; no download/refit):

```bash
.venv/bin/python -m src.performance_benchmark --stage NEW_STAGE --repeats 5
.venv/bin/python -m src.performance_benchmark --stage NEW_STAGE --cache-mode warm --repeats 5
.venv/bin/python -m src.performance_audit
.venv/bin/python -m pytest -q
```

Existing baseline/measurement stage files refuse overwrite; explicit new names preserve prior receipts. Only three reviewed performance aggregates and this report enter Git. Raw inputs, model copies, caches, pickle parity receipts, predictions and pair scores remain ignored. T33/T34 not started.

Measurement environment (no home paths):

```json
{
  "python": "3.11.15",
  "system": "macOS-26.5.2-arm64-arm-64bit",
  "machine": "arm64",
  "cpu": "Apple M5",
  "cpu_count": 10,
  "physical_memory_bytes": 17179869184,
  "available_memory": "vm_stat recorded separately; OS dynamic, not assumed from physical capacity",
  "libraries": {
    "pandas": "2.3.3",
    "numpy": "2.4.6",
    "pyarrow": "23.0.1",
    "networkx": "3.6.1",
    "scikit-learn": "1.9.1",
    "xgboost": "3.2.0",
    "streamlit": "1.65.0"
  }
}
```

Final verification: **109 focused tests passed in20.77s;307 full tests passed in29.22s** (25 new T32 tests).36 saved models across5 frozen statistical stages reproduce full probabilities/metrics. Real Copenhagen Time Machine Select/Predict/Freeze/Reveal, immutable freeze, date invalidation and static-prospective clock rejection pass. All836 protected files/106 prior reports retain their original hashes.
