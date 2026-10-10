# Encounter Lab — Research Edition 2.2

**未来24小时匿名设备接近预测与研究审计 / Auditable 24-hour device-contact prediction.**

A Python research application that asks whether a pair of anonymous devices will have a recorded proximity contact in the next 24 hours. It compares bounded historical windows, simulates historical predictions, and audits what incomplete observation lets us conclude. Device proximity is a proxy for encounters; this does not predict relationships or track live locations.

**T01–T34 已完成 / Research Edition 2.2 delivered.** T34 release commit `9f9164f` passed all three jobs in [Actions 38065140435](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38065140435): 384 full tests, 68 Streamlit smoke tests, 27 repository-safety tests and 12 native dependency checks. These are observed counts for that commit; later commits require their own CI.

本项目包含可交互的 Streamlit 科研前端：查看接触网络与数据质量、比较 1/3/7 天历史窗口，并用 Time Machine 独立完成历史预测、冻结与实际结果揭晓。真实数据和模型权重仅保存在本地，GitHub 提供代码、已审查的聚合报告和公开测试。

## Research and implemented features

Copenhagen supports the main binary experiment with scan-coverage proxy evidence. Workplace archives support observed-positive retrieval; High School supports limited descriptive retrieval. MIT Reality Mining has unverified tick units; Social Evolution remains unavailable. Identities are namespaced by source and never merged across datasets.

- Chronological train/validation/test splits with strict 24-hour label purging; validation-only thresholds and model calibration where supported.
- Shared candidates and bounded 1/3/7-day features, frozen models and explicit model information deadlines.
- Independent Time Machine: Select → Predict → Freeze → Reveal; unreliable absence remains Unknown.
- Population/selection-bias audit, source-specific network exploration and fixed-rule Top-K retrieval.
- Parquet/PyArrow processing, stable archive snapshots and versioned caches with output-parity checks.
- 12 Streamlit pages, pytest, Python 3.11/Linux GitHub Actions and repository/secret scanning.

## Genuine findings and their populations

| Copenhagen evidence | Test population | XGBoost AP | ROC-AUC | Brier |
| --- | --- | --- | --- | --- |
| T17 sigmoid baseline | 260,170 samples, 6 dates, 10.22% positive | 0.381491 | 0.750717 | 0.077673 |
| T22 fixed cohort, 1d history | 25,569 samples, 4 dates, 21.38% positive | 0.588723 | 0.770656 | 0.128026 |
| T22 fixed cohort, 3d history | same T22 cohort | 0.627494 | 0.799719 | 0.120801 |
| T22 fixed cohort, 7d history | same T22 cohort | 0.691366 | 0.841494 | 0.109107 |
| T30 expanded, reliably labeled and predictable, 7d | 27,802 samples, same exposed 4 dates, 27.70% positive | 0.758930 | 0.854281 | 0.128114 |

T22 compares the same historical candidates, labels and purged splits; only the bounded history budget changes. Its 7d−1d AP difference is 0.102644. **Only four principal test dates, scan-proxy labels and no independent population validation:** these results do not establish significance, causation or long-term generalization. T17 uses a different cohort and a 14-day feature bank, so it is not a direct window comparison.

T30 has 38,005 historical candidates: 27,820 reliable labels and 10,185 Unknown (26.80%); 37,913 candidates can be predicted, of which 27,802 have reliable labels. The added 12,436 candidates contain 10,185 Unknown and 2,251 known positives, with no known negatives. Its higher AP is **not a same-population model improvement**; Brier worsens relative to T22. Reliable-subset performance does not identify unbiased performance over all candidates. [Audit evidence and interpretation](FINAL_RESEARCH_AUDIT.md).

T32 measured five separate processes per configuration on the same machine/input. MIT cold peak RSS fell 27.59%; specific Copenhagen warm feature/prediction operations reduced elapsed time about 97.9%/95.0%. Some cold paths became slower. Whole-page rendering and cross-OS performance were not measured. [Performance evidence](PERFORMANCE_AUDIT.md).

## Architecture and stack

Python, pandas, NumPy, scikit-learn, XGBoost and LightGBM provide preparation, baselines, model persistence and synthetic/native regression coverage. Copenhagen window results use XGBoost, logistic regression and historical frequency; LightGBM is supported but is not the reported window-study winner. NetworkX supports historical networks; Streamlit and Plotly provide the application. Parquet/PyArrow and SHA256 snapshot/cache identities preserve data contracts. [Actual module architecture](PORTFOLIO_GUIDE.md).

## 前端预览 / Frontend walkthrough

前端由 Python + Streamlit 构建，图表使用 Plotly，页面导航在 [app.py](app.py) 和 [src/ui.py](src/ui.py) 中定义。无需额外构建 JavaScript 应用；后端推理与研究逻辑位于独立的 src 模块。

安装依赖后运行：

```sh
streamlit run app.py
```

打开终端显示的本地地址，默认是 http://localhost:8501。应用提供中文优先的深色界面和 12 个导航页面；窗口较窄时，其余页面收纳在顶部的 more 菜单中。

建议按以下顺序查看：

1. **Overview**：查看本地数据、匿名参与者/接触记录规模和整体分布。
2. **History Window Study**：保留默认配置，点击 Run Study 读取并验签已有冻结结果，查看同一队列的 1/3/7 天比较。匹配的本地数据、模型和运行记录是必要条件。
3. **Time Machine**：选择历史研究日、配对及窗口，按 Select → Predict → Freeze → Reveal 操作。揭晓不足以验证无接触时显示 Unknown；静态档案不作为实时预测。
4. **Multi-Dataset Exploration**：查看各来源的描述网络与正接触检索，区分可用、历史不足、时间单位未知和不可用状态。

首次克隆没有真实数据或模型时，相关页面显示明确空状态；公共报告与测试仍可直接查看。T30 审计通过文档和聚合表呈现，没有单独的应用页面。完整操作说明见 [五分钟演示](DEMO_GUIDE.md) 和 [分级复现指南](REPRODUCIBILITY.md)。

查看前端代码时，从 app.py 的导航进入下面各页面；Time Machine 的具体交互在 [src/time_machine_ui.py](src/time_machine_ui.py)，多数据集展示在 [src/multisource_ui.py](src/multisource_ui.py)。

## Application pages

| Page | Purpose |
| --- | --- |
| [Overview](pages/0_Overview.py) | Available local artifacts and project overview |
| [Data Manager](pages/1_Data_Manager.py) | Explicit download, validation and preprocessing |
| [Data Explorer](pages/2_Data_Explorer.py) | Contact distributions |
| [Encounter Network](pages/3_Encounter_Network.py) | Historical network visualization |
| [Model Training](pages/4_Model_Training.py) | Explicit legacy training workflows |
| [Prediction Lab](pages/5_Prediction_Lab.py) | Legacy saved-model prediction |
| [Model Evaluation](pages/6_Model_Evaluation.py) | Saved evaluation and calibration |
| [Data Sources](pages/7_Data_Sources.py) | Provenance and source limitations |
| [History Window Study](pages/8_History_Window_Study.py) | Frozen bounded-window comparisons |
| [Dataset Catalog](pages/9_Dataset_Catalog.py) | Source quality and availability |
| [Time Machine](pages/10_Time_Machine.py) | Independent historical prediction and reveal |
| [Multi-Dataset Exploration](pages/11_Multi_Dataset_Exploration.py) | Descriptive topology and positive retrieval |

T30 has no dedicated application page: read [ASOF_AUDIT.md](ASOF_AUDIT.md) and its public aggregate tables. Local private HTML, when present, is an additional research artifact.

## Install, test and run

Use Python 3.11 and a full Git clone on branch `research-v2.2` so the trusted frozen baseline is available. Linux native tree libraries require an OpenMP runtime (CI uses libgomp1); macOS may require libomp. The archived requirements-lock.txt describes a macOS ARM64 environment, not a Linux lock.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
python -m src.final_audit
python tools/check_repository_safety.py
python -m tools.run_secret_scan
streamlit run app.py
```

No dataset or model download is needed for public tests or the public audit. The default public audit checks aggregate equations and 51 frozen files against the trusted T32 commit; it does not recompute genuine Copenhagen AP from raw data. Data/models are excluded from Git; missing local artifacts yield informative empty states. [Three reproduction levels](REPRODUCIBILITY.md), [five-minute demo](DEMO_GUIDE.md).

## Research limitations, sources and licenses

Only four principal window-study test dates; exposed historical periods; coverage is a proxy, not continuous device-online evidence; missing contact is not automatically negative. Stable archive event time does not establish historical ingestion availability. Static archives cannot be advertised as real-time forecasts. Snapshots retain disclosed TOCTOU/atomic-publication limits and lack live ingestion transactions. Anonymous identifiers can still carry reidentification risk; no individual demo exports are published. Case Explorer now reuses the verified Time Machine policy/snapshot service; mixed policies reject before prediction or future reads. Five critical pages passed real browser visual acceptance, alongside the 12-page AppTest suite. See [final acceptance evidence](FINAL_RESEARCH_AUDIT.md).

Source links, citations and dataset-specific licensing evidence are preserved in [source quality metadata](reports/multisource/T31_SOURCE_SUMMARY.json), [dataset catalog](reports/DATASET_CATALOG.json), and [multi-source study](MULTISOURCE_STUDY.md). Copenhagen: [official Figshare record](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433). Do not infer a dataset license from website source-code licenses; MIT Social Evolution acquisition/license remain unverified. Contact-only sources cannot support reliable binary negatives. No project code LICENSE file is currently provided; do not assume permission for unrestricted redistribution. Dataset-specific licenses govern third-party data separately.

## CI, safety and document index

[![Public CI](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/workflows/ci.yml/badge.svg?branch=research-v2.2)](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/workflows/ci.yml)

Three jobs verify full public pytest, 12-page Streamlit smoke, and repository/secret safety. Synthetic fixtures and public aggregates are distinct from lawful local research reproduction. No raw data, weights, per-sample predictions, credentials or personal paths belong in Git. [Verified historical T33 CI record and current-head gate](CI_VERIFICATION.md).

- [Final research audit and task evidence index](FINAL_RESEARCH_AUDIT.md)
- [Reproducibility](REPRODUCIBILITY.md), [portfolio architecture](PORTFOLIO_GUIDE.md), [demo](DEMO_GUIDE.md), [release checklist](FINAL_RELEASE_CHECKLIST.md)
- [Tasks](TASKS.md), [latest progress](PROGRESS.md), [session instructions](AGENTS.md)
- Frozen historical snapshots: [research report](RESEARCH_REPORT.md), [window study](WINDOW_STUDY.md), [as-of contract](ASOF_INFERENCE.md), [Time Machine](TIME_MACHINE.md), [population audit](ASOF_AUDIT.md), [multi-source](MULTISOURCE_STUDY.md), [performance](PERFORMANCE_AUDIT.md). Old task-status statements in these are historical, not current status.
- [Development history](DEVELOPMENT_HISTORY.md): previous README preserved as a dated historical snapshot; its old status notes are superseded by TASKS/PROGRESS.
