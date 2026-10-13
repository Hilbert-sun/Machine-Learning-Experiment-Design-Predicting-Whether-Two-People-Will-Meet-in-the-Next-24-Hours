# 完整研究报告：章节与证据对应清单

基准：478a320c0a8146cf8dfdcbb8c0d93b16640b8594；审阅日期：2026-10-13。采用目录清点、关键源码审阅、公开聚合对账及已验收 CI 复核；不声称逐行审计全部代码，也不重新训练模型。所有数值表和数据图直接读取既有公开 JSON/CSV。报告不使用逐样本预测、研究配对或私有原始文件。

| 章节 | 主要代码依据 | 研究/工程证据 | 核对重点 |
| --- | --- | --- | --- |
| 1 绪论 | app.py、src/ui.py | README.md、PROJECT_SPEC.md、TASKS.md | 设备接触、记录事件与自填娱乐指数的边界 |
| 2 架构 | src/loader.py、src/preprocessing.py、src/model_registry.py、app.py | PORTFOLIO_GUIDE.md、DEVELOPMENT_HISTORY.md | 分层模块、独立数据通路和已实现能力 |
| 3 数据 | src/loader.py、src/dataset_catalog.py、src/preprocessing.py | reports/T17_DATA_DIAGNOSTICS.md、reports/multisource/T31_SOURCE_SUMMARY.json | 原始行/规范记录/有效配对/时间单位/不可用来源不同口径 |
| 4 特征 | src/label_builder.py、src/feature_engineering.py、src/window_cohort.py、src/window_features.py、src/asof_inference.py | T19_COHORT_AUDIT.md、T20_FEATURE_AUDIT.md、ASOF_INFERENCE.md | 严格时间边界、15项中性有界特征、历史候选与未来标签分离 |
| 5 实验 | src/temporal_split.py、src/baselines.py、src/train.py、src/calibration.py、src/window_study.py | T17_SAFE_METADATA.json、T17_REAL_EXPERIMENT.md、T22_ROBUSTNESS.json | 原始训练/校准/阈值支持，LightGBM仅能力与原生测试 |
| 6 结果 | src/evaluate.py、src/asof_audit.py、src/final_audit.py | T17_METRICS.json、T22_METRICS.csv/ROBUSTNESS.json、T30_METRICS.csv/RESULTS.json | AP定义、不同总体、Unknown、单类退化、概率损失与排序分离 |
| 7 网络 | src/network.py、src/positive_retrieval.py、src/multisource_exploration.py、src/encounter_graph.py | MULTISOURCE_STUDY.md、T31_SOURCE_SUMMARY.json、T31_RETRIEVAL_METRICS.csv | 正接触检索分母、相对日活动、结构示意不冒充个体研究网络 |
| 8 产品 | src/chance_encounter.py、src/chance_encounter_ui.py、src/encounter_insights.py、src/welcome.py、pages/ | PRODUCT_PLAN.md、PRODUCT_DELIVERY.md、EXPLORE_GUIDE.md | 固定规则、实际Keyword、状态隔离、四入口/15路由 |
| 9 测试与性能 | tests/、.github/workflows/ci.yml、tools/check_repository_safety.py、src/snapshot_manager.py、src/safe_cache.py | FINAL_RESEARCH_AUDIT.md、FINAL_RELEASE_CHECKLIST.md、CI_VERIFICATION.md、PERFORMANCE_AUDIT.md、T32_BENCHMARK.csv | 已验收SHA日志、51份冻结、测量范围、冷路径代价、截图范围 |
| 10 讨论 | 上述实现与协议 | REPRODUCIBILITY.md、T17/T22/T30/T31/T32各报告 | 数据缺失、参与者依赖、只有4主测试日、无实时采集证明 |
| 11 结论 | 当前完整已交付树 | TASKS.md、PROGRESS.md、以上交叉证据 | 已完成工作与未来计划分开，不把工程验证当科研泛化 |

以上表内未加目录前缀的研究文件位于原项目相应 reports/window_study、reports/asof_audit 或根目录；精确文件及SHA256清单由配套生成器输出到 REPORT_VERIFICATION.json。最终PDF与渲染中间文件仅在本地；公开SVG只含聚合数值或明确标注的结构示意。
