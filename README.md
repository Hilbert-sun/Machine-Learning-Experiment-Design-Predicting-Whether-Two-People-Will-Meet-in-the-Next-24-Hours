# Encounter Lab — 相遇实验室

使用公开、匿名接触数据，研究两名参与者未来 24 小时内发生设备近距离接触的概率。T01–T16的软件交付证据见 [DELIVERY.md](DELIVERY.md)。T17已在完整Copenhagen真实数据上完成首次基线/XGBoost实验：测试PR-AUC(AP)0.3815、ROC-AUC0.7507、校准Brier0.0777，详见 [诊断报告](reports/T17_DATA_DIAGNOSTICS.md) 和 [真实实验报告](reports/T17_REAL_EXPERIMENT.md)。数据与模型仅在本地，仓库只提交代码及安全聚合结果；新克隆仍需自行准备真实数据与模型。

## 环境安装

需要 Python 3.11。在项目目录执行：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
python -m pytest -q
```

macOS 上 XGBoost / LightGBM 需要 OpenMP 运行库。如果导入提示找不到 `libomp.dylib`，可使用已有 Homebrew 安装：

```bash
brew install libomp
```

`requirements-lock.txt`记录Python3.11/macOS arm64已验证环境的51个精确包版本，便于模型版本复现；`requirements.txt`保留可维护的依赖范围。T17完整测试结果：171项通过。新机器需从官方来源获取数据；仓库不包含原始样本和模型权重，T17安全聚合报告为明确例外。

通过以下命令启动应用，默认地址为 `http://localhost:8501`：

```bash
source .venv/bin/activate
streamlit run app.py
```

## 目录

```text
app.py                 Streamlit 顶部导航入口
configs/default.yaml   默认路径、预测窗口与时间切分设置
data/raw/copenhagen/   Copenhagen 原始数据
data/raw/sociopatterns/ SocioPatterns 原始数据
data/processed/        处理后的数据
data/features/         特征缓存
models/                本地模型
reports/               实验结果
pages/                 八个 Streamlit 页面
src/                   下载、读取、预处理与共享 UI
tests/                 环境、下载、字段验证与界面测试
```

默认深色主题，可通过 Streamlit 设置切换浅色主题。尚未接入的功能显示明确空状态，指标显示「—」。数据管理读取 `configs/default.yaml` 中的原始数据路径。数据、衍生数据、模型、报告、虚拟环境与密钥均通过 `.gitignore` 排除；空目录标记保留。

Overview复用当前清洗缓存，显示实测参与者、接触记录、配对、Study Day及已有模型版本；标签正例率仅使用当前配置策略下可评估的已知目标，无可靠分母时为“未知”。源文件或缓存版本改变后旧统计失效。

## 下载与上传

在 Data Manager 选择数据集。Copenhagen 先点击「读取官方文件清单」，选择文件后下载；文件名、地址、大小与 MD5 均取自 Figshare API。实际主文件名为 `bt_symmetric.csv`，不假设存在 `bt.csv`。界面不会默认下载大型文件。SocioPatterns 可直接下载官方压缩文件。

下载有超时、重试和进度提示，校验完成后才替换本地文件；失败保留原文件并删除临时片段。已有匹配文件会跳过。SocioPatterns 没有发布校验和，本地存在只表示已下载，仍需结构验证。

网络不可用时可从 Data Sources 的官方链接手动下载，放入对应原始目录后扫描，或在 Data Manager 上传。上传不会覆盖同名文件。Downloaded 不等于 Ready。

## 读取与验证

下载或上传完成后，在 Data Manager 点击「验证本地数据」。系统分块检查整个文件的字段、数值、整数 ID、时间范围与压缩完整性，显示最多10行预览和真实行数。文件改变后旧验证状态失效；失败显示 Validation Failed，修复后可以重新验证。

| 数据源 | 实际源字段 | 读取行为 |
| --- | --- | --- |
| Copenhagen 蓝牙 | `# timestamp,user_a,user_b,rssi` | 接受真实文件名 `bt_symmetric.csv`，兼容同结构 `bt.csv`；时间仍是相对秒 |
| Copenhagen 电话 | `timestamp,caller,callee,duration` | caller/callee 映射为 user_a/user_b；保留 duration=-1 的未接来电 |
| Copenhagen 短信 | `timestamp,sender,recipient` | sender/recipient 映射为 user_a/user_b |
| SocioPatterns 接触 | 无表头、空白分隔的时间/ID/ID/班级/班级 | 恰好5列，直接读取 gzip，保留原始 UNIX 秒 |

仅主接触文件通过验证才能显示 Ready；只有电话/短信不能让 Copenhagen 就绪。Ready 仅指源文件结构通过验证，不代表已经清洗或可以预测。蓝牙 -1/-2 扫描标记、重复行和自接触都保留给后续清洗任务；不将未知观测当作负例。静态 Facebook/gender 文件及 Notebook/README 当前仅保存和列出。

初期真实验证覆盖calls.csv、sms.csv、SocioPatterns及Copenhagen小片段；T17补齐了完整Copenhagen蓝牙。原始数据不会上传Git。reports目录默认忽略，五份T17及十五份经审查的T18–T22聚合证据按文件名列入白名单；其他本机验证记录、逐样本数据、HTML大文件及训练清单仍保持本地。

## 数据清洗与缓存（T05）

主接触文件验证通过后，点击「运行预处理」。同时存在多个主文件时只选择一个，避免重复计数。电话/短信原始文件保留供后续任务使用。预处理会过滤负参与者 ID 和自身接触，将两端统一为 `user_min/user_max`，并同步交换班级字段。完全相同的规范化接触记录在所有分块之间去重；同一时刻的不同配对、不同 RSSI 测量继续保留。不会增加 RSSI 或时长阈值，也不会修改原始文件。

缓存位于 `data/processed/<dataset>/`，包括：

- `contacts.parquet`：相对秒 `timestamp`、原始秒 `source_timestamp`、`user_min/user_max`、RSSI、对应两端班级。不存在的 RSSI/班级字段保持 null。Copenhagen 时间原点为0；SocioPatterns 使用首条时间所在 UNIX 整日的起点（`floor(min_timestamp/86400)*86400`），并记录可还原原始时间的偏移。
- `observations.parquet`：稀疏的参与者/时间窗口观测证据。Copenhagen 保留含 -1/-2 标记的报告者扫描窗口，不把接收者出现当成其主动扫描。SocioPatterns 仅记录有效正接触的两端，`scan_observed` 为 null。
- `coverage.parquet`：观测区间内每位参与者/研究日的已记录窗口数。Copenhagen 的 `scan_coverage = recorded_bins/288`，分母为完整研究日的5分钟窗口数，首末不足一日也使用相同分母；这是记录覆盖率，不是确定的设备在线率。无扫描的日记录为0覆盖率，但不生成「没有见面」标签。SocioPatterns 的期望扫描窗口数和扫描覆盖率均为 null，不能由正接触推断其扫描日志。
- `quality.json`：输入/过滤/重复/输出计数、缺失值、时间范围、RSSI摘要与每日接触记录数。这些是回顾性质量统计；未来预测必须按自己的时间窗口读取观测证据，不能直接使用全观测期统计构造特征。

预处理通过磁盘 SQLite 处理跨分块去重，使用 Parquet 保存结果。缓存签名包含源路径、大小、修改时间、数据集与处理版本；匹配缓存会复用。仅全部文件成功保存后发布缓存清单，源文件改变或输出不完整会使缓存失效；失败会清理本次临时输出并保留旧缓存。代码改变清洗语义时须增加 `src/preprocessing.py` 的 `VERSION`。

T05验证时只有完整SocioPatterns和Copenhagen片段。T17经用户授权已下载并校验完整Copenhagen主文件，原覆盖率/标签/时间隔离规则保持不变，现已完成真实预处理与首个实验；历史片段未作为训练数据。

## 数据探索（T06）

Data Explorer 直接复用当前源文件对应的清洗缓存。选择 Study Day 范围、匿名用户及可选无向配对：用户筛选保留任一端命中的记录，配对筛选再取交集。源文件变化或缓存缺失时，页面会要求重新预处理，不使用旧数据。

Plotly 提供每日/每小时趋势、配对频率、RSSI分布、活跃度排名、历史接触热力图及扫描/缺失观测图，支持悬停、缩放和图例交互。所有统计标注数据集、Study Day及筛选范围；排名和热力图只显示最活跃的20人。统计分块汇总全部匹配记录，不通过抽样伪装全量结果。RSSI使用缓存真实信号范围分箱；不同RSSI测量记录不等同于不同连续见面。

覆盖率独立于配对是否有接触，按所选用户汇总；未选用户时按配对两端，否则全部参与者。无接触记录时仍展示观测状态。SocioPatterns 不显示不存在的 RSSI分布或扫描覆盖率曲线，扫描覆盖率指标为「未知」。小时基于缓存时间原点，不伪造真实日历或当地时间；图表是回顾性探索，不是预测结果。

## 24小时标签（T07）

Data Manager 中先预处理，再点击「生成24小时标签」。配置默认每天08:00生成一次快照，预测未来24小时。只为 `timestamp < t` 已经接触过的 Known Pair 生成样本；不能借助未来接触找到候选，也不枚举全人口的所有配对。首版不加入通讯候选、不做负例下采样，不设置额外RSSI/持续时长阈值。

标签为 `(t, t+24h]` 内是否存在有效接触，正好在t的事件不计入标签，正好在t+24h的计入。未来窗口不完整的快照不生成样本。扫描覆盖率按该未来窗口中报告者的5分钟扫描窗口数/288计算，只用于标签可靠性与评估准入，不是模型输入。

「最低扫描覆盖率」默认0.5，是可调整的实验策略，并非经调优结论。两人均达到阈值才进入主要评估；此时无接触记录为0。已观测到的正例始终保留标签1，但低/未知覆盖时仍被排除出主要评估；没有可靠观测的无记录样本保持null。SocioPatterns没有扫描日志，因此其无记录不能作为负例，当前所有样本均不进入主要评估。后续训练必须同时检查标签非空及 `eligible_for_evaluation`。

标签及策略报告保存在忽略的 `data/processed/labels/`。API为 `src.label_builder.build_labels(processed, output, snapshot_hour=8, min_scan_coverage=0.5)`，其中 `processed` 来自现有预处理缓存。参数或输入签名改变会生成新缓存；失败不会发布半成品。

## 历史特征（T08）

标签生成后点击「生成历史特征」。API为 `src.feature_engineering.build_features(processed, labels, output)`。以预测时刻和规范化配对为键，输出独立的Parquet特征表到 `data/features/`；仅从标签文件读取键，不把目标标签、未来扫描覆盖率或评估准入字段带入特征。

所有历史窗口均为 `[t-window, t)`，窗口起点包含，预测时刻排除：

- 1/3/7/14天接触记录数；1/7天唯一配对扫描时间窗口数；7/14天有接触的Study Day数；距离最近一次历史接触的秒数。
- 7天RSSI均值/最大值、两端活跃记录数，以及仅由7天历史接触构成的邻居数和共同邻居数。
- 7天历史扫描覆盖率；14个历史滚动24小时桶中，双方覆盖率足够的桶的接触发生比例。没有可用分母时概率为空，不能把未知当0。
- 预测研究日索引（0起）、小时与各窗口 `history_complete_*` 标记，区分真实零计数与观察历史不足。

通讯可用时间尚未核实，电话/短信特征默认禁用且为空，强行启用会报错。星期起点未确认时 `relative_weekday/is_relative_weekend` 保持空值；只有明确设置 `features.weekday_origin`（周一=0）并附 `weekday_reference` 来源说明才计算，不能猜星期或伪造日期。SocioPatterns的RSSI、扫描覆盖率和历史接触概率继续为空。

默认产出29个数值特征字段（包括4个历史完整性标记），以及3个键字段；没有模型分数。缓存记录版本、输入签名与策略。实测改变未来接触或目标标签不改变此前快照的特征，构建期间输入改变则拒绝发布缓存。

阶段二的SocioPatterns样本仍为10,742行，4,023正例、6,719未知、0个主要评估可用样本；该数据的覆盖/时长限制未被改写。T17完整Copenhagen产生769,627个可评估样本，严格隔离后训练/验证/测试为269,757/155,368/260,170，支持真正的时间评估。

## 时间切分与模型开发（T09–T12）

Model Training 自动查找与当前清洗缓存、输入签名一致的标签/特征产物。只有标签已知、覆盖策略允许且键一一对应的样本可以进入训练；未知目标不会插补。当前SocioPatterns在页面上会禁用训练并解释缺少有效样本的原因。

默认按**不同预测时点**顺序进行60%/20%/20%切分，同一时点的所有配对在同一集合。训练与验证末尾凡是 `t+24h >= 下一集合开始时间` 的样本都清除，保证含端点的标签窗口严格结束于下一集合之前。清除后为空则报错，不改成随机切分；实际样本比例会因配对数量和隔离窗口而不同。

统一 `ModelRegistry` 支持七个模型：

| ID | API名称 | 规则 |
| --- | --- | --- |
| B0 | constant | 训练集正例率 |
| B1 | historical_frequency | T08历史接触概率；不可用时回退到训练集先验 |
| B2 | time_rule | 按历史最近接触间隔桶（1/3/7天）和预测小时学习训练集平滑概率 |
| B3 | logistic_regression | 训练段中位数插补、缺失标记、标准化及 Logistic Regression |
| B4 | random_forest | 训练段插补/缺失标记及 Random Forest |
| M1 | xgboost | 单CPU工作线程、固定随机种子的 XGBoost |
| M2 | lightgbm | 单CPU工作线程、固定随机种子的 LightGBM |

模型输入严格限制为T08历史特征白名单；配对ID、时间键、目标和未来覆盖率不能作为输入。完全不可用的训练列直接移除，部分缺失列只用训练段统计插补。页面可选择模型、运行全部Baseline或比较全部模型，并调整随机种子、树迭代数及最长历史窗口。窗口之外的特征组移除，超过窗口的最近接触间隔为空；拟合与预测使用同一契约。

可比较两组树迭代数，API也接受小参数网格（每模型最多32组）。参数按验证Log Loss选择，分类阈值按验证F1选择；并列阈值取最接近0.5者。报告记录平均精度版本的PR-AUC、Brier Score、Log Loss、Precision/Recall/F1及辅助指标，不以Accuracy作为唯一依据。

### 校准、保存和加载

校准可选 `none/sigmoid/isotonic`。启用时，验证集前半段用于拟合冻结基模型的校准器，后半段用于参数/阈值选择及校准前后比较；两个时段之间同样清除跨界24小时标签窗口。校准段缺少两类可靠目标或有效时长不足时明确报错，不能复用同一批样本假装独立评估。

页面显示后段验证集的校准前后Brier Score、Log Loss和可靠性图。测试集不参与训练、参数选择、阈值或校准；最终测试报告在Model Evaluation显式计算。训练完成自动把完整预测管道和模型清单保存到忽略的 `models/`，并将实验JSON保存到忽略的 `reports/`。清单记录模型版本、随机种子、有效参数、实际特征列、阈值、依赖版本、输入签名、本地清洗缓存版本、标签/特征策略和时间切分；加载前核对文件SHA-256和环境版本。

```python
from src.temporal_split import prepare_cohort, chronological_split
from src.train import train_models, save_training_run
from src.model_registry import ModelRegistry
from src.feature_engineering import FEATURE_NAMES

# labels/features 是T07/T08产物；必须有可靠正负目标及足够时间跨度。
split = chronological_split(prepare_cohort(labels, features))
run = train_models(split, ["logistic_regression", "xgboost"], calibration="sigmoid", feature_window_days=14)
record, report_path = save_training_run(run, "models", "reports", provenance={"dataset": "your_verified_dataset"})
model = ModelRegistry.load(record["saved_models"]["xgboost"])
probabilities = model.predict_proba(split.validation.loc[:, FEATURE_NAMES])[:, 1]
```

阶段三使用合成测试验证七模型管道；T17后来使用真实Copenhagen训练Constant Probability、Historical Contact Frequency、Logistic Regression及XGBoost，并验证模型保存/加载等价。SocioPatterns仍被拒绝作为主要训练队列，不把未知观测改为负例。

## 历史关系网络（T13）

Encounter Network 复用清洗缓存，在所选 Study Day/小时之前的 `[t-window,t)` 构建 NetworkX 无向图。节点大小按历史活跃记录数、边宽按接触记录数变化。可选1/3/7/14天窗口，查找匿名ID或点击节点查看完整窗口统计及历史邻居。绘图最多100节点/300边；默认30节点/100边，查找时保留所选节点及其最强历史邻居。截断显示不会改变完整统计，条件改变时旧点击选择失效。

已有SocioPatterns全量缓存的7天历史图已核对为327名参与者、5,818个配对、188,508条接触记录。布局不是地理位置，记录不等于实际交谈或社交关系。

## Prediction Lab（T14）

选择数据集、已训练模型、Study Day/小时、历史窗口及两名匿名参与者。候选ID与配对只来自预测时刻之前的记录；当前仅支持Known Pair。模型与数据集、历史窗口必须匹配，而且预测时刻必须严格晚于该模型训练/校准/参数及阈值选择所用验证标签的结束时间。不能拿使用了未来信息的最终模型伪装早期回测。

点击 Predict Encounter 才显示模型实际概率、所选窗口历史记录数、最近接触间隔、历史趋势与解释。数学分布熵仅为概率不确定性指标，不是经验证的置信区间。XGBoost/LightGBM 提供原生TreeSHAP原始分数贡献；其他模型使用明确标识的训练中位数替换敏感度，不称为SHAP或因果效应。

未来实验模式不读取或显示真实结果。显式历史回测才检查 `(t,t+24h]`：有正接触证据为Contact，可靠扫描下无记录才为No Contact，低/未知覆盖或不完整窗口为Unknown。改动输入或模式会隐藏旧结果。缺少模型时不显示占位概率。

API是 `src.predict.predict_pair(processed, model_directory, timestamp, a, b, window_days=14, backtest=False)`。原先完整特征组模型（窗口契约为null）仍按原契约预测，并在页面注明最近接触间隔使用全部已知历史；新训练的显式窗口模型遵守有界历史组。当前预测部署不支持依赖未接入通讯列的模型。

## 模型评估与实验（T15）

Model Evaluation 读取已保存训练报告与相同签名的数据，重建原时间切分，检查模型校验/版本及冻结阈值，再计算validation或最终test报告。评估不调用训练或阈值选择；启用校准时validation评估只用后段调参时段。测试页面禁用消融，配置只能由验证阶段确定。

报告包含实际已训练模型对比、PR/ROC、混淆矩阵、校准曲线、AP版本PR-AUC、Brier Score、Log Loss、Precision/Recall/F1、正例率和ECE，以及历史7天记录频率分组。无正例时PR/AP不可用，单类目标时ROC/AUC不可用，不生成伪造曲线。规则模型不假装有通用原生重要性；线性/树模型显示各自原生重要性，明确不是因果解释。

XGBoost `pred_contribs` / LightGBM `pred_contrib` 计算原生TreeSHAP，无需额外安装SHAP包。贡献和已与基模型原始分数核对；坐标是训练管道转换后的特征，可能含缺失标记，不是校准后概率贡献。默认解释前200条按时间排序的评估记录并标注样本范围，评估指标使用全部可靠目标。

- E1：比较同一冻结评估集合上的实际保存模型，未训练Baseline只标明缺失，不填假分数。
- E2：固定已选参数和随机种子，重新训练1/3/7/14天历史特征组，**只在验证集**比较，显示性能曲线。
- E3：仅在通讯特征已启用、有可核实的可用时间来源说明且训练字段完整时比较有/无通讯。当前真实管道禁用通讯，报告为not_available，不生成分数；已用明确验证约定的合成特征测试条件分支。
- E4：按预测前7天接触记录数分组，避免按未来接触分组。
- E5：用同一冻结评估集合比较校准前后概率分数与可靠性，不保证校准一定改善指标。

CSV按record_type区分模型指标、频率分组、校准前后、重要性、原生SHAP摘要、窗口/通讯消融及不可运行原因；不可用实验不填补数值。独立HTML包含Plotly脚本、曲线和实验元数据，可离线查看。JSON/CSV/HTML保存在忽略的reports目录，也可从页面下载CSV/HTML；合成测试来源会保留在页面、图表和导出中。

API入口：`src.experiments.evaluate_saved_run(report_path, evaluation_set="test")`、`run_ablation_experiments(report_path)`、`export_evaluation(report)` 和 `save_evaluation(report, directory)`。

阶段四/T16的模型交互证据来自合成测试；T17已补上首个真实实验，未新增UI功能。现有本机页面可发现真实Copenhagen模型；新克隆若没有忽略的本地数据/模型，仍显示诚实空状态。后续调参不得反复利用已报告的T17测试集。

## T17真实实验复现

先从官方API获取并验证完整bt_symmetric.csv，然后有意执行：

```bash
.venv/bin/python -m src.real_experiment
.venv/bin/python -m src.real_experiment_report
```

此命令复用数据流程、按固定协议重新拟合并覆盖T17聚合输出，不隐式下载。初始零样本由SocioPatterns无扫描日志和4.21天时长共同导致；完整Copenhagen解决了数据可行性，无需降低0.5覆盖门槛或弱化测试隔离。测试集仅有6个预测日，结果是记录过程下的初步可行性证据，不能解释为独立个体试验或长期关系预测。原始数据、模型与私有训练清单仍不提交。

运行当前测试：

```bash
python -m pytest -q
```

## 开发约束

先读 `PROJECT_SPEC.md`、`AGENTS.md`、`TASKS.md` 和 `PROGRESS.md`，每次只执行一个明确任务，通过相关验证后更新进度并停止。所有数据字段应由真实源文件验证，所有预测和指标应来自实际运行；不得使用未来信息构建特征或候选配对。没有观测不能直接当作没有接触。


## Research Edition：T18–T22

2026-10-10完成前五个研究任务，规范见 [RESEARCH_SPEC.md](RESEARCH_SPEC.md)。T17原始基准已冻结，84,332行差额来自Day16/21边界purge；不要运行上面的T17重拟合命令覆盖冻结证据。原E2仅屏蔽部分长窗口列，不能替代本轮严格信息预算比较。

新run `102140b8cf3df83f` 用共同前1d候选集、完整7d历史跨度及原0.5覆盖策略：100,485行eligible；purge后训练54,677／验证14,816／测试25,569行，11／3／4个预测日。中性命名特征逐项裁剪到1/3/7d；原T17代码/模型/报告不变。

| XGBoost历史窗口 | AP | ROC-AUC | Brier | Log Loss |
| --- | --- | --- | --- | --- |
|1d|0.588723|0.770656|0.128026|0.415109|
|3d|0.627494|0.799719|0.120801|0.394671|
|7d|0.691366|0.841494|0.109107|0.360995|

测试正例率21.38136%，7d−1d AP差+0.102644；4个主测试日及3个预设滚动折的差值均为正。结果支持这些观测时期内的窗口效果；仅4个主测试日，不输出置信区间或显著性结论。验证只有3天，无法在严格隔离后同时支持校准和>=2个阈值选择日，统一报告未校准模型及可靠性曲线。T17已经看过重叠日期，本轮不是全新独立外部验证；候选/正例率变化也使它不能与T17直接比较原始AP。

详见 [T18审计](reports/window_study/T18_AUDIT.md)、[共同样本](reports/window_study/T19_COHORT_AUDIT.md)、[窗口隔离](reports/window_study/T20_FEATURE_AUDIT.md)、[主实验](reports/window_study/T21_REAL_EXPERIMENT.md)、[三窗口/时间鲁棒性](reports/window_study/T22_WINDOW_COMPARISON.md)。三个模型全部实际拟合，较差的1d历史频率结果保留。十五份聚合输出可随代码保存；逐样本Parquet、36个模型和完整交互HTML保存在忽略目录。

在本机原T17数据/模型、T19共同cohort和T20特征缓存齐全的情况下：

```bash
.venv/bin/python -m src.window_verify
.venv/bin/python -m src.window_study
.venv/bin/python -m src.window_robustness
```

第一条只读校验所有冻结代码/数据/模型/概率及指标；后两条复用完成的独立run并生成报告，不重新拟合已完成run。完整HTML位于 `reports/window_study/102140b8cf3df83f/T21_REPORT.html` 和 `T22_REPORT.html`。新克隆不带本地数据/模型/cohort/特征，必须先准备同源产物；不得替换冻结输入以冒充复现。T19/T20生成API分别是 `build_comparison_cohort`、`build_window_features(history_window_days=...)`，私有特征receipt包含内容哈希和路径。

全量验证：185项测试通过；5个实验阶段的指标重算通过，36个保存模型对完整导出样本的预测一致。下一任务T23尚未开始，研究UI和新增数据源不属于本次交付。


## Research Edition最终交付：T23–T27

2026-10-10完成剩余任务，现共十个导航页面。新增 **History Window Study**：真实后端作业、完整样本审计、1/3/7d曲线、PR/可靠性/日期差异、CSV/JSON/HTML下载和保存模型个案预测。默认复用冻结研究；更改设置只评估validation，保护已报告test；未来模式不读取实际标签。新增 **Dataset Catalog**：分来源许可/访问/字段/哈希/时间/覆盖/可用历史诊断、小片段探针后合法下载、验证后手动导入及拒绝覆盖已有raw文件。

完整交付见 [RESEARCH_REPORT.md](RESEARCH_REPORT.md)、[WINDOW_STUDY.md](WINDOW_STUDY.md)、[DATASET_CATALOG.md](DATASET_CATALOG.md)。机器可读指标：[CSV](reports/RESEARCH_METRICS.csv)、[JSON](reports/RESEARCH_METRICS.json)；验证：[T27_VERIFICATION.json](reports/T27_VERIFICATION.json)。全量196项测试通过；十页真实AppTest、导出和临时本地HTTP启动通过；36个冻结模型的完整概率/指标一致，另有真实seed43验证作业及缓存复用检查。冻结T17–T22统计源码、数据、模型和报告保持不变。

来源结论：Copenhagen支持目前报告的主要实验；High School历史/扫描证据不足；Reality Mining处理版96个ID/1,086,403行，但时间ticks0–233单位未核验且无在线日志；Workplace2015/2013为217/92个ID、78,249/9,827行，各只剩3个完整7d历史预测日且缺在线证据，均仅探索；Social Evolution官方端点无法连接、许可/实际schema未核验，未下载实际文件。没有为了新增AP而造负例或混合来源。

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.window_verify
.venv/bin/python -m src.research_delivery
.venv/bin/streamlit run app.py
```

研究交付生成命令只读本地证据并生成聚合报告，不训练、不下载。数据/模型/逐样本预测和大型交互HTML留在本地；Git只保存经审查的代码、文档及按文件名列入白名单的聚合结果。未经新授权不push。全部T01–T27结束，未自动启动新任务。


## Research v2.2 — T29 Time Machine

新增独立顶部导航 **时间机器 · Time Machine**，现在共11个页面；不需要先运行离线Window Study。按 **Select → Predict → Freeze Prediction → Reveal Next24h** 操作，查看1/3/7天历史统计、模型信息截止时间及实际概率。预测/冻结阶段不读取未来结果；揭晓独立返回Contact/No Contact/Unknown及依据。选择、模型或数据版本变化会使旧活动记录失效。当前静态档案缺少可信实时锚点，实时模式会明确拒绝。

操作与限制见 [TIME_MACHINE.md](TIME_MACHINE.md)。冻结记录仅在会话中保存，原始数据、模型和逐样本结果不入Git。T17–T27冻结实验与T28接口保持不变。专项37项及完整234项测试通过；真实Copenhagen模型的完整流程、日期失效和归档实时拒绝也已验证。T30预测质量与选择偏差审计为下一任务，尚未开始。


## T30 — As-of预测质量与选择偏差审计

见 [ASOF_AUDIT.md](ASOF_AUDIT.md) 和 [聚合指标CSV](reports/asof_audit/T30_METRICS.csv)。固定原T22模型/阈值，在已报告Study Days24–27先冻结纯历史候选概率，再独立揭晓和对账。共38,005个候选，27,820个标签可揭晓，10,185个Unknown（26.80%）；92个候选因历史扫描输入不足拒绝推理，最终共同可预测且可靠标签子集为27,802行。

该条件子集上XGBoost1/3/7d AP为0.669281/0.701926/0.758930；**不能解释为全部候选总体的无偏性能或独立新测试改善**。新增12,436个候选中81.90%为Unknown，已知的2,251个结果全为正例；正例率/观测选择变化会抬高表面AP。7d Brier从旧队列0.109107变成新条件子集0.128114，不能只报AP上升。旧25,569行队列上的概率、标签和指标均重现原结果，冻结模型未重训。

```bash
.venv/bin/python -m src.asof_audit
.venv/bin/python -m src.asof_audit --verify-only
```

9个模型/窗口组合共享可评价键；Unknown不进入二分类指标。逐日漏斗、历史频率/扫描质量分组、可靠性曲线、错误统计和选择偏差均可由本地冻结样本重算。只有4日期，不报告显著性或置信区间。逐样本概率/标签/错误及完整HTML保存在忽略的data/processed/asof_audit/<run_id>/，只有7份经过审查的聚合文件纳入Git。T31多数据集探索尚未开始。


## T31 — Multi-Dataset Exploratory Research

新增第12个导航页 **多数据集探索 · Multi-Dataset Exploration**；读取真实聚合报告，支持来源切换、网络/频率分布、每日活动和已观测正接触Top-K检索。详见 [MULTISOURCE_STUDY.md](MULTISOURCE_STUDY.md)，[质量汇总](reports/multisource/T31_SOURCE_SUMMARY.json)、[检索CSV](reports/multisource/T31_RETRIEVAL_METRICS.csv) 和 [窗口适用性](reports/multisource/T31_FEASIBILITY.json)。

真实Workplace2013/2015：92/217名接触参与者，9,827/78,249条记录，755/4,274个配对；各只有3个完整7d历史时点。共同日期上固定频率Top20的1/3/7d候选池内捕获率为21.09%/23.13%/23.81%及5.82%/6.57%/6.38%，仅描述已记录正接触，不能跨源比较模型强弱。候选池覆盖未来已记录正配对31.34%/24.87%，候选池外大量正接触另报，不能只看Top-K命中。

HighSchool只有2个完整1d时点，短窗口结果仅有限描述；3/7d不运行。RealityMining仅拓扑：1,086,403原记录、27,572唯一(timestamp,pair)记录、2,539配对，未知tick不换算秒/天。SocialEvolution无合法核验实际文件，明确source_unavailable。缺少独立扫描日志，未观测保持Unknown，不生成分类AP/Precision等。Copenhagen主实验及T17–T30冻结产物不改、不重训。

```bash
.venv/bin/python -m src.multisource_exploration
.venv/bin/python -m pytest -q tests/test_positive_retrieval.py tests/test_multisource_exploration.py tests/test_multisource_ui.py
.venv/bin/python -m pytest -q
```

固定规则/时间/源哈希先冻结，纯历史排名保存后独立揭晓；重跑同协议核对原排名。无隐式下载。5份公开聚合输出可由本地522条时点/窗口/规则/K统计重算成117行；逐配对记录及交互HTML均忽略。小分组抑制不是形式化匿名保证。T28/T29/T31专项76项、全量282项测试通过，五来源真实页面验证通过。推送research-v2.2并核对远程SHA，不合并main。下一任务T32，尚未开始。


## T32 — 性能、安全缓存与稳定档案快照

见 [PERFORMANCE_AUDIT.md](PERFORMANCE_AUDIT.md)、[真实性能CSV](reports/performance/T32_BENCHMARK.csv)、[结果一致性](reports/performance/T32_PARITY.json) 和 [快照保障/限制](reports/performance/T32_SNAPSHOT_AUDIT.json)。每个真实路径/缓存状态5个独立进程，记录原生峰值RSS、中位耗时及范围；冷指应用缓存为空，未声称清空操作系统缓存。

MIT Reality Mining冷缓存峰值RSS439.69→318.36MiB，下降27.59%，达到25%目标。Copenhagen热缓存1/3/7d特征0.7675→0.0159秒，Time Machine已保存模型预测0.7827→0.0391秒；均与同样热状态的冻结T31源码比较。冷候选/检索/模型加载等请求因完整哈希、只读快照和缓存校验而变慢，具体例外完整公开，不宣称所有路径都加速。

候选/窗口/评分/排名/概率不变；整数和顺序精确一致，浮点容限1e-12。T30全38,005候选/9模型窗口组合及Known/Unknown/全部指标、T31全4来源唯一记录/图/配对频率/40份评分与完整排名/117行聚合结果均重现。36个冻结模型完整预测一致，836个受保护文件（含106份旧报告）不变。没有重训、调参或下载。

稳定快照绑定规范化来源与模型版本；中途变更报source_snapshot_changed并取消结果/缓存发布。损坏的非活动副本从相同核验来源建立新版本；缓存损坏/临时文件不被接受。Time Machine仍遵循Select→Predict→Freeze→Reveal，schema3使旧活动记录失效；真实模型全流程、修改日期失效及静态档案实时拒绝已验证。事件时间回放缺少ingestion_time，不能代表当时的在线采集；检查后TOCTOU、跨文件实时原子采集和孤立缓存版本清理仍有限制。

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.performance_benchmark --stage NEW_STAGE --repeats 5
.venv/bin/python -m src.performance_benchmark --stage NEW_STAGE --cache-mode warm --repeats 5
.venv/bin/python -m src.performance_audit
```

公共测试不依赖私人数据/模型；真实性能复现需合法同源本地档案、原保存模型和原测量收据。原baseline/已完成stage禁止覆盖。原始测量、权重副本、私人缓存与逐配对结果均留在忽略目录，仅三份安全聚合报告入Git。专项109项、全量307项通过。推送research-v2.2并核对远程SHA，不合并main。下一任务T33，尚未开始。


## T33 — Public GitHub Actions CI

新增 [CI_VERIFICATION.md](CI_VERIFICATION.md) 说明测试清单、公开验证与本地真实研究复现的不同范围。工作流在research-v2.2的push/PR触发，采用Ubuntu/Python3.11和只读权限；unit-tests运行全量pytest，streamlit-smoke覆盖全部导航/交互，repository-safety检查实际Git索引、51份历史冻结公开材料及Gitleaks全可达历史/跟踪内容。没有私人数据/模型恢复、数据集下载、正式模型重训或main合并。

```bash
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
python tools/check_repository_safety.py
python -m tools.run_secret_scan
```

最后一条仅下载经固定SHA256核验的官方Gitleaks软件，不下载研究数据；仅支持当前核验的Linux x64/macOS ARM64。macOS requirements-lock.txt不冒充Linux依赖锁。测试中的真实HTTP请求默认拒绝，downloader使用mock；安装依赖/扫描器可联网。仓库扫描不是形式化匿名性保证。

首次真实Linux实现运行 [38053176593](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38053176593) 全部成功：335项全量、61项页面、24项安全及12项原生依赖检查，pip check通过，51份冻结公开材料不变。最终工作流不恢复任何依赖/home/研究缓存，并增加模型格式拒绝测试。文档/配置提交也必须重跑三个Job，最终验收以最新SHA对应的真实Actions为准；详见CI_VERIFICATION.md及交付回复。T34尚未开始。
