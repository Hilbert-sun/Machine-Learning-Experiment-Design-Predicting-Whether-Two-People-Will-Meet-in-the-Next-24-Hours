# T17 — Real Data Diagnostics

Task date: 2026-10-09 (Asia/Kuala_Lumpur). Counts are computed from genuine local files, not synthetic fixtures.

## Local inventory and acquisition

Initially, local Copenhagen contained only calls/SMS, READMEs and the notebook; the Bluetooth main file was absent. The earlier 8 KB probe is not a training dataset. After diagnostics began, the user explicitly authorized the official complete file download.

Official source: [Copenhagen Figshare article 7267433](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433), DOI 10.6084/m9.figshare.7267433. The API returned bt_symmetric.csv; downloaded bytes and MD5 were checked before parsing. Raw data remain excluded from Git.

| Dataset | Local project-relative path | Bytes | Valid observed IDs | IDs with study contacts | Valid contact records |
| --- | --- | --- | --- | --- | --- |
| SocioPatterns | data/raw/sociopatterns/HighSchool2013_proximity_net.csv.gz | 653252 | 327 | 327 | 188508 |
| Copenhagen | data/raw/copenhagen/bt_symmetric.csv | 98257835 | 706 | 692 | 2426279 |

Copenhagen official MD5: `98892459f73e774cf79e7977edfeee3e`; verified size: 98,257,835 bytes.

Local Copenhagen communication files are genuine but are not physical-contact labels:

| Path | Records | IDs | Communication pairs | Min relative seconds | Max relative seconds |
| --- | --- | --- | --- | --- | --- |
| data/raw/copenhagen/calls.csv | 3600 | 536 | 621 | 184 | 2416399 |
| data/raw/copenhagen/sms.csv | 24333 | 568 | 697 | 18 | 2418982 |

## SocioPatterns

- SHA-256: `ecf4a90312c8d72057f72e936c366b470e63876da7db846300044795f045e2ea`.
- Source timestamp range: [1385982020, 1386345580]; basis: unix_seconds. Relative range: [39620, 403180]; recorded origin: 1385942400.
- Observation span: 363,560 seconds (4.207870 days), touching 5 Study Days. No calendar dates are invented.
- Raw rows: 188,508; valid contact records: 188,508; nonparticipant/sentinel contact rows excluded: 0; self/duplicate rows: 0/0.
- Empty-scan rows: 0; external-device rows: 0. These are retained as observation evidence, not mislabeled study contacts.
- Full-period observed pairs: 5,818 (descriptive only). Actual historical candidates appearing in prediction rows: 4,602; the future-only pairs are not backfilled into candidates.
- Complete scheduled snapshots: 3; nonempty candidate snapshots: 3; candidate sample rows: 10,742.
- Positive labels, including ineligible observed positives: 4,023; negative labels: 0; unknown labels: 6,719.
- After coverage filtering: 0 samples, 0 positive / 0 negative.

| Set after purge | Samples | Positive | Negative | Prediction times |
| --- | --- | --- | --- | --- |
| train | 0 | unknown | unknown | unknown |
| validation | 0 | unknown | unknown | unknown |
| test | 0 | unknown | unknown | unknown |

Exclusion reasons: `{"scan_coverage_unknown": 10742}`.

Historical candidate counts at each prediction timestamp:

| Relative prediction seconds | Past-only candidate pairs |
| --- | --- |
| 115200 | 2329 |
| 201600 | 3811 |
| 288000 | 4602 |

Split blocker: No eligible rows.

Timeline-only counterfactuals, ignoring coverage without creating or training on fabricated negatives:

| Snapshot interval hours | Complete times | Purged train times | Purged validation times | Test times |
| --- | --- | --- | --- | --- |
| 24 | 3 | 0 | 0 | 1 |
| 6 | 13 | 3 | 0 | 3 |
| 1 | 76 | 21 | 0 | 16 |

## Copenhagen

- SHA-256: `1c620f0f0f25d59730dc3427b051d5ab9e7c0b70173d9f92c04cf7c2d8b97e44`.
- Source timestamp range: [0, 2418900]; basis: relative_seconds. Relative range: [0, 2418900]; recorded origin: 0.
- Observation span: 2,418,900 seconds (27.996528 days), touching 28 Study Days. No calendar dates are invented.
- Raw rows: 5,474,289; valid contact records: 2,426,279; nonparticipant/sentinel contact rows excluded: 3,048,010; self/duplicate rows: 0/0.
- Empty-scan rows: 2,220,136; external-device rows: 827,874. These are retained as observation evidence, not mislabeled study contacts.
- Full-period observed pairs: 79,530 (descriptive only). Actual historical candidates appearing in prediction rows: 77,172; the future-only pairs are not backfilled into candidates.
- Complete scheduled snapshots: 27; nonempty candidate snapshots: 27; candidate sample rows: 1,196,828.
- Positive labels, including ineligible observed positives: 111,299; negative labels: 687,700; unknown labels: 397,829.
- After coverage filtering: 769,627 samples, 81,927 positive / 687,700 negative.

| Set after purge | Samples | Positive | Negative | Prediction times |
| --- | --- | --- | --- | --- |
| train | 269757 | 30619 | 239138 | 15 |
| validation | 155368 | 18289 | 137079 | 4 |
| test | 260170 | 26594 | 233576 | 6 |

Exclusion reasons: `{"eligible": 769627, "low_scan_coverage": 427201}`.

Historical candidate counts at each prediction timestamp:

| Relative prediction seconds | Past-only candidate pairs |
| --- | --- |
| 28800 | 233 |
| 115200 | 923 |
| 201600 | 9215 |
| 288000 | 13911 |
| 374400 | 18716 |
| 460800 | 22618 |
| 547200 | 25797 |
| 633600 | 26372 |
| 720000 | 26726 |
| 806400 | 31386 |
| 892800 | 35847 |
| 979200 | 40288 |
| 1065600 | 45885 |
| 1152000 | 52542 |
| 1238400 | 52773 |
| 1324800 | 52936 |
| 1411200 | 55948 |
| 1497600 | 59125 |
| 1584000 | 60855 |
| 1670400 | 65487 |
| 1756800 | 67485 |
| 1843200 | 67927 |
| 1929600 | 68054 |
| 2016000 | 70898 |
| 2102400 | 72819 |
| 2188800 | 74890 |
| 2275200 | 77172 |

Coverage sensitivity below is counts-only. No models/test-score searches were run to select these thresholds; the original0.5 remains fixed:

| Threshold | Eligible samples | Positive | Negative |
| --- | --- | --- | --- |
| 0.25 | 951999 | 101445 | 850554 |
| 0.5 | 769627 | 81927 | 687700 |
| 0.75 | 474131 | 49903 | 424228 |

## Exact diagnosis and minimal resolution

1. The existing zero-sample result was dataset/policy specific: SocioPatterns supplies positive contacts without independent scan logs, so this code correctly retains unknown absence rather than inventing negative labels. Lowering a numerical coverage threshold cannot create those logs.
2. Separately, its 4.21-day span yields only three daily complete 24h snapshots. Even ignoring coverage, strict chronological label-window purging removes train and validation. Six-hour/hourly snapshots leave validation empty under the original 60/20/20 allocation; they do not create more independent days.
3. Changing the target to no recorded contact, using contact activity as proof of online coverage, or compressing test/calibration boundaries could change the estimand or manufacture a nominal split. These were not used to force metrics.
4. Minimal scientifically defensible resolution: acquire the intended genuine 28-day Copenhagen source with the user's explicit authorization. Keep daily 08:00,24h horizon, Known Pair candidates, coverage 0.5,1/3/7/14-day features, chronological60/20/20 and strict purging unchanged. The resulting cohort supports all requested models.
5. First-history windows may be shorter than14 days; existing completeness flags/missing values remain. No future candidate enumeration, negative downsampling, fake weekdays or unverified communication features were introduced.
6. Engineering-only change: vectorized chunk aggregation scales to 2.43 million contact rows without changing counts/bins/days/RSSI definitions; small-row-group parity and no-future tests verify equivalence.

## Measurement limitations

Coverage is recorded reporter-bin availability, including empty/external scans and symmetrized data rows, not independent proof of continuous device online status. With 50% coverage, absence can still reflect missed detection. The target is a recorded valid study-device Bluetooth proximity event under the declared coverage assumption, not verified human conversation.
Four positive-RSSI contact rows exist in the genuine file and were retained under the original no-RSSI-threshold protocol; no post-test outlier deletion was performed. Contact records are measurements, not continuous encounters.
Sources: [SocioPatterns official dataset/CC BY-NC-SA](https://sociopatterns.org/datasets/high-school-contact-and-friendship-networks/) (Mastrandrea, Fournet, Barrat 2015); Copenhagen dataset authors Sapiezynski, Stopczynski, Lassen, Lehmann 2019, Figshare MIT data license. Raw files and individual pair rows are not committed.
