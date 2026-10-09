# Encounter Lab — Tasks

Task IDs and titles follow the user's task-board screenshot. Dependencies and acceptance criteria below are the implementation plan derived from `PROJECT_SPEC.md`, rather than additional completed functionality.

Current execution: **T16 — DONE**. All T01–T16 software tasks are verified; full tests, documented startup, final integration and source-only GitHub delivery succeeded. Stop; real-data research work requires a new instruction.

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

T01 excludes Streamlit navigation/pages, dataset downloads, preprocessing, features, training and predictions. These belong to later tasks.
