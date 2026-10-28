# Encounter Lab

[中文](README.md) | English

**Will two people come into contact within the next 24 hours?** Encounter Lab studies this question with the anonymized Bluetooth proximity records of the Copenhagen Networks Study. Predictions use only history before time t, the target is a recorded contact in (t, t+24h], leakage is guarded at every step, and a missing observation is never treated as "did not meet". The project also ships a Streamlit app with a playful questionnaire, public data stories and the full research toolkit.

[![Public CI](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/workflows/ci.yml/badge.svg?branch=research-v2.2)](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/workflows/ci.yml) [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://hjm59payrde6ronekgiqsn.streamlit.app/)

**[Try the live demo →](https://hjm59payrde6ronekgiqsn.streamlit.app/)** No installation needed for Play and Explore. The research tools need local data and run locally only.

![Rolling-origin pooled AP: XGBoost with 1/3/7-day history, and five models with 7-day history](docs/figures/rolling_ap.svg)

The figure labels are in Chinese. Top panel: 7-day XGBoost history vs. 1 and 3 days. Bottom panel, top to bottom: XGBoost + Hawkes features, XGBoost, label-free Hawkes, logistic regression and historical frequency. The dashed line is random ranking (prevalence 0.197).

**Findings (T35–T40 supplementary studies, 11 rolling test days)**

1. **Longer history predicts better.** 7 days of history beats 1 day by +0.090 AP (day-block 95% interval [0.073, 0.103]), positive on all 11 days.
2. **The signal is mostly the recent timing of contacts.** A label-free Hawkes self-exciting process with two parameters per pair reaches AP 0.629, close to XGBoost's 0.662. Adding Hawkes scores to XGBoost adds only +0.003.
3. **These findings are descriptive.** All test days had been evaluated before, the intervals describe day-to-day variation only, and there is no independent population. See [Results and their populations](#results-and-their-populations).

The figure is generated from public aggregates by [docs/figures/build_readme_figure.py](docs/figures/build_readme_figure.py).

## Quick start

Use Python 3.11 in a macOS/Linux terminal:

```sh
git clone --branch research-v2.2 https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours.git encounter-lab
cd encounter-lab
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the address the terminal prints (usually http://localhost:8501). The [live demo](https://hjm59payrde6ronekgiqsn.streamlit.app/) opens only Play, Explore and the public reports; see the [deployment guide](docs/DEPLOY.md). For a local-only preview, add `--server.address 127.0.0.1`. Native tree models on Linux need an OpenMP runtime (CI installs libgomp1); macOS may need libomp. The current version lives on the [`research-v2.2`](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/tree/research-v2.2) branch.

| What to try | Entry | Needs local data/models? |
| --- | --- | --- |
| Playful encounter index | Home → Play, seven multiple-choice questions | No |
| Personal clues and diagram | Play result → my encounter analysis | Only the questionnaire in the current session |
| Public population patterns | Explore → patterns in real data | No; reads reviewed aggregate reports in the repository |
| Historical research and models | Research directory | Matching local data, models and version evidence; empty states otherwise |

**The Play index is a fixed rule, not a real encounter probability**, and it is fully separate from the research models. The app UI is Chinese-first. Rules are in the [product plan](docs/PRODUCT_PLAN.md), Explore scope in the [Explore guide](docs/EXPLORE_GUIDE.md) and a walkthrough in the [demo guide](docs/DEMO_GUIDE.md).

## Results and their populations

All results use Copenhagen scan-coverage proxy labels: "no contact" becomes a negative only for a completely and sufficiently observed horizon; otherwise the label is Unknown and stays out of binary metrics. Populations differ between experiments, so the rows below are not directly comparable.

| Copenhagen evidence | Test population | XGBoost AP | ROC-AUC | Brier |
| --- | --- | --- | --- | --- |
| T17 sigmoid baseline | 260,170 samples, 6 dates, 10.22% positive | 0.381491 | 0.750717 | 0.077673 |
| T22 fixed cohort, 1d history | 25,569 samples, 4 dates, 21.38% positive | 0.588723 | 0.770656 | 0.128026 |
| T22 fixed cohort, 3d history | same T22 cohort | 0.627494 | 0.799719 | 0.120801 |
| T22 fixed cohort, 7d history | same T22 cohort | 0.691366 | 0.841494 | 0.109107 |
| T30 expanded, reliably labeled and predictable, 7d | 27,802 samples, same exposed 4 dates, 27.70% positive | 0.758930 | 0.854281 | 0.128114 |

- **T22**: the same candidates, labels and purged splits, changing only the history window; the 7d−1d AP difference is 0.102644. **Only four principal test dates, scan-proxy labels and no independent population validation**: no claim of significance, causation or long-term generalization. T17 uses a different cohort and a 14-day feature bank, so it is not a window comparison.
- **T30**: of 38,005 historical candidates, 27,820 have reliable labels and 10,185 are Unknown. The 12,436 added candidates contain known positives only and no known negatives, so the higher AP is **not a same-population model improvement**, and Brier is worse than T22. See the [audit evidence](docs/FINAL_RESEARCH_AUDIT.md).
- **T35–T37**: the unchanged protocol re-evaluated with rolling origins gives 11 test days (59,140 samples, 19.66% positive), shown in the figure. Per-participant NDCG@5: 7d XGBoost 0.786, Hawkes 0.784. See [rolling validation](studies/rolling_validation/README.md), [Hawkes baseline](studies/hawkes_baseline/README.md) and [Hawkes features](studies/hawkes_features/README.md).
- **T38 participant holdout**: training only on pairs within participant group A and testing on B–B pairs of people never seen in training gives XGBoost AP 0.651 (0.631–0.666 over 5 partitions), about 0.017 below the all-participant model. The gap mixes unseen people with only about a quarter of the training data. See [participant holdout](studies/participant_holdout/README.md).
- **T39 day differences**: daily AP ranges from 0.43 to 0.91 and tracks the day's prevalence and how recently candidates last met (ρ = −0.86 with mean hours since last contact). On the lowest-AP day the model still ranks 7.9× better than random. See [day analysis](studies/day_analysis/README.md).
- **T40 shorter half-lives**: extending the Hawkes grid down to 5 minutes puts the validation optimum at 15–30 minutes (inside the grid); test AP 0.626, no change from T36. See [shorter Hawkes half-lives](studies/hawkes_short/README.md).
- **T32 performance**: five separate processes per configuration on the same machine and input. MIT cold peak RSS fell 27.59%; specific Copenhagen warm feature/prediction operations got about 97.9%/95.0% faster; some cold paths became slower. See the [performance evidence](PERFORMANCE_AUDIT.md).

Other sources: Workplace supports observed-positive retrieval only and High School limited descriptive retrieval; MIT Reality Mining has unverified tick units; Social Evolution is unavailable. Identities are namespaced per source and never merged; see the [multi-source study](MULTISOURCE_STUDY.md).

## Method highlights

- Chronological train/validation/test splits with strict purging of 24-hour label windows that cross a boundary; thresholds and calibration use validation data only.
- Shared candidates, bounded 1/3/7-day features, frozen models and explicit model information deadlines.
- An independent Time Machine: Select → Predict → Freeze → Reveal; an absence that cannot be verified stays Unknown.
- Population and selection-bias audits, per-source network exploration and fixed-rule Top-K retrieval.
- Parquet/PyArrow processing, stable archive snapshots and versioned caches with output-parity checks.
- Stack: pandas, NumPy, scikit-learn, XGBoost, LightGBM, SciPy, NetworkX, Streamlit, Plotly. See the [portfolio architecture guide](docs/PORTFOLIO_GUIDE.md).

## Application pages

The app has four top-level entries, Home / Play / Explore / Research, and keeps the research pages inside the Research directory. Navigation is defined in [app.py](app.py) and [src/ui.py](src/ui.py); the full 15-page list is in the [Chinese README](README.md#应用页面). The T30 audit has no page of its own; see [ASOF_AUDIT.md](ASOF_AUDIT.md).

## Verification and reproduction

```sh
python -m pip check
python -m pytest -q
python -m src.final_audit
python tools/check_repository_safety.py
python -m tools.run_secret_scan
```

Public tests and the public audit need no data or model downloads. The public audit checks arithmetic consistency between aggregate files and that 51 frozen files match the trusted baseline; it does not recompute AP from raw data. With local Copenhagen data, `python -m src.rolling_validation --verify-only` and the `--verify-only` flag of `hawkes_baseline`, `hawkes_features`, `participant_holdout`, `day_analysis` and `hawkes_short` recompute the public aggregates from local per-sample results. CI runs three jobs: the full pytest suite, a 15-route Streamlit smoke test, and repository and secret scanning. See the [reproducibility guide](docs/REPRODUCIBILITY.md) and the [CI records](docs/CI_VERIFICATION.md).

## Limitations, sources and licenses

Coverage is a proxy, not evidence that a device was continuously online, and a missing contact is never automatically a negative. Static archives are not real-time forecasts. Snapshots keep disclosed TOCTOU and atomic-publication limits. Anonymous identifiers can still carry re-identification risk, so no individual-level exports are published. Raw data, model weights and per-sample predictions never enter Git.

Source links, citations and per-dataset licensing evidence are in the [source quality metadata](reports/multisource/T31_SOURCE_SUMMARY.json) and the [dataset catalog](reports/DATASET_CATALOG.json). Copenhagen data comes from its [official Figshare record](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433). A website's source-code license does not determine a dataset's license. The project code is released under the [GNU GPL-3.0](LICENSE) (Copyright © 2026 Hilbert-sun): you may use, modify and redistribute it, and modified versions you distribute must also be released under GPL-3.0. The license covers this repository's code and documentation only, **not third-party data**: Copenhagen, SocioPatterns and other datasets keep their own original licenses (for example CC BY-NC-SA for SocioPatterns).

## Documentation

| Document | Contents |
| --- | --- |
| [Full research report, 2nd edition (Chinese)](deliverables/v2/Encounter_Lab_Full_Report_v2.md) | 12 chapters; chapter 11 covers T35–T40. The [1st edition](deliverables/Encounter_Lab_Full_Report.md) (478a320) is kept as a historical record |
| [docs/README.md](docs/README.md) | Product delivery, Explore guide, product plan, demo, reproduction, audit, checklist, CI records, history |
| [studies/README.md](studies/README.md) | T35–T40: rolling validation, Hawkes baseline and features, participant holdout, day analysis, shorter half-lives |
| [TASKS.md](TASKS.md) · [PROGRESS.md](PROGRESS.md) · [AGENTS.md](AGENTS.md) | Task board, latest progress, session rules |
| Frozen historical snapshots | [research report](RESEARCH_REPORT.md), [window study](WINDOW_STUDY.md), [as-of contract](ASOF_INFERENCE.md), [Time Machine](TIME_MACHINE.md), [population audit](ASOF_AUDIT.md), [multi-source](MULTISOURCE_STUDY.md), [performance](PERFORMANCE_AUDIT.md), [dataset catalog](DATASET_CATALOG.md). The trusted baseline pins these to the repository root; their task states are historical |
