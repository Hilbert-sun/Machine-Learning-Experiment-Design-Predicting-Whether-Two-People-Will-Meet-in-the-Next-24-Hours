# T18 — T17 baseline freeze and audit

Date: 2026-10-10 (Asia/Kuala_Lumpur). Local baseline commit: `f116951`.
The existing T17 results, reports, raw data, labels, features and model files were read, hashed and preserved without refitting. `T18_BASELINE_MANIFEST.json` is create-only/idempotent; differing content is rejected. `python -m src.baseline_audit` verifies it against local evidence. Raw/model artifacts stay ignored. The manifest records relative paths and checksums, not sample identities.

## Reconciliation

1,196,828 original candidate rows − 427,201 low-coverage exclusions = 769,627 eligible rows. Of the excluded rows, 29,372 retain recorded positive evidence and 397,829 remain unknown; none were fabricated as negatives.

769,627 − 37,735 (Study Day 16) − 46,597 (Study Day 21) = 685,295 = 269,757 train + 155,368 validation + 260,170 test. Day16 contains 5,637 positive / 32,098 negative; Day21 contains 788 positive / 45,809 negative. Day16's inclusive target end equals validation start; Day21's equals test start. Both are removed by the existing strict `t+24h < next_start` rule. No additional unexplained loss exists between eligible rows and the three sets.

Train:15 distinct prediction days (1–15); validation:4 (17–20); test:6 (22–27). The immutable manifest enumerates all actual timestamps, calibration counts, original protocol, scores, source and model hashes. Distinct days are not necessarily statistically independent observations.

## Legacy E2 audit

Inspected `src/experiments.py`, `feature_policy.py`, `feature_engineering.py`, `model_registry.py`, `train.py`, `temporal_split.py`, and the existing Model Evaluation UI.

- E2 rebuilds the original same chronological split from exact input signatures; all windows share validation row keys and, when enabled, identical calibration/tuning partitions. E2 reports validation only, with fixed saved parameters; the UI disables E2 during test evaluation.
- `feature_window_view(days=1)` masks suffixes requiring3/7/14d, including long history-completeness flags. Network degree/neighbors and historical scan coverage are assigned a7d requirement and masked. RSSI/activity at7d are masked, not recomputed at1d/3d.
- `historical_contact_probability` is a14d feature: it is masked for1d,3d,7d. Historical Frequency therefore falls back to the train prior for these windows. This cannot serve as an informative window-specific frequency baseline.
- Last-contact recency is computed from all past records, but values older than the chosen window become null. Values within the window are correct. Calendar/relative-day features remain visible, with unverified weekday/communications null.
- Original candidate keys use **any contact before t**, including pairs visible only beyond1d or7d. Keys are not fed as numeric features, but this cohort selection uses a larger information budget. It is not a strict1d-vs7d information comparison.
- Original samples allow truncated history, indicated by completeness flags. E2 does not require a common full7d historical span. T17 keeps this original behavior as an existing baseline, not the new comparison.

## Decision and checklist

- [x] Local T17 commit and report scores verified; remote state not used as a replacement.
- [x] Official raw hashes and original statistical source hashes match the baseline commit.
- [x] Model/artifact/report paths and hashes frozen; original files preserved.
- [x] Eligible/split totals reconciled exactly, with day/class purge counts.
- [x] Existing feature isolation, candidate budget, frequency fallback and validation keys audited.
- [x] Original test suite and new freeze/audit tests pass (173 total).

T19 will use a common `[t-1d,t)` candidate pool and full7d source span, retaining the existing future coverage policy. T20 will compute bounded activity/network/RSSI/frequency/scan/recency explicitly rather than reinterpret legacy E2. No old code/model contract is changed by this audit.

Remaining risks: Copenhagen has only28 observed days; strict7d-history comparison reduces usable dates further. Symmetrized recorded bins only approximate device observation. T17 already exposed some of the new comparison's dates; report the new study as a fixed-protocol same-source temporal comparison, **not a pristine new external holdout**. No test-driven retuning will follow. No additional dataset or UI work is included.
