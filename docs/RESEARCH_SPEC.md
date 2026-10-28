# Encounter Lab — Research Edition 2.0
## T18–T27 分任务 Codex 实施手册 v2.1（2026-10-09，7天主窗口）

**目标**：在保留 T17 真实数据实验及其代码/报告的前提下，开展严格的 1 天 vs 7 天历史窗口比较，并加入 3 天作为中间对照（1/3/7 天），增加 Streamlit 研究 UI，并调查/验证更多长期匿名接触数据源。

**当前已知**：T17 本地提交 `f116951`，截图标记为尚未推送；T17 报告 769,627 个有效样本、269,757/155,368/260,170 训练/验证/测试样本，测试正例率 10.22%；XGBoost sigmoid AP=0.3815、ROC-AUC=0.7507、Brier=0.0777，171 个测试通过。以上来自用户展示的运行摘要；不要把 GitHub 远端 T16 当作最新本地研究状态。

**工作模式**：严格按任务号执行，每次只执行一个任务；结束时输出修改文件、验证命令及结果、剩余风险、下一任务；然后 STOP，等待用户输入 `next`。除非用户额外明确授权，不要推送远程仓库；不要覆盖 T17 原报告、原模型、原数据。


## 本次从14天改为7天的研究决策

- **主假设 H1：** 相比仅使用前24小时，使用前7天信息能提高未来24小时匿名蓝牙接近事件的预测 AP。**这是假设，不是既定结论**；同时报告差异及其不确定性。
- **对照 H0：** 7天窗口不会比1天窗口带来稳定的 AP 提升。
- **中间对照：** 3天窗口检查性能提升是逐渐增加、快速饱和，还是因样本有限而不稳定。
- **为什么选择7天：** 周周期是可解释的时间尺度，且相比14天减少观测期长度门槛，能保留更多共同预测时点；“快餐式时代”可以放在科普动机中，但不作为数据支持的统计学论断。
- **24小时预测目标不变。** 不要把“输入7天历史”误写成“预测未来7天”。
- **7天也不是万能的：** 在没有可靠扫描/设备在线证据的数据集中，缺失记录依然不是可证实的负例；跨数据集仍须独立报告。
- **与 T17 的关系：** 原 T17 的14天配置及历史分数只保留作已有基准资料，不删除、不篡改；新一轮严格 1d/3d/7d 比较必须生成独立 run ID 和对应结果。

## 研究原则 / 硬约束

1. 目标仍是 `(t, t+24h]` 内的**匿名设备近距离接触**，不是爱情、朋友关系或真实面对面交谈。
2. 1d 和 7d 的主比较必须共享完全相同的 `sample_key=(dataset_id,t,user_min,user_max)`、标签、候选集合、训练/验证/测试日期和扫描覆盖门槛，并显示每一层过滤的样本数。
3. 对**严格的信息预算比较**，主实验候选集合必须只依赖 `[t-1d,t)` 数据（或使用另行明确定义的共同独立候选机制）；不能仅靠 7 天历史发现配对，再声称 1d 模型没有使用更早的信息。可附加“7天候选池扩展”实验，但不得直接与主实验 AP 作公平对比。
4. 历史窗口：1d `[t-86400,t)`、3d `[t-3*86400,t)`、7d `[t-7*86400,t)`；未来标签窗口 `(t,t+86400]`。**主比较所有样本统一要求具有完整7天可用历史的时间跨度**，并有可评价的未来24小时观测。时间跨度完整不等于扫描覆盖完整，依然必须使用可靠观测覆盖策略；不将无扫描记录自动认作“确定未见面”。
5. 无未来特征、无时间随机划分、无测试集调参；把时间分组，边界必须 purge 24h 重叠的标签。所有折都明确列出 **独立的预测天数**，不能拿数十万条配对样本冒充数十万个独立时间观察。
6. 第一轮比较：相同 XGBoost 配置、随机种子、样本和训练预算，只有历史特征预算不同；增加 Historical Frequency 和 Logistic Regression 做参照。第二轮（可选）允许分别调参，各窗口给相同验证预算。
7. 主要报告 AP（Average Precision）及测试正例率、相对常数基准提升；并报 ROC-AUC、Brier、Log Loss、Precision、Recall、F1、校准曲线。不同数据集的原始 AP 不在正例率不同的前提下直接排序。
8. 主测试一次性冻结。消融/超参/窗口选择使用训练+验证。必要时通过前向滚动多个时间折检验稳健性；按时间块做配对差异置信区间，样本独立性有限应说明。
9. 数据源许可、个人隐私、原始数据不入 Git、不自动上传、不擅自重识别。各数据集 ID 严格隔离；不跨源把相同匿名数字视为同一个人。
10. 优先复用现有 `src/experiments.py` 的 E2 历史窗口消融、`src/model_registry.py` 与 Model Evaluation 页面，先审计实际语义再增量开发，不重写成熟部分。

## 任务安排

### T18 — T17 基准冻结与审计
- 读取本地 `PROGRESS.md`, `TASKS.md`, `DELIVERY.md`, T17 新增文件、现有 UI、特征、训练、实验、时间切分代码。
- 确认本地 Git 状态；优先读取本地尚未推送提交 `f116951`。将 T17 实际配置、数据源哈希、样本统计、模型及报告路径、训练/验证/测试独立日期保存成不可变 baseline manifest。
- 对账：769,627 与 269,757+155,368+260,170=685,295 相差 **84,332**；逐项报告被过滤、purge 或舍弃的原因，不得擅自填解释。
- 对既有 E2 消融审查：`feature_window_days=1` 是否严格屏蔽 3/7天网络特征，以及原有14天特征、历史频率、`time_since_last_contact`、1天外的配对可见性；是否用同一 validation row keys。
- 验收：baseline 数值和本地报告可复核；包含审计清单及剩余风险；全部原测试通过。

### T19 — 比较样本与真实信息预算
- 统一 stable sample key，建立完整7天历史要求的共同样本集合，记录排除样本理由与每个快照日正/负样本数。
- 设计严格 1d 可观测候选配对集合，在主比较中固定用于所有历史窗口；候选必须以预测时刻及之前数据生成。不能偷用其他窗口来筛选 1d 候选。
- 共享 `train/validation/test` split manifest、时间清洗边界和最终标签哈希。保存 Parquet + JSON，不覆盖 T17。
- 若共同有效预测时点不足以建立独立验证/测试，明确报 `insufficient_days` 并提出可审计的替代时间验证方案，**禁止**退化成随机划分。特别检查减到7天后，purge 24h、训练/验证/测试、校准分段还能剩多少个实际预测日。
- 验收：两个历史窗口的样本键、标签、集合划分完全一致，且 7d history completeness 验证通过。

### T20 — 重构窗口隔离与特征计算
- 提供参数 `history_window_days`，确保严格裁剪 pair-count、活动度、RSSI、网络共同邻居、历史概率、扫描覆盖、最近见面间隔等特征。
- 1d 模型不能看到 3/7天窗口统计（包括原项目14天遗留特征），也不能通过“是否为老配对”的未声明变量绕过隔离；必要时构建显式窗口型的网络特征。
- 做缓存 key 包括 source signature、窗口长度、特征版本、cohort version；面向大数据源使用 Arrow/Parquet、分块读和可恢复缓存。
- 验收：在 t-5d 插入一条过去接触，1d 特征完全不变、7d 特征可能变化；在 t-10d 插入一条过去接触，1d/3d/7d 特征都不变；修改 t 之后的数据，两者历史特征都不变。

### T21 — 1d vs 7d 主实验
- 主模型 XGBoost；参照 Historical Contact Frequency 与 Logistic Regression；严格固定种子与超参。
- 同一 train/validation/test，测试集完全冻结；自动存储预测概率与标签、运行耗时及元信息。校准策略在验证集独立分段确定；若有效验证天数不足，允许报告未校准模型并说明原因，不得牺牲防泄漏约束。
- 输出 `reports/window_study/` 中 CSV、JSON、HTML 的审计结果，包含 `AP_1d`, `AP_7d`, `delta_AP_7d_minus_1d`, `ROC-AUC`, `Brier`, `Log Loss`, `Precision`, `Recall`, `F1`, positive prevalence。
- 验收：所有对比指标可由导出的预测概率重算，不显示演示数字。

### T22 — 3d 中间窗口与时间鲁棒性
- 在已经比较的1d、7d之间增加3d，画1/3/7天的 AP、ROC-AUC、Brier 和 Log Loss 对比曲线。
- 如果可行，增加按研究日滚动的 walk-forward folds；每折保留独立训练、验证和未来测试关系，不允许后折信息穿越到前折。
- 使用成对样本和按时间块聚合的差异估计区间；独立日数不足时不要输出貌似精确的显著性结论。
- 输出低频接触组、扫描质量分组、不同预测日的敏感性分析。对比遵循共同1天候选集主分析；另行报告“7天候选集扩展”的覆盖范围，但不得将其 AP 与1天候选集结果直接解释为纯窗口效应。
- 验收：主报告说明窗口效果是否稳定，以及有限时间跨度的局限。

### T23 — 新增 Streamlit `History Window Study` 页面
- 在现有顶部 `st.navigation` 增加 `pages/8_History_Window_Study.py`（或按现有顺序合理命名）。
- 页面分四个区域：`Experiment Setup`, `Cohort Audit`, `Window Comparison`, `Case Explorer`。
- 设置控件：Dataset, Candidate Policy, Coverage Threshold, Compare Windows, Model, Seed, Calibrate, Run Study；用户点击触发真后端作业，长任务要有进度和缓存。
- 样本审计：历史可用天数、每日 eligible 正负数量、筛选漏斗、训练/验证/测试独立日期、被 purge 数量。
- 对比：3窗口 AP 柱图/曲线、ROC-AUC、Brier、Log Loss；1d 与7d 成对差异图、PR曲线、校准曲线及按日期性能；展示测试正例比例。
- Case Explorer：匿名 A/B、预测时间、窗口1d/7d 及两模型预测；仅历史回测允许展开真实结果。
- 空状态：未运行、缺数据、无已校准模型、时间不足时显示具体阻碍，不显示虚假概率。
- 验收：实际研究结果驱动全页，CSV/HTML 下载有效；切换数据/策略会使不兼容缓存失效；Streamlit AppTest 通过。

### T24 — Dataset Catalog 与接入门槛
- 新增 `pages/9_Dataset_Catalog.py` + 可扩展 `DatasetAdapter`：获取源清单/许可，下载或手动导入，校验 schema、时间戳、参与者 IDs、时间跨度、观测/扫描覆盖证据。
- 为每个数据源输出 `dataset_manifest.json`: source_url, citation, licence, file hash, temporal_resolution, first/last timestamps, participants, event rows, valid pairs, scan coverage evidence, usable days for 1d/3d/7d, eligibility status。
- 标记 `eligible_primary_24h`, `exploratory_only`, `insufficient_history`, `restricted_access`, `not_yet_verified`。不要因文件能打开就将数据标成可训练。
- 新增源须先下载一小段并做 schema 检查；只有审核合法访问路径后才允许下载全量。避免重复下载。
- 保留原 Copenhagen/SocioPatterns 下载器；添加新适配器不能破坏旧功能。
- 验收：每个数据集有公开/受限状态、下载/导入路径、字段和缺失数据诊断。

### T25 — MIT Reality Mining 接入（优先）
- 先检查公开镜像和 Mendeley：原始网络边是否明确指蓝牙接近、时间戳单位和范围、重复测量、参与者 ID 稳定性、许可、采样窗口/扫描日志是否可获。
- 参考源：
  - https://networks.skewed.de/net/reality_mining
  - https://data.mendeley.com/datasets/d6bzzfd23g/1
  - https://realitycommons.media.mit.edu/realitymining.html
- 若没有能证明无接触时可靠观测的扫描证据：接入 `exploratory_only`，**不要**计算把未观测当负例的“真实预测 AP”。
- 若证据充分，再走完整 1d/3d/7d 标签、特征、时间切分和评估。
- 验收：数据字典、源信息与报告说明确切限制，绝不自动造负例。

### T26 — 其他数据适配 / 合法性验证
- MIT Social Evolution（官方介绍）：https://realitycommons.media.mit.edu/socialevolution.html ；Proximity字段：https://realitycommons.media.mit.edu/socialevolution1.html 。检查原始数据实际可否获取；受限则只列目录不绕过访问限制。
- Workplace 2015：https://sociopatterns.org/datasets/test/
- Workplace 2013：https://sociopatterns.org/datasets/contacts-in-a-workplace/
- 2015/2013 Workplace 必须逐日计算连续可用历史和可靠观测；满足7天日历跨度不等于拥有7天的有效扫描覆盖。若严格条件下7d训练、验证、测试独立日期不足则标记 `insufficient_history` 或 `insufficient_days`；可在数据质量规则允许时做1d/3d探索，不能放宽规则以强行产出7d指标。
- 跨数据集初版**分别训练与分别报告**，不可把不同人群、不同传感器的 raw event 直接拼在一起宣称样本增大。
- 验收：每个新增源至少实现正确的读取/解析/质量报告；可比较的实验要有完整支持证据。优先检查 Workplace 2015 是否存在足够7天历史后的独立评估日；2013短观察期很可能不适合完整7天主实验，但仍可做数据接入与探索。

### T27 — 研究交付与最终验证
- 对 T17 / 1d / 3d / 7d / 各数据集状态给出总表。
- 输出 `RESEARCH_REPORT.md`, `WINDOW_STUDY.md`, `DATASET_CATALOG.md`, 可复现的机器可读指标和有证据的结论。
- 报告不完整的7天历史、不同 dataset 的扫描证据不足、少数独立日期、不能代表实际面对面交流等局限。
- 全量 pytest、Streamlit AppTest、数据与模型缓存验签、CSV/HTML 实际导出检查；不上传隐私/原始数据/模型和密钥。
- Git 变更及提交应经检查。**未经用户明确授权不 push**。

## UI 设计草图

```text
Encounter Lab | Overview | Data Manager | Data Explorer | Network
              | Training | Prediction | Evaluation | Window Study | Datasets

Window Study
[Dataset ▼] [Candidate Policy ▼] [Coverage ▼] [Model ▼]
[Compare: ☑1d ☑3d ☑7d] [Run Experiment]

Dataset Quality: duration | scan coverage | usable snapshot days | eligible samples
Cohort Audit: raw -> labels -> coverage -> 7d eligible -> purge -> train/val/test

Window Comparison:  AP (3 windows) | ROC-AUC | Brier | Log Loss
                    delta(7d - 1d) | paired uncertainty | positive prevalence
                    PR Curves | Calibration | Per Study Day

Case Explorer: Person A / Person B / Study Day / Model
              1d prob | 7d prob | historical support | backtest outcome
[Download CSV] [Download JSON] [Download HTML]
```

## 每个任务的标准输出

```text
Task ID:
Status: DONE / BLOCKED
Changed files:
Actual dataset(s) used:
Commands run:
Tests: passed / failed
Actual metrics (if produced):
Data-leakage / coverage checks:
Remaining issues:
Next task (not started):
```

## 给 Codex 的启动指令（先只跑 T18）

你是 Encounter Lab 的研发工程师。完整阅读本文件，优先理解用户本地工作区（尤其尚未推送的 T17），不要用远端 T16 状态替换本地结果。**实验目标已调整为 1天 vs 7天（3天为中间对照），绝不擅自沿用旧1天 vs 14天主比较。现在只执行 T18：冻结并审计 T17；不要实施 T19–T27，也不要开始下载新数据、修改研究模型或 push。** 完成后用规定格式汇报，等待用户输入 `next`。
