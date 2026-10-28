# Encounter Lab · 相遇实验室

**世界这么大，明天我们会不会刚好遇见？**

回答七个简单问题，获得0–100的趣味偶遇指数；用关键词、因素图和 A/B 线索图理解自己的填写信息，也可以查看真实研究群体的接触规律。无需注册、原始数据或模型即可使用 Play 与 Explore。**趣味指数来自固定规则，不是真实相遇概率。**

应用只有四个一级入口：**首页 Home / 玩一玩 Play / 数据分析 Explore / 科研中心 Research**。首页点击“开始偶遇预测”，提交问卷后进入完整分析；也可直接进入 Explore 的公开数据区。原有科研功能全部保留在 Research 分类目录，科研统计需主动打开。安装与一分钟操作见 [产品交付说明](PRODUCT_DELIVERY.md)。

**T01–T34 与 Product Extension P01–P03 已交付。** P03 最终提交 [`390384c`](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/commit/390384ca27b9e9e89788a6d17e5c436552d28873) 的 [GitHub Actions](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38115466252) 已核实三个必需 Job 全部成功：500项全量测试、71项 Streamlit Smoke、27项安全测试及12项原生依赖检查。该记录对应已发布的 P03；后续文档提交须通过自己的 CI。

当前产品版本位于 [`research-v2.2`](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/tree/research-v2.2)。在 GitHub 查看代码、README 或克隆时请选择这个分支。

科研部分研究未来24小时的匿名设备接近记录，比较历史窗口、模拟历史预测并审计不完整观测。设备接近是相遇的代理证据，不能预测关系或追踪实时位置。真实数据、权重及逐样本结果仅在本地，GitHub 提供代码、已审查聚合报告和公开测试。

## 快速开始

使用 Python 3.11，在 macOS/Linux 终端执行：

```sh
git clone --branch research-v2.2 https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours.git encounter-lab
cd encounter-lab
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

浏览器打开终端显示的地址，通常为 http://localhost:8501。仅在本机预览时可在启动命令后加 `--server.address 127.0.0.1`。Linux 原生树模型需要 OpenMP 运行时（CI 使用 libgomp1）；macOS 原生依赖及平台限制见下方安装说明。

| 想体验什么 | 操作入口 | 是否需要本地真实数据/模型 |
| --- | --- | --- |
| 趣味偶遇指数 | Home → Play，填写七项选择题 | 不需要 |
| 个人线索与图谱 | Play 结果 → 查看我的偶遇分析 | 只需当前会话的有效问卷 |
| 公开群体规律 | Explore → 真实数据中的相遇规律 | 不需要，使用仓库中的已审查聚合报告 |
| 历史科研与模型 | Research 分类目录 | 具体研究操作需要对应本地数据、模型及版本证据；缺失时显示空状态 |

普通用户路径：**开始偶遇预测 → 七项问卷 → 查看指数 → 查看我的偶遇分析 → 修改或重置**。科研复现路径和娱乐体验互相独立。

## Play · 趣味偶遇预测（P01）

从首页点击“开始偶遇预测”，或在全局导航选择“玩一玩 Play”。无需登录、数据集或模型；填写七项粗粒度选择题即可体验。首次访问显示一次娱乐提示，同标签页刷新在浏览器会话存储可用时不重复；问卷答案只留在服务器当前会话，刷新会清空。

输出是0–100的**固定规则趣味指数，不能当作真实偶遇概率**。五类已知历史/日常线索等权平均，不确定项不当成零分；关系类型不加权。少于三项有效线索、已约定见面、约定不明或明显矛盾时不出指数。结果提供3–5张仅引用实际填写信息的关键词卡片，支持修改与重新开始。

原 Copenhagen 模型没有用该问卷训练，也不能区分约定见面与偶遇；Play 与 Research 的结果保持独立。完整规则、刷新限制与 P02/P03 边界见 [PRODUCT_PLAN.md](PRODUCT_PLAN.md)。

## Explore · 看看偶遇分析（P02）

一级导航提供 Home / Play / Explore / Research；科研概览移至科研中心，在点击“打开科研概览”后才加载。Play 结果页点击“查看我的偶遇分析”，即可解释当前问卷的真实 Keyword、因素分值和 A/B 线索关联；没有提交问卷时不生成示例个人分数。

深色线索图使用稳定力导向布局、悬停/点击说明、A/B 焦点切换和恢复视图；触屏可使用节点说明选择器。可选共同熟人数仅画一个自述汇总节点，不改变 P01 指数，不制造个体朋友或真实社交链路。个人信息只在当前会话中处理；修改/重置问卷会使旧分析失效。

Explore 使用“我的偶遇分析 / 真实数据中的相遇规律”两个标签；无问卷时默认打开公开数据。公开群体区无需原始数据或模型：直接读取 T22 同一测试总体的窗口排序结果、T31 相对研究日接触活动及已公开邻居分组。隐私抑制/缺失不补0；MIT 未核实时间单位不画日趋势，Social Evolution 不画虚构曲线。真实科研接触网络通过独立入口访问，不混入 A/B 图谱。见 [EXPLORE_GUIDE.md](EXPLORE_GUIDE.md)。

## 前端预览 / Frontend walkthrough

前端由 Python + Streamlit 构建，图表使用 Plotly，页面导航在 [app.py](app.py) 和 [src/ui.py](src/ui.py) 中定义。无需额外构建 JavaScript 应用；后端推理与研究逻辑位于独立的 src 模块。

安装依赖后运行：

```sh
streamlit run app.py
```

打开终端显示的本地地址，默认是 http://localhost:8501。应用提供中文优先的深色界面：四个全局一级入口、Research 分类目录和15个注册页面（原12条路由 + Play + Explore + Research Hub）。窄屏导航自动换行、卡片纵向排列，不再平铺全部科研页面。

建议按以下顺序查看：

1. **Home / Research**：首页选择 Play、Explore 或科研中心；Research 目录中点击“打开科研概览”查看原有六项指标，首页和未打开概览的目录不扫描本地研究数据。
2. **History Window Study**：保留默认配置，点击 Run Study 读取并验签已有冻结结果，查看同一队列的 1/3/7 天比较。匹配的本地数据、模型和运行记录是必要条件。
3. **Time Machine**：选择历史研究日、配对及窗口，按 Select → Predict → Freeze → Reveal 操作。揭晓不足以验证无接触时显示 Unknown；静态档案不作为实时预测。
4. **Multi-Dataset Exploration**：查看各来源的描述网络与正接触检索，区分可用、历史不足、时间单位未知和不可用状态。

首次克隆没有真实数据或模型时，相关页面显示明确空状态；公共报告与测试仍可直接查看。T30 审计通过文档和聚合表呈现，没有单独的应用页面。完整操作说明见 [五分钟演示](DEMO_GUIDE.md) 和 [分级复现指南](REPRODUCIBILITY.md)。

查看前端代码时，从 app.py 的导航进入下面各页面；Time Machine 的具体交互在 [src/time_machine_ui.py](src/time_machine_ui.py)，多数据集展示在 [src/multisource_ui.py](src/multisource_ui.py)。

## Research and implemented features

Copenhagen supports the main binary experiment with scan-coverage proxy evidence. Workplace archives support observed-positive retrieval; High School supports limited descriptive retrieval. MIT Reality Mining has unverified tick units; Social Evolution remains unavailable. Identities are namespaced by source and never merged across datasets.

- Chronological train/validation/test splits with strict 24-hour label purging; validation-only thresholds and model calibration where supported.
- Shared candidates and bounded 1/3/7-day features, frozen models and explicit model information deadlines.
- Independent Time Machine: Select → Predict → Freeze → Reveal; unreliable absence remains Unknown.
- Population/selection-bias audit, source-specific network exploration and fixed-rule Top-K retrieval.
- Parquet/PyArrow processing, stable archive snapshots and versioned caches with output-parity checks.
- 12 original research routes plus independent Play, Explore and Research Hub pages, pytest, Python 3.11/Linux GitHub Actions and repository/secret scanning.

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

**T35 rolling-origin re-evaluation** (unchanged T21/T22 protocol, 11 previously exposed test days, 59,140 samples): 7d XGBoost pooled AP 0.6619 vs 1d 0.5716 (Δ+0.090, day-block 95% interval [0.073, 0.103], positive on 11/11 days) and vs 7d historical frequency 0.4762; per-participant NDCG@5 0.786. Different population from T22; descriptive of day-to-day variation, not population inference. [Rolling validation](studies/rolling_validation/README.md).

**T36 Hawkes baseline** on the same T35 folds: a label-free per-pair exponential-kernel Hawkes process reaches pooled AP 0.6285 (7d XGBoost 0.6619, Δ+0.033, interval [0.017, 0.048]; above 7d logistic 0.5907), with nearly identical per-participant NDCG@5 (0.784 vs 0.786). Every fold selected the smallest half-life in the grid. [Hawkes baseline](studies/hawkes_baseline/README.md).

T32 measured five separate processes per configuration on the same machine/input. MIT cold peak RSS fell 27.59%; specific Copenhagen warm feature/prediction operations reduced elapsed time about 97.9%/95.0%. Some cold paths became slower. Whole-page rendering and cross-OS performance were not measured. [Performance evidence](PERFORMANCE_AUDIT.md).

## Architecture and stack

Python, pandas, NumPy, scikit-learn, XGBoost and LightGBM provide preparation, baselines, model persistence and synthetic/native regression coverage. Copenhagen window results use XGBoost, logistic regression and historical frequency; LightGBM is supported but is not the reported window-study winner. NetworkX supports historical networks; Streamlit and Plotly provide the application. Parquet/PyArrow and SHA256 snapshot/cache identities preserve data contracts. [Actual module architecture](PORTFOLIO_GUIDE.md).

## Application pages

| Page | Purpose |
| --- | --- |
| [Overview](pages/0_Overview.py) | Public Home with Play/Explore/Research entries; original statistics available in Research Hub |
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
| [Chance Encounter · Play](pages/12_Chance_Encounter.py) | Session-only rule-based entertainment index and sourced keyword cards |
| [Encounter Insights · Explore](pages/13_Encounter_Insights.py) | Personal clue explanations/diagram and separate public research stories |
| [Research Hub](pages/14_Research_Hub.py) | Categorized research directory, opt-in original overview and report links |

T30 has no dedicated application page: read [ASOF_AUDIT.md](ASOF_AUDIT.md) and its public aggregate tables. Local private HTML, when present, is an additional research artifact.

## 环境与验证 / Environment and verification

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

Only four principal window-study test dates; exposed historical periods; coverage is a proxy, not continuous device-online evidence; missing contact is not automatically negative. Stable archive event time does not establish historical ingestion availability. Static archives cannot be advertised as real-time forecasts. Snapshots retain disclosed TOCTOU/atomic-publication limits and lack live ingestion transactions. Anonymous identifiers can still carry reidentification risk; no individual demo exports are published. Case Explorer now reuses the verified Time Machine policy/snapshot service; mixed policies reject before prediction or future reads. Five critical pages passed real browser visual acceptance, alongside the 15-route AppTest suite. See [final acceptance evidence](FINAL_RESEARCH_AUDIT.md).

Source links, citations and dataset-specific licensing evidence are preserved in [source quality metadata](reports/multisource/T31_SOURCE_SUMMARY.json), [dataset catalog](reports/DATASET_CATALOG.json), and [multi-source study](MULTISOURCE_STUDY.md). Copenhagen: [official Figshare record](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433). Do not infer a dataset license from website source-code licenses; MIT Social Evolution acquisition/license remain unverified. Contact-only sources cannot support reliable binary negatives. No project code LICENSE file is currently provided; do not assume permission for unrestricted redistribution. Dataset-specific licenses govern third-party data separately.

## CI、验收证据与文档索引

[![Public CI](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/workflows/ci.yml/badge.svg?branch=research-v2.2)](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/workflows/ci.yml)

Three jobs verify full public pytest, 15-route Streamlit smoke, and repository/secret safety. Synthetic fixtures and public aggregates are distinct from lawful local research reproduction. No raw data, weights, per-sample predictions, credentials or personal paths belong in Git. [已核验的研究及产品 CI 记录](CI_VERIFICATION.md)。最新维护提交仍以该 SHA 自己的 Actions 状态为准。

| 文档 | 内容 |
| --- | --- |
| [完整中文项目研究报告](deliverables/Encounter_Lab_Full_Report.md) | 11章学术报告、可追溯实验表与黑白SVG；正式PDF保留本地 |
| [产品交付说明](PRODUCT_DELIVERY.md) | 当前功能、操作路径、三档浏览器验收、图谱与隐私限制 |
| [Explore 使用指南](EXPLORE_GUIDE.md) | 个人线索、公开图表、来源口径与 Unknown 处理 |
| [产品计划与固定规则](PRODUCT_PLAN.md) | P01–P03 完成情况、字段、计分和会话行为 |
| [演示指南](DEMO_GUIDE.md) | 无私有数据的产品演示与科研五分钟路径 |
| [交付清单](FINAL_RELEASE_CHECKLIST.md) | 已完成验收及不可等同于研究泛化的边界 |
| [CI 验证记录](CI_VERIFICATION.md) | 已发布 SHA、实际 Actions、公开测试验证范围 |

- [Final research audit and task evidence index](FINAL_RESEARCH_AUDIT.md)
- [Reproducibility](REPRODUCIBILITY.md), [portfolio architecture](PORTFOLIO_GUIDE.md), [demo](DEMO_GUIDE.md), [release checklist](FINAL_RELEASE_CHECKLIST.md)
- [Tasks](TASKS.md), [latest progress](PROGRESS.md), [session instructions](AGENTS.md)
- Frozen historical snapshots: [research report](RESEARCH_REPORT.md), [window study](WINDOW_STUDY.md), [as-of contract](ASOF_INFERENCE.md), [Time Machine](TIME_MACHINE.md), [population audit](ASOF_AUDIT.md), [multi-source](MULTISOURCE_STUDY.md), [performance](PERFORMANCE_AUDIT.md). Old task-status statements in these are historical, not current status.
- [Development history](DEVELOPMENT_HISTORY.md): previous README preserved as a dated historical snapshot; its old status notes are superseded by TASKS/PROGRESS.
