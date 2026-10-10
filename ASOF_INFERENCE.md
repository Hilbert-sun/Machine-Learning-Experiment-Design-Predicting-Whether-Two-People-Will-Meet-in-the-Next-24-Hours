# T28 — Independent as-of-time inference

Branch: `research-v2.2`. Baseline: `820d080`. Scope: inference/data-path correction only; no real-model refit, new experiment, dataset acquisition or push.

## Correction to the earlier Case Explorer

The old `src/window_ui.py.case_keys()` opened keys from a bank whose rows had already passed **future** observation-coverage eligibility. Avoiding the target column did not remove that candidate-selection leak. T17–T27 reports, evaluation cohorts, models and statistical source remain frozen as historical evidence; their scores do not constitute evaluation of the new unfiltered inference population.

The active page now calls `src/asof_ui.py` / `src/asof_inference.py`. Old `window_ui.case_keys/predict_case` remain for frozen reproducibility only and are not called by Case Explorer. The independent explorer is available without clicking offline Run Study. Offline comparison charts and evaluation downloads retain their original data and scope.

## Interfaces

```python
from src.asof_inference import (
    as_of_candidates, as_of_features, read_model_contract,
    predict_as_of, reveal_outcome, ClockAnchor,
)

keys = as_of_candidates(processed, t, dataset_id="copenhagen")
features = as_of_features(
    processed, t, dataset_id="copenhagen", windows=(1, 3, 7),
    min_scan_coverage=0.5,
)

prediction = predict_as_of(
    processed, saved_model_directory, t, person_a, person_b,
    dataset_id="copenhagen", history_window_days=7,
    mode="historical_blind_replay", evidence_path=frozen_study_record,
)
# A distinct, explicit action; never an argument to the inference method.
outcome = reveal_outcome(processed, t, person_a, person_b, backtest=True)
```

- `processed` is the existing validated `ProcessedDataset` (canonical sorted `contacts.parquet`, deduplicated scan-bin `observations.parquet` and truthful source metadata). No evaluation cohort, label table or stored evaluation feature bank is accepted as an inference argument.
- `as_of_candidates` returns canonical `(dataset_id,t,user_min,user_max)` keys from `[t-86400,t)` contacts only. The start is inclusive; events exactly at `t` are excluded. Neither historical nor future scan quality filters this candidate function. Invalid namespaces/IDs are rejected.
- `as_of_features` generates neutral `bounded_window_v1` columns afresh through frozen `window_features.snapshot_features`. Each window clips counts, bins/days, RSSI, activity, network, recency, coverage and frequency to `[t-window,t)`. A complete selected **past** span is required; an observed future horizon is not. Unavailable observation fields stay null. Features include all historical candidates, including those omitted by the old future-coverage filter. No persistent inference cache is added.
- `predict_as_of` verifies model provenance, dataset namespace/time origin, feature/window contract and all label-information deadlines before producing a probability. Unknown/old-only pairs outside the1d candidate pool reject. Unknown/missing historical scan evidence, or no pre-t scan evidence for either endpoint, rejects. Partial positive historical coverage can be represented; it does not prove continuous device presence. The method never returns an actual outcome.
- `reveal_outcome` refuses before any data read unless `backtest=True`. It independently queries raw contacts/scans in `(t,t+86400]`; target/evaluation files are not read. An observed positive is Contact even if coverage is uncertain. A negative requires a complete horizon and sufficient **unique** observed bins for both devices. Missing/low coverage or incomplete absence is Unknown. Repeated scan rows cannot inflate negative confidence.

Errors are `InferenceError` (a `TrainingDataError`/`ValueError` subtype). Missing or unverifiable model-time provenance rejects rather than guessing an early date.

## Model-time provenance

A new producer can place the following contract in the existing registry manifest's `metadata.as_of_inference`. These are inference metadata fields, not invented source dataset columns. T28 does not rewrite any existing model manifest or train a replacement model.

```text
schema_version: 1
feature_contract: bounded_window_v1
feature_version: 1
dataset_id: canonical population namespace
history_window_days: 1 | 3 | 7
prediction_horizon_hours: 24
min_scan_coverage: feature historical-frequency observation threshold
time_origin_seconds: source normalization origin
label_information_ends:
    training_labels_end: inclusive latest information endpoint
    validation_labels_end: inclusive latest information endpoint
    threshold_labels_end: inclusive latest information endpoint
    calibration_labels_end: required when calibrated
```

Each deadline must be an integer on the same relative-second time axis. **Every** declared endpoint must be strictly earlier than `t`; equality rejects. Missing training/validation/threshold/calibration provenance rejects. Unsupported target horizons and test-informed selection without verified bounds reject. Saved artifact checksums and loaded model feature/window/calibration identity are checked.

For unchanged T21/T22/fold records, `evidence_path` binds the exact saved model path, run, parameters, fitted feature list and threshold to the recorded training/validation prediction times. Add24h to the latest label-producing time. Validation end also bounds threshold selection and, if applicable, calibration conservatively. Recorded validation-only UI jobs additionally bind model/manifest hashes and their declared selection deadline. Relative artifact paths are resolved against report ancestors, independently of process working directory. Evaluation-bank/cohort/prediction paths in these records are never opened for inference.

The supported namespace/sensor mappings are the existing Copenhagen and High School contracts; models without a verified bounded-history contract (including legacy14d banks) are rejected. Unsupported data sources need an explicit future adapter/provenance design, not anonymous-ID matching by number.

## Blind replay and genuine prospective inference

`historical_blind_replay` simulates a requested past Study Day and uses only pre-t input data. The chosen saved model must already be time-valid at that simulated moment. A model trained/selected later cannot be used to replay earlier dates. This mode needs no calendar origin and can operate when the archive ends before the target outcome horizon.

`prospective_inference` additionally requires a `ClockAnchor(origin_utc, reference)` from an independently verified upstream clock mapping relative second zero to wall time. It is not inferred from file mtime, recent downloads, Study Day labels or a UI-entered date. Current time must be timezone-aware. Prediction time must be current/recent (default600s; permitted policy1–3600s), and both endpoints need recent **pre-t** scan evidence. Time arithmetic is normalized to UTC elapsed seconds. Increasing the allowed age to years is rejected.

Current static Copenhagen/High School archives have no verified live clock anchor, so the page rejects prospective mode and labels valid historical outputs as blind replay. The API can support a trustworthy fresh feed; tests use an explicitly synthetic anchored feed. Clock/provenance authenticity remains a trusted-provider responsibility, not something a timestamp string alone can prove.

## Verification and residual risks

Offline tests use small synthetic Parquet and small temporary fitted models only. They cover future contact/observation perturbations and future-span changes; inference with all future rows removed; pre-t query bounds and no evaluation-file IO; changes beforet; inclusive/exclusive boundaries; unknown pairs; missing scans; dataset/window/time-origin/checksum conflicts; all selection deadlines (including equality); old metadata bridging; calibration/horizon rejection; real-time freshness/UTC; explicit outcome authorization and Unknown negatives; and the independent page route.

A read-only genuine Copenhagen check at Study Day24 found10,995 historical candidates, compared with7,482 old future-filtered evaluation rows:3,513 candidates were formerly omitted. An omitted pair successfully received1/3/7d probabilities from unchanged saved models, without refitting or reading an evaluation bank as model input. These are candidate/inference checks, not new performance metrics. All existing local frozen artifacts are hash-checked before/after.

This task fixes inference membership and time validity. Earlier models were still trained on future-observation-eligible evaluation populations. Selection/missingness bias, probability calibration for the expanded as-of population, archive scan proxies and short dependent study periods remain limitations. Old AP/ROC/Brier scores must not be advertised as validated for every new as-of candidate. Historical replay follows recorded event time; actual availability under delayed uploads/revisions needs separate upstream ingestion provenance. Concurrent source updates require consistent validated snapshots; the current API assumes its processed snapshot is stable during a call.

Recommended next task (not started): independently evaluate the as-of population and define auditable model/clock/source provenance for a real observation feed. No T29 or other implementation starts automatically.
