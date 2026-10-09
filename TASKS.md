# Encounter Lab — Tasks

Task IDs and titles follow the user's task-board screenshot. Dependencies and acceptance criteria below are the implementation plan derived from `PROJECT_SPEC.md`, rather than additional completed functionality.

Current execution: **T18–T22 — DONE**. All five requested Research Edition tasks verified on real Copenhagen data; stop here. Next recommended task: T23, not started. T17 remains frozen; no push.

| Complete | ID | Task | Status | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| [x] | T01 | 初始化项目和依赖 | DONE | None | Project directories, Python 3.11 virtual environment, dependency manifest, default configuration, ignore rules and setup documentation exist; all declared dependencies import successfully; focused environment tests pass. |
| [x] | T02 | 搭建 Streamlit UI 框架 | DONE | T01 | App opens with Chinese-first navigation to all eight specified views, including Data Sources; empty states show no fabricated data; all pages load without ImportError. |
| [x] | T03 | 实现数据集下载器 | DONE | T01, T02 | Figshare metadata supplies real download URLs; streaming, progress, timeout/retry, local-file checks and available size/checksum checks work; manual recovery and SocioPatterns download are supported. |
| [x] | T04 | 实现数据读取与验证 | DONE | T03 | Real source schemas and delimiters are verified; Copenhagen relative time, special IDs and SocioPatterns field counts are handled; focused schema tests pass. |
| [x] | T05 | 数据清洗和统一格式 | DONE | T04 | Valid undirected pairs and self/invalid-ID filtering work; meaningful simultaneous events are retained; missingness and coverage are tracked; pair symmetry tests pass. |
| [x] | T06 | 数据探索与可视化 | DONE | T02, T05 | Real-data time, participant and pair filters drive Plotly distributions, activity trends and coverage charts with labeled scope. |
| [x] | T07 | 生成24小时预测标签 | DONE | T05 | Daily 08:00 snapshots use (t, t + 24h] labels; candidates use history only; low-coverage outcomes remain unknown/excluded; boundary and missingness tests pass. |
| [x] | T08 | 历史特征工程 | DONE | T07 | 1/3/7/14-day features and network statistics use only available past data; Parquet cache works; communication features default off if availability is uncertain. |
| [x] | T09 | 时间切分与泄漏测试 | DONE | T08 | Chronological 60/20/20 split purges label windows crossing boundaries; candidate, feature and split leakage tests pass; no random split. |
| [x] | T10 | 基础预测模型 Baselines | DONE | T09 | B0–B4 run through a shared ModelRegistry interface and report real validation metrics; thresholds use validation data. |
| [x] | T11 | XGBoost / LightGBM | DONE | T10 | Both main models train and predict probabilities using the chronological pipeline; training configuration and real metrics are recorded. |
| [x] | T12 | 概率校准与模型保存 | DONE | T11 | Validation-only calibration compares Brier Score, Log Loss and reliability; save/load preserves predictions for a baseline and main model. |
| [x] | T13 | 相遇关系网络可视化 | DONE | T02, T08 | Historical-window network supports ID search, activity/frequency sizing, node statistics and Top-N limits without future events. |
| [x] | T14 | Prediction Lab 交互页面 | DONE | T12, T13 | Pair/time/window/model controls return real model probabilities; history and uncertainty are explained; backtest outcomes respect unknown coverage; future mode hides labels. |
| [x] | T15 | 模型评估和实验比较 | DONE | T06, T12, T14 | Real baseline/model metrics, PR/ROC/confusion/calibration, feature/SHAP analysis and E1–E5 experiments are reproducible and exportable as CSV/HTML. |
| [x] | T16 | 整体测试、文档和最终交付 | DONE | T03–T15 | Applicable specification tests A–H and full pytest suite pass; README steps work; data provenance/licenses, limitations and reproducibility metadata are documented. |
| [x] | T17 | Real Data Training & Feasibility Verification | DONE | T16 | Diagnose local files, candidates, labels, coverage and temporal splits; justify/test minimal feasible changes; train genuine baselines and XGBoost only with meaningful chronological cohorts; save requested reports, aggregate metrics and local models; commit safe code/docs/metadata only. |
| [x] | T18 | T17 基准冻结与审计 | DONE | T17 | Immutable hash manifest verifies T17 data/config/models/reports, reconciles 84,332 purged rows and audits E2 information budget; original tests pass. |
| [x] | T19 | 比较样本与真实信息预算 | DONE | T18 | Common dataset/time/pair keys with strict 1d candidates, complete 7d history, coverage labels and shared purged chronological splits; Parquet/JSON hashes and day counts. |
| [x] | T20 | 窗口隔离与特征计算 | DONE | T19 | Explicit bounded 1/3/7d features and source/window/cohort/version caches; old/future perturbation and cache recovery tests pass. |
| [x] | T21 | 1d vs 7d 主实验 | DONE | T20 | Fixed XGBoost/frequency/logistic protocol and shared frozen cohort, validation-only thresholds/calibration; actual predictions and CSV/JSON/HTML reproduce scores. |
| [x] | T22 | 3d 中间窗口与时间鲁棒性 | DONE | T21 | 3d comparison, feasible forward folds, paired day-block differences, frequency/coverage/day sensitivity and separate 7d-pool reach report. |
| [ ] | T23 | History Window Study UI | TODO | T22 | Real backend-driven setup/audit/comparison/case explorer, downloads and AppTest; meaningful empty states. |
| [ ] | T24 | Dataset Catalog 与接入门槛 | TODO | T23 | Source adapters/catalog, licenses/schema/coverage/history manifests and evidence-based eligibility. |
| [ ] | T25 | MIT Reality Mining 接入 | TODO | T24 | Verify legal source/schema/coverage; exploratory-only unless reliable negative observation evidence. |
| [ ] | T26 | 其他数据适配与合法性验证 | TODO | T24 | Verify Social Evolution/workplace source access, reading/quality, independent per-source eligibility without fabricated negatives. |
| [ ] | T27 | 研究交付与最终验证 | TODO | T25, T26 | Research/window/catalog reports, reproducible outputs and full tests; reviewed Git changes, no unauthorized push. |

T01 excludes Streamlit navigation/pages, dataset downloads, preprocessing, features, training and predictions. These belong to later tasks.
