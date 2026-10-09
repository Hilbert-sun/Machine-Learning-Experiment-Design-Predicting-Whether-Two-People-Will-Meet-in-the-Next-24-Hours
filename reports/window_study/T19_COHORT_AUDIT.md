# T19 — Shared comparison cohort

Date: 2026-10-10. Source: genuine Copenhagen, original T17 labels and processed contact/observation evidence. T17 files preserved. No model fitted.

Stable key is `(dataset_id,t,user_min,user_max)`, represented in local Parquet as `dataset_id|t|a|b`. Dataset namespace is copenhagen. Main candidates are only pairs with a contact in `[t-1d,t)`. Both windows (and the3d intermediate) share exactly the same key/label/split hashes. All samples have `t-7d >= source_start` and `t+1d <= source_end`; full calendar span does not imply continuous device observation. Future target coverage stays>=0.5 per participant, with unknown/low coverage excluded and no downsampling. Future coverage fields are prefixed and excluded from feature inputs.

## Actual filtering funnel

- all_past_candidate_rows: 1,196,828
- excluded_incomplete_7d_span: 91,413
- excluded_not_1d_candidate: 960,966
- one_day_candidates: 144,449
- excluded_coverage_or_unknown: 43,964
- eligible_rows: 100,485
- positive: 20,099
- negative: 80,386

20 eligible prediction dates remain (Study Days8–27). Purged chronological60/20/20 gives54,677 train rows/11 days (8–18),14,816 validation rows/3 days (20–22),25,569 test rows/4 days (24–27). Day19 removes4,775 rows and Day23 removes648; total5,423. Strict label end is earlier than the next set start. All sets have>=20 observations of both classes and>=2 distinct dates.

An independent early-calibration/later-threshold partition with the predeclared>=2 tuning dates cannot fit inside the3 validation dates after24h purge. Calibration is disabled for every window/model rather than sacrificing separation; raw probabilities and reliability will be reported. This is fixed before any new model test scores.

`T19_COHORT_MANIFEST.json` records every daily funnel, label/key/Parquet checksum, actual split dates and class counts. Local ignored artifacts are `data/processed/window_study/cohort-*.parquet` and matching `*-splits.parquet`, with complete keys/labels/assignments. No individual samples are published. Insufficient sources return `insufficient_days`, with a chronological forward-fold/longer-source alternative, never a random split.

Validation:25 focused cohort/temporal/label tests passed. Real cohort construction and cached replay succeeded. Main comparison remains a fixed-protocol same-source temporal study with prior T17 exposure, not a pristine independent holdout. Next:T20 bounded features; no model training in T19.
