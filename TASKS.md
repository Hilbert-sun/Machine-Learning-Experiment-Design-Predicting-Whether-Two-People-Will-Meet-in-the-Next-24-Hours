# Encounter Lab — Tasks

Task IDs and titles follow the user's task-board screenshot. Dependencies and acceptance criteria below are the implementation plan derived from `PROJECT_SPEC.md`, rather than additional completed functionality.

Current execution: **DOCS-PRESENT — DONE** (user authorized 2026-10-28: fix the presentation layer). T35–T37 DONE. T36 DONE (see studies/hawkes_baseline/README.md). T35 DONE (11 rolling test days; see studies/rolling_validation/README.md). User chose (2026-10-28) to strengthen baselines by first building a new rolling-origin validation design, then adding a Hawkes baseline (T36) plus per-participant ranking metrics, and to push completed work. T35 only; T36 stays TODO until separately started. REPORT-FULL is DONE.

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
| [x] | T23 | History Window Study UI | DONE | T22 | Real backend-driven setup/audit/comparison/case explorer, downloads and AppTest; meaningful empty states. |
| [x] | T24 | Dataset Catalog 与接入门槛 | DONE | T23 | Source adapters/catalog, licenses/schema/coverage/history manifests and evidence-based eligibility. |
| [x] | T25 | MIT Reality Mining 接入 | DONE | T24 | Verify legal source/schema/coverage; exploratory-only unless reliable negative observation evidence. |
| [x] | T26 | 其他数据适配与合法性验证 | DONE | T24 | Verify Social Evolution/workplace source access, reading/quality, independent per-source eligibility without fabricated negatives. |
| [x] | T27 | 研究交付与最终验证 | DONE | T25, T26 | Research/window/catalog reports, reproducible outputs and full tests; reviewed Git changes, no unauthorized push. |
| [x] | T28 | Independent as-of-time inference | DONE | T27 | Direct1d historical candidates; bounded1/3/7d inputs without evaluation cohort/future coverage; dataset/window/all label-deadline guards; honest blind replay vs fresh anchored prospective mode; explicit independent outcome reveal; strict offline leakage tests and full pytest pass; frozen artifacts unchanged. |
| [x] | T29 | Time Machine 历史预测模拟器 | DONE | T28 | Independent UI uses as-of candidates/features and saved models; Select→Predict→Freeze→Reveal ordering; all context/data/model versions invalidate old state; correct Contact/No Contact/Unknown explanations and live clock/freshness guard; Streamlit/T28/full tests pass. |
| [x] | T29-FIX | Time Machine 标签覆盖策略传递修复 | DONE | T29 | Read verified min_scan_coverage from every T28 model contract; reject mixed policies; freeze actual policy under integrity hash; Reveal uses frozen threshold with no default fallback;0.25/0.5/0.75 x future0.4/0.6 tests plus T28/T29/full tests pass; safe branch push only. |
| [x] | T30 | 预测质量与选择偏差审计 | DONE | T29 | Separate all as-of candidates/reliably labeled/Unknown sets; daily funnels, paired1/3/7d metrics/reliability/error and population-bias diagnostics; local sample recomputation, no test retuning or unsupported significance. |
| [x] | T31 | 多数据集探索性研究 | DONE | T30 | Separate source quality/topology/positive-retrieval exploration, verified tick units/access/license; no invented negatives/AP or identity merging; clear descriptive vs predictive charts. |
| [x] | T32 | 数据处理和前端性能优化 | DONE | T31 | Measure real time/memory before/after; equivalent candidates/features/probabilities; safe version/time/window/policy caches and consistent snapshots; distinguish event and ingestion time; tests pass. |
| [x] | T33 | GitHub Actions 自动化测试 | DONE | T32 | Python3.11 public synthetic pytest/UI smoke and repository-safety CI; no private artifacts required; actual pushed commit Actions success verified, not merely claimed. |
| [x] | T34 | 最终科研验收与项目交付 | DONE | T33 | Audit T17–T33 evidence/frozen preservation; distinguish cohorts/prevalence/research scopes; final audit/reproduction/limits/index docs, full tests/security/remote CI, verified research branch push only. |

T01 excludes Streamlit navigation/pages, dataset downloads, preprocessing, features, training and predictions. These belong to later tasks.

## Post-delivery maintenance

| ID | Task | Status | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- |
| README-FRONTEND | GitHub README 更新与前端查看 | DONE | T34 | Document actual frontend startup/navigation/source and accepted T34 evidence; focused docs/public-audit/safety checks pass; safely publish research-v2.2 and verify own CI; open README and frontend source/live localhost preview. No research or UI feature change. |

## Product extensions

| ID | Task | Status | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- |
| P01 | 趣味偶遇预测 Play | DONE | T34, README-FRONTEND | Pure deterministic self-report index, valid/unknown/conflict/arrangement gates,3–5 sourced keyword cards, session edit/reset, native welcome with tested refresh scope,13-page navigation preserving12 research pages, focused/full/public/safety and exact-head three-job CI. |
| P02 | Explore 分析、线索图谱与三入口 | DONE | P01 | Reuse submitted P01 Keywords without rescoring policy; bounded deterministic self-report diagram, optional mutual-summary only; actual T22/T31 public stories with missingness/source/cohort guards; lazy three-entry homepage; edit/reset isolation; all14 pages/public/full/safety/browser/narrow/own-head CI pass. |
| P03 | 最终体验、导航与产品交付 | DONE | P02 DONE bb05d4a | Four native primary entries, all12 research routes/opt-in statistics retained; Play/Explore presentation and session invariants; real390/768/1440px browser checks; full/smoke/audit/safety and exact pushed HEAD three-job CI pass; STOP |

## Product documentation maintenance

| ID | Task | Status | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- |
| DOCS-P03 | README 与配套产品/科研交付文档补齐 | DONE | P03 DONE390384c | Accurate current branch/quick start/navigation/product flow and verified P03 SHA/CI counts; demo/checklist/portfolio/index/task/progress synchronized; no source/data/models/frozen changes; focused docs/public audit/safety and exact maintenance-head three-job CI verified; safe branch push and STOP |

## Full project report

| ID | Task | Status | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- |
| REPORT-FULL | 完整中文学术项目研究报告 | DONE | T01–T34/P01–P03 DONE;478a320 | Evidence-linked11 chapters, abstract/references/appendices; distinguish T17/T22/T30 populations and rule-based Play; accurate source-derived tables/black-white figures; A4 Chinese12pt/1.5spacing, numbered TOC/pages, rendered PDF QA; safe Markdown/SVG only in Git, local PDF, frozen51 unchanged, focused/safety/own-head CI; STOP |

## Research extension: stronger baselines

| ID | Task | Status | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- |
| T35 | 滚动起点重评估与按人排序指标 | DONE | T21/T22 frozen cohort/features/protocol | Protocol and complete fold plan frozen before any fit: every cohort prediction time with >=4 earlier train times and 3 validation times, each set's t+24h strictly before the next set's first t, >=20 rows of each class per set; unchanged T21/T22 models/parameters/seed/threshold rule, no calibration, no tuning; a fold is dropped for all models if any fit fails. Report pooled/per-day AP, ROC-AUC, Brier for 1/3/7d; paired day-block bootstrap (>=8 test days, 1000 reps, seed42) for prespecified contrasts; per-participant Precision/Recall/NDCG@5/10 on reliably labeled candidates. Disclose that all test dates were previously exposed (T17/T21/T22). Private predictions stay under ignored data/processed/rolling/<run_id>; public aggregates only outside reports/ (no CSV, no IDs); --verify-only recomputes metrics from local predictions; synthetic tests pass. |
| T36 | Hawkes 自激过程基线 | DONE | T35 | Per-pair exponential-kernel Hawkes intensity fitted by MLE per (t, pair) only on that pair's [t-7d,t) contacts (no labels; clarified at implementation: unsupervised, so no training-time pooling is needed); any decay grid chosen on fold validation only; evaluated in the frozen T35 fold plan with the same metrics and contrasts against XGBoost; no test-driven choices. |
| T37 | Hawkes 强度作为 XGBoost 输入 | DONE | T35, T36 | Prespecified before fitting: 7d bounded features plus all four T36 Hawkes grid scores (no half-life selection) feed XGBoost with unchanged T21/T22 parameters/seed, train-only all-null column removal, max-validation-F1 threshold, no calibration/tuning, on the frozen T35 fold plan. Hawkes scores for every train/validation/test time use only [t-7d,t) contacts; T36 scores are reused after checksum verification and overlap rows recomputed for equality. Report T35 metrics and contrasts XGB+Hawkes vs 7d XGBoost and vs Hawkes; public aggregates only; --verify-only; synthetic tests. |

## Presentation maintenance

| ID | Task | Status | Dependencies | Acceptance criteria |
| --- | --- | --- | --- | --- |
| DOCS-PRESENT | 展示层精简：文档归档、README 首屏与核心图 | DONE | T37 | Move the 12 non-frozen, non-generated root guides into docs/ with every relative link rewritten; keep the 7 trusted-baseline frozen documents, generated DATASET_CATALOG.md, workflow files and the REPORT-FULL deliverables byte-identical. README opens with the question, one source-derived result figure, a three-line conclusion and quick start; details move to docs/. Pages/navigation unchanged (research-route and legacy-UI contracts). Link, documentation, audit, safety and full tests pass; own CI succeeds. |
