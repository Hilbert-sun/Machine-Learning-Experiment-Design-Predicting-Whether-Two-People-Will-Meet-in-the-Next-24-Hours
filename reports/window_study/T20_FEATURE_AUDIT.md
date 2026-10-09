# T20 — Explicit bounded-history features

Date: 2026-10-10. Genuine Copenhagen common T19 cohort; no new model fitted and no old T17 source changed.

`build_window_features(history_window_days=1/3/7)` reads only common keys and historical contact/observation Parquet batches. Each computation clips **every** pair count/bin/day, activity, RSSI, network degree/common-neighbor, scan coverage, historical probability and last-contact record to `[t-window,t)`. Same neutral feature names are used for all windows; no3d/7d/14d legacy column, old-pair flag, communication, unverified weekday or target eligibility enters inputs. Missing source/RSSI/coverage remains null; known no-contact counts remain zero.

Historical frequency uses contact-positive rolling24h buckets divided by sufficiently observed buckets in the chosen window, null if denominator zero. Buckets are anchored backwards from prediction t; coverage threshold stays0.5. Candidate inclusion still depends only on the shared1d pool. This makes the1d frequency rule degenerate toward1 where historical coverage is adequate: it conditions on already having a recorded previous-day contact. This is disclosed, not hidden or repaired from test results.

Caching identity includes SHA256 contact/observation content, history length, feature version1, cohort version1, key hash and coverage policy. Per-snapshot Arrow/Parquet chunks support restarting after an interrupted final file; publication uses the existing atomic cache helper. No raw data is loaded wholesale for features. No labels or future coverage columns are read.

Actual outputs:100,485 rows for each of1d/3d/7d, with identical common keys. Local ignored bank receipt: `data/features/window_study/T20_FEATURES.json`.

- 1d: `data/features/window_study/bounded-1d-8629349a905aa978dc76.parquet`; SHA256 `e375a17e0f12ab3a9f802a27bcee7f5f086494e97f10c3cd2c63387dfc730ee4`.
- 3d: `data/features/window_study/bounded-3d-a8e39dbf2c43fb72897f.parquet`; SHA256 `27c78747b919b05b5315cd9704ad20a1598de96b90374ebe76e8fd34488ecffa`.
- 7d: `data/features/window_study/bounded-7d-c7f43018d1ec36ffba9d.parquet`; SHA256 `e138e1c155f16d0c7a73d0c89cda800762ebb3b87a06d198df06077ea32e75f5`.

Verification:14 feature/cohort tests passed in1.30s. Tests add t-5d contacts:1d/3d unchanged,7d pair/network features change; t-10d contacts:all three unchanged; t/future contacts:all unchanged. Missing final cache reuses completed snapshot chunks; modified target/coverage fields do not change features. Unknown scans remain null. Actual3 real feature banks completed; T17 frozen hash verification passes. Next:T21 fixed1d-vs7d models and prediction exports.
