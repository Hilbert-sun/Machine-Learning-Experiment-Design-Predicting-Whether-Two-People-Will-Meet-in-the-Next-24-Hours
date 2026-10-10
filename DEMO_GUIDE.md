# Five-minute demonstration

Start with `streamlit run app.py` in the verified Python 3.11 environment. Keep individual pair details local; do not publish screenshots with participants or probabilities. No screenshots or per-sample demo files are included in this delivery.

| Time | Action | Evidence and explanation |
| --- | --- | --- |
| 0:00–0:40 | Overview, then Dataset Catalog | Predict recorded anonymous-device proximity within 24 hours. Show which lawful local sources exist and why contact-only archives cannot supply reliable negatives. |
| 0:40–1:30 | History Window Study with existing frozen default run | Show 1/3/7-day shared-cohort comparisons. Seven-day XGBoost AP 0.691366, four dates, 25,569 samples; bounded inputs and same labels make this comparison meaningful. Do not change settings/train. |
| 1:30–2:10 | Open ASOF_AUDIT.md alongside the app | T30 has no dedicated navigation page. Show 38,005 candidates, 10,185 Unknown, 27,802 prediction/label intersection. Higher AP with changed prevalence and worse Brier is not a same-population improvement. |
| 2:10–3:30 | Time Machine | With matching private saved models, select a supported historical Study Day after model deadlines, pair and 1/3/7-day windows. Predict → Freeze → Reveal. Explain historical features, frozen coverage policy, Contact/No Contact/Unknown and version invalidation. Do not enable prospective mode for an old archive. |
| 3:30–4:20 | Multi-Dataset Exploration | Show workplace fixed-rule Top-K Observed Positive Retrieval and source-specific graphs. No unobserved negatives, no binary AP/Precision; MIT tick mapping and Social Evolution remain unavailable. |
| 4:20–5:00 | GitHub Actions | Open the latest branch workflow run; verify exact commit SHA and all three jobs. Distinguish public synthetic/aggregate checks from private research reproduction. |

Public-only alternative: show reviewed [window metrics](reports/window_study/T22_METRICS.csv), [T30 audit](ASOF_AUDIT.md), [T31 study](MULTISOURCE_STUDY.md) and meaningful UI empty states. Do not present fixture probabilities as genuine results. A deliberately synthetic AppTest demonstration must be labeled synthetic fixture, never a real-data experiment.

The 12 navigation paths are in [README](README.md). Data Manager downloading and legacy training are explicit user actions, not prerequisites for public tests. No acquisition, model fit or new export should occur during this demo. For local source/model/version prerequisites and verification commands see [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
