# Reproducibility — three distinct verification levels

## Level 1 — Public CI reproduction

Use a full clone, research-v2.2, Python 3.11. Install requirements.txt, not the macOS-specific archived lock as a Linux lock. CI installs libgomp1; macOS native trees may need libomp.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
python -m pytest -q tests/test_ui.py tests/test_time_machine_ui.py tests/test_time_machine_coverage.py tests/test_multisource_ui.py tests/test_window_ui.py
python -m src.final_audit
python tools/check_repository_safety.py
python -m tools.run_secret_scan
```

The last command obtains the pinned official Gitleaks executable if absent; it downloads software, never research data. An already verified local executable may be supplied with `--binary PATH`. Gitleaks scans reachable Git history and exact index bytes; the repository scanner separately checks frozen evidence and private formats. Full clone history supplies trusted commit 5f3be86bebe089af5dea9b671ce25fe8e0c279f0. A source ZIP or shallow checkout lacking that object cannot verify historical integrity and must fail rather than silently skip it.

Tests use synthetic fixtures, reviewed aggregates and isolated temporary paths, with live requests/urllib HTTP blocked by pytest. `ENCOUNTER_CI_PUBLIC=1` additionally checks absence of genuine datasets/models on fresh runners; do not enable it on a populated research checkout. Native XGBoost/LightGBM tests remain enabled. No private weights or real source files are supplied to CI.

Public audit outputs `public_aggregate_verified` and `not_verifiable_without_local_artifacts`. It verifies CSV/JSON metric consistency, prevalence/population arithmetic, retrieval formulas, measured performance arithmetic and frozen bytes. It never upgrades its scope merely because private directories exist, and does not rerun true Copenhagen AP or query live Actions. Current-head CI requires a separate GitHub check.

## Level 2 — Verified local research reproduction

Prerequisites: lawful original sources matching frozen source hashes; the matching preprocessed Parquet versions and split/feature banks; 36 saved window/fold models; original private predictions, labels and run manifests. These are local artifacts excluded from Git. Obtain source permission independently; no T34 dataset acquisition or model refit is part of this verification.

Verified read-only entry points:

```sh
python -m src.window_verify
python -m src.asof_audit --verify-only
```

window_verify checks five frozen stages, recomputes metrics from saved predictions, compares all 36 loaded model outputs with the saved full predictions, and checks T17/frozen source hashes. asof_audit --verify-only validates frozen prediction/export checksums and recomputes T30 funnels, groups, reliability, errors and metrics from the saved private sample table. Both fail if required artifacts differ or are missing. Neither fits models or overwrites reports. They establish saved-artifact reproducibility, not an independent new acquisition, raw-to-label reconstruction or external validation.

T34 local receipts are ignored temporary outputs; only safe aggregate outcomes enter progress. T31 source hashes and saved canonical counts can be inspected without publishing IDs. T32 public before/after arithmetic is verified by final_audit; its original five-process performance experiment is not rerun, and current-machine timing is not claimed to reproduce the original benchmark.

Do not use `src.real_experiment`, `src.research_delivery`, default `src.asof_audit` or default `src.performance_audit` as read-only audit commands: these entry points fit and/or publish outputs. Re-running them can replace frozen material. Missing prerequisites mean NOT AVAILABLE/PARTIAL, never synthetic substitution.

## Level 3 — Interactive application

```sh
streamlit run app.py
```

All 12 registered pages are listed in [README](README.md). Overview summarizes actual available local files. Data Manager requires explicit acquisition actions; Catalog explains per-source suitability. A public checkout has no genuine models/processed data and should show empty states rather than invented scores. Raw files alone do not constitute a verified processed version.

With matching saved artifacts, History Window Study reuses the default frozen run; do not alter settings or launch new experiments during final acceptance. Model manifests and source/snapshot versions must match. Legacy Prediction Lab and bounded-window Time Machine have different contracts; do not substitute one bank for another.

Time Machine uses Select → Predict → Freeze → Reveal. Select the source, Study Day/hour, anonymous pair and 1/3/7-day model windows. Predict validates dataset, bounded history, source/model versions and all label-information deadlines; Freeze seals probabilities, inputs and verified coverage policy; Reveal alone reads future outcome evidence. Missing scans produce Unknown; a trustworthy absent event requires complete sufficiently covered horizons. Context/version changes invalidate active state. No participant/pair records or screenshots are exported to Git.

Static Copenhagen archives cannot pass real-time prospective mode without a verified current clock and recent pre-t scans. Event time is distinct from data arrival; ingestion_time is unavailable. Historical replay assumes archive availability and is not a reconstruction of live upload timing.

T30 has no standalone UI tab: open [ASOF_AUDIT.md](ASOF_AUDIT.md) and [aggregate metrics](reports/asof_audit/T30_METRICS.csv); private local HTML is optional. T31 appears in Multi-Dataset Exploration, separating descriptive graphs from Observed Positive Retrieval; unrecorded pairs are Unknown, and MIT ticks are not converted to days.

Case Explorer Reveal reuses the verified Time Machine policy service: every selected model policy comes from read_model_contract, mixed policies reject before prediction/future access, and the exact verified threshold reaches Reveal. The legacy checkbox remains an explicit backtest action; the independent Time Machine retains its separate Freeze step. No evaluation bank becomes an inference candidate source. See [final audit](FINAL_RESEARCH_AUDIT.md).

For a bounded demonstration follow [DEMO_GUIDE.md](DEMO_GUIDE.md). Test harness AppTest validates navigation/state logic; it does not replace manual browser rendering checks. [Final audit](FINAL_RESEARCH_AUDIT.md) records actual verification scope and research limits.
