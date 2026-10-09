# Encounter Lab — 相遇实验室
## Codex / Vibe Coding 项目实施手册 v1.0

**项目目标：** 使用公开真实接触数据，预测两个匿名参与者在未来24小时内是否发生物理接近事件，并通过交互式UI展示数据、预测概率、模型性能和历史关系网络。

**开发方式：** Codex 驱动的 Vibe Coding。采用分阶段开发，每阶段验证后再进入下一阶段。

**技术栈：** Python 3.11、Streamlit、Pandas、NumPy、scikit-learn、XGBoost、LightGBM、Plotly、NetworkX、Requests、PyArrow、pytest。

---

# 1. 数据集来源与下载

## 1.1 主数据集：Copenhagen Networks Study

官方数据页：

https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433

数据 DOI：

https://doi.org/10.6084/m9.figshare.7267433

研究论文：

https://www.nature.com/articles/s41597-019-0325-x

数据采用匿名化处理，包含约4周的手机蓝牙接近事件、电话和短信元数据，以及静态社交关系。

### 方法A：网页手动下载

1. 打开 Figshare 官方数据页。
2. 点击 `Download all`。
3. 下载后解压到项目的 `data/raw/copenhagen/` 目录。
4. 确认主要 CSV 文件齐全。
5. 打开 Streamlit 的 Data Manager 页面，点击 `Scan Local Files`。
6. 系统自动读取文件、检查字段、显示数据状态。

### 方法B：Figshare API 自动下载

推荐由 Codex 实现下载管理器。

元数据 API：

```text
https://api.figshare.com/v2/articles/7267433
```

单独文件清单 API：

```text
https://api.figshare.com/v2/articles/7267433/files
```

下载逻辑：

```python
import requests

article_id = 7267433
url = f"https://api.figshare.com/v2/articles/{article_id}"

response = requests.get(url, timeout=30)
response.raise_for_status()

metadata = response.json()

for item in metadata["files"]:
    print(
        item["name"],
        item["size"],
        item["download_url"]
    )
```

要求：

- 不要手动猜测 Figshare 文件 ID。
- 从 API 返回的 `download_url` 获取真实地址。
- 使用流式下载，避免一次读取全部数据。
- 支持下载进度、错误提示、超时、重试。
- 下载前检查本地文件，避免重复下载。
- 若 API 不可用，允许手动上传文件。
- 检查 API 元数据中的文件大小及校验信息（如果存在）。
- 不要自行生成不存在的下载链接。

预计数据文件：

```text
bt.csv
calls.csv
sms.csv
fb_friends.csv
genders.csv
Copenhagen_Networks_Study_Notebook.ipynb
```

真实文件清单以 API 返回结果为准。

### 关键字段

`bt.csv`

```text
timestamp
user_a
user_b
rssi
```

`calls.csv`

```text
timestamp
user_a
user_b
duration
```

`sms.csv`

```text
timestamp
user_a
user_b
```

注意：

- 时间戳是观测期开始后的相对秒数，不是真实日期。
- 蓝牙扫描按5分钟划分时间窗口。
- `user_b = -1` 表示空扫描。
- `user_b = -2` 表示发现研究之外的设备。
- 有效参与者ID不能假设连续。
- 蓝牙RSSI只是粗略的距离代理，不能直接换算成准确的米数。
- 蓝牙接近不等于真实面对面交流。
- Facebook关系数据为期末静态快照，默认禁止加入严格时间预测模型。
- 短信和电话元数据按日收集，严格实验应考虑上传延迟，或者将这两类数据限制到预测时间之前已可靠可用的保守窗口。

## 1.2 辅助数据集：SocioPatterns High School

官方下载页：

https://sociopatterns.org/datasets/high-school-contact-and-friendship-networks/

接触数据直接下载：

https://sociopatterns.org/assets/data/HighSchool2013_proximity_net.csv.gz

下载后保存在：

```text
data/raw/sociopatterns/
```

下载方法：

1. 网页打开官方链接。
2. 下载 `.csv.gz` 压缩文件。
3. 使用 Pandas `read_csv` 直接读取，无须手动解压。
4. 数据按20秒间隔记录。
5. 解析时间戳、两名学生ID以及各自班级。

注意：这是空格分隔的接触事件数据，不要因为扩展名是CSV就默认按逗号解析。应使用合适的 `sep` 参数并验证字段数量。

本数据集主要用于测试整套机器学习流程，不能直接将五天样本推断到数年的人际关系。

## 1.3 数据来源与署名

在应用内设置独立的 `Data Sources` 页面，展示：

- 数据集名称。
- 作者和发表年份。
- DOI / 官方链接。
- 数据许可。
- 数据字段简介。
- 实验用途和局限。

Copenhagen 数据与论文的许可分别按官方页面及文件信息注明。

SocioPatterns 使用 CC BY-NC-SA，应用中必须保留正确署名，不得误当作可以无限制商业使用的数据。

---

# 2. 项目环境

使用 MacBook、VS Code 与 Python 3.11。

初始目录：

```text
encounter-lab/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── configs/
│   └── default.yaml
├── data/
│   ├── raw/
│   │   ├── copenhagen/
│   │   └── sociopatterns/
│   ├── processed/
│   └── features/
├── models/
├── reports/
├── pages/
│   ├── 1_Data_Manager.py
│   ├── 2_Data_Explorer.py
│   ├── 3_Encounter_Network.py
│   ├── 4_Model_Training.py
│   ├── 5_Prediction_Lab.py
│   └── 6_Model_Evaluation.py
├── src/
│   ├── downloader.py
│   ├── loader.py
│   ├── preprocessing.py
│   ├── feature_engineering.py
│   ├── label_builder.py
│   ├── temporal_split.py
│   ├── baselines.py
│   ├── train.py
│   ├── predict.py
│   ├── evaluate.py
│   └── visualization.py
└── tests/
    ├── test_downloader.py
    ├── test_schema.py
    ├── test_labels.py
    ├── test_leakage.py
    └── test_training.py
```

初始操作：

```bash
mkdir encounter-lab
cd encounter-lab

python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
```

由 Codex 生成并维护 `requirements.txt` 后：

```bash
pip install -r requirements.txt
streamlit run app.py
```

默认本地地址：

```text
http://localhost:8501
```

`.gitignore` 必须排除原始数据、处理后的敏感衍生数据、模型大文件、虚拟环境与密钥。

---

# 3. 数据预处理

## 3.1 数据检查

系统自动检查：

- 数据行数与字段名称。
- 字段类型。
- 缺失值。
- 重复记录。
- 无效参与者ID。
- 时间戳范围。
- RSSI分布。
- 每名参与者的数据可用率。
- 各天的接触事件数量。

不要直接删除所有重复时间戳，因为同一时间可能存在多个不同配对的接触事件。

## 3.2 配对ID标准化

由于A-B与B-A代表同一个无向接触关系：

```python
user_min = min(user_a, user_b)
user_max = max(user_a, user_b)
```

使用两个ID构成稳定的配对键。

必须排除无效ID和自身接触：

```python
user_a >= 0
user_b >= 0
user_a != user_b
```

## 3.3 正例标签

主实验的定义：

在预测时间 `t` 后的24小时内，只要该配对有一次符合阈值的有效蓝牙接近事件，则：

```text
label_24h = 1
```

否则：

```text
label_24h = 0
```

使用半开区间：

```text
(t, t + 24 hours]
```

默认第一版不限制额外的持续时间与RSSI阈值，直接使用有效的蓝牙接近事件。

第二版增加可配置参数：

```text
Minimum Contact Bins
RSSI Threshold
Minimum Estimated Duration
```

必须强调：单个蓝牙事件只证明设备近距离接近，不证明两人进行了交流。

## 3.4 预测窗口

默认每天生成一次快照。

```text
prediction_time = relative_day_start + 8 hours
prediction_horizon = 24 hours
```

因为Copenhagen没有真实日历日期，界面统一使用：

```text
Study Day 01
Study Day 02
...
```

不要伪造实际年月日。

未来可加入每6小时预测一次的模式，但必须处理重叠预测窗口以及相应的统计依赖。

## 3.5 负例采样

禁止把整个用户集合的所有可能配对直接全部生成训练样本，因为这可能造成巨量无效负例，模型只学会预测「不见面」。

设计两种模式：

**Known Pair：** 只预测在当前预测时刻之前已经存在有效接触记录的配对。

**Candidate Pair：** 基于过去的接触或通讯历史构造候选配对，测试较少见面的人。

候选配对只能使用历史信息构建，不允许通过完整数据先找出未来会接触的配对。

训练阶段允许负例下采样，但验证集和测试集必须保留真实分布；如果采用负例下采样，需要对最终概率校准进行处理。

此外，持续缺少蓝牙扫描的时段不能简单标记为确定没有见面。需要设置最小数据覆盖率阈值，并将低覆盖样本标记为未知或从主要评估中排除。

---

# 4. 特征工程

默认历史观察窗口：

```text
1 day
3 days
7 days
14 days
```

生成以下特征：

```text
contact_count_1d
contact_count_3d
contact_count_7d
contact_count_14d

contact_bins_1d
contact_bins_7d

time_since_last_contact

unique_contact_days_7d
unique_contact_days_14d

historical_contact_probability

rssi_mean_7d
rssi_max_7d

sms_count_7d
call_count_7d

prediction_day_index
prediction_hour
relative_weekday
is_relative_weekend

participant_a_activity_7d
participant_b_activity_7d

common_neighbors_historical
historical_network_degree_a
historical_network_degree_b

scan_coverage_a
scan_coverage_b
```

要求：

1. 所有滚动统计只能使用预测时刻以前的数据。
2. 不允许用完整数据集提前计算关系网络特征。
3. 星期索引应根据论文提供的观测起点约定计算。
4. 没有接触与没有观测必须区分。
5. 如果短信或电话特征的可用时间无法确定，初版先禁用。
6. 特征工程必须支持缓存，以 Parquet 保存中间数据。

---

# 5. 模型系统

## 5.1 Baselines

必须实现：

```text
B0: Constant Probability
B1: Historical Pair Frequency
B2: Time-based Rule
B3: Logistic Regression
B4: Random Forest
```

## 5.2 Main Models

```text
M1: XGBoost
M2: LightGBM
```

主输出：

```python
prediction_probability = model.predict_proba(X)[:, 1]
```

支持在验证集上选择分类阈值。

支持概率校准，并对校准前后的Brier Score、Log Loss和可靠性图进行比较。

所有模型统一通过 `ModelRegistry` 接口调用，支持保存、加载、比较与选择。

## 5.3 时间切分

采用 Chronological Split。

推荐初始比例：

```text
Train: 60%
Validation: 20%
Test: 20%
```

按预测时间进行顺序切分，训练样本的标签窗口必须完全结束于下一个数据集合开始之前。

不允许随机划分。

所有模型超参数和决策阈值必须在验证阶段确定，最终测试集只用于最后报告。

增加 Walk-forward Validation 作为可选高级模式。

---

# 6. Streamlit UI 设计

## 6.1 整体视觉规范

项目名称：**Encounter Lab**

副标题：**Can We Predict When Two People Meet Again?**

界面语言：中文优先，技术术语保留英文。

设计风格：

- 简洁、偏科研仪表盘。
- 默认深色模式，兼容浅色模式。
- 使用卡片、图表、表格和清晰的信息层级。
- 不要过多装饰性动画。
- 桌面端优先，兼容较窄窗口。
- 长时间计算显示进度。
- 所有重要指标附有说明。

顶部导航：

```text
Overview
Data Manager
Data Explorer
Encounter Network
Model Training
Prediction Lab
Model Evaluation
Data Sources
```

### 页面1：Overview

显示：

```text
Total Participants
Total Contact Events
Total Valid Pairs
Observation Days
Positive Event Rate
Active Model
```

主图表：

- 每天接触事件数。
- 每小时接触活跃度。
- 数据可用率。
- 当前实验状态。

提供：

```text
Load Dataset
Explore Data
Train Model
Open Prediction Lab
```

这些按钮必须能够导航到实际功能页面。

### 页面2：Data Manager

核心功能：

- 选择 Copenhagen / SocioPatterns。
- 查看数据来源。
- 一键下载数据。
- 下载进度条。
- 手动上传数据。
- 扫描本地文件。
- 字段检查结果。
- 数据质量报告。
- 一键运行预处理。
- 缓存状态。
- 错误和修复建议。

状态标识：

```text
Not Downloaded
Downloaded
Validation Failed
Ready
Processing
Processed
```

禁止出现点击后没有反应的假按钮。

### 页面3：Data Explorer

提供：

- 时间范围选择器（Study Day）。
- 用户ID过滤器。
- 配对ID过滤器。
- 接触频率分布。
- RSSI分布。
- 每日、每小时接触趋势。
- 用户活跃度排名。
- 历史见面次数热力图。
- 缺失数据和扫描覆盖率图表。

图表优先采用 Plotly，实现缩放、悬停提示和筛选。

### 页面4：Encounter Network

使用 NetworkX 构建历史接触关系图。

节点代表匿名参与者。

边代表预测时点之前发生的蓝牙接触。

要求：

- 用户可调整历史窗口。
- 节点大小与历史活跃度关联。
- 边宽与历史接触频率关联。
- 支持查找匿名ID。
- 支持点击节点查看历史统计。
- 支持仅显示Top-N节点和边。
- 网络过大时限制渲染规模。

不能使用未来接触数据构建某个历史时刻的关系网络。

### 页面5：Model Training

提供：

```text
Dataset Selector
Training Mode
Historical Window
Model Selector
Hyperparameter Settings
Time Split Preview
Training Button
```

模型选择：

```text
Logistic Regression
Random Forest
XGBoost
LightGBM
Run All Baselines
Compare All Models
```

实时显示：

- 训练阶段。
- 已完成步骤。
- 训练与验证分数。
- 训练耗时。
- 错误日志。
- 模型版本。

训练结束自动保存模型与实验配置。

### 页面6：Prediction Lab

这是项目最重要的交互页面。

用户选择：

```text
Person A: [匿名ID选择]
Person B: [匿名ID选择]

Prediction Day: [Study Day]
Prediction Hour: [时间]

Historical Window: [1 / 3 / 7 / 14 days]

Model: [已训练模型]
```

点击：

```text
Predict Encounter
```

输出：

```text
未来24小时内发生蓝牙接近事件的概率：

73.4%
```

必须明确标识这是示例或模型计算结果，不能在尚未运行模型时显示虚构概率。

附加展示：

```text
Historical Contact Count
Time Since Last Contact
Pair Activity Trend
Top Feature Contributions
Prediction Confidence / Uncertainty
```

历史回测模式可以在用户选择的预测时间之后展示：

```text
Actual Outcome: Contact / No Contact / Unknown
```

未来实验模式不能提前展示真实标签。

需要在页面顶部提醒：

「本系统预测匿名设备的近距离接触概率，不预测爱情、友谊或命运。」

### 页面7：Model Evaluation

必须包含：

- Baseline比较表。
- PR Curve。
- ROC Curve。
- Confusion Matrix。
- Calibration Curve。
- Brier Score。
- Log Loss。
- Precision、Recall、F1。
- 正例占比。
- Feature Importance。
- SHAP可解释性分析。
- 消融实验。
- 按接触频率分组评估。
- 不同历史窗口的预测性能曲线。

支持下载实验结果为CSV与HTML。

### 页面8：Data Sources

显示数据原始出处、引用、许可、字段定义与研究局限。

提供官方链接，避免误导使用者认为系统拥有真实身份数据或完整地理轨迹。

---

# 7. 模型评估标准

不要仅以 Accuracy 判断效果。

主要指标：

```text
PR-AUC
Brier Score
Log Loss
Recall
Precision
```

次要指标：

```text
ROC-AUC
F1
Accuracy
Calibration Error
```

输出完整测试报告，并保存随机种子、数据集版本、时间切分、超参数及特征配置。

需要实现以下实验：

**E1：Baseline对比**

判断机器学习是否优于简单历史频率。

**E2：历史长度消融**

分别使用1、3、7、14天历史数据训练和评估。

**E3：通讯特征消融**

对比是否加入历史短信、电话特征。

**E4：低频配对分析**

评估很少接触的两个人是否能够被预测。

**E5：概率校准**

检查预测概率是否与真实事件频率一致。

---

# 8. 必须实现的测试

Codex 在继续下一阶段之前，必须通过以下测试：

### Test A：Schema Validation

确认实际字段与加载逻辑匹配。

### Test B：No Future Feature

任何用于预测时间t的特征，都不能依赖t之后的数据。

### Test C：Label Correctness

使用人工构造的小型事件数据验证24小时标签。

### Test D：Temporal Split

训练、验证、测试严格按时间排列，不允许标签窗口跨越边界。

### Test E：Pair Symmetry

A-B和B-A应得到相同的无向配对结果。

### Test F：Missingness

没有观测到蓝牙信号，不等于必然没有接触。

### Test G：Model Pipeline

至少一个baseline和一个主模型可以完整训练、保存、加载与预测。

### Test H：UI Integration

确保界面能够使用真实模型结果，而不是占位数据。

---

# 9. Codex开发流程

采用严格的阶段式 Vibe Coding。

## Phase 1 — 初始化

Codex任务：

建立项目结构、虚拟环境、依赖文件、Streamlit导航和基础页面。

验收：

```text
streamlit run app.py
```

能够正常打开所有页面，无ImportError。

## Phase 2 — 数据下载

Codex任务：

完成Figshare API数据下载器和SocioPatterns数据加载器。

验收：

真实数据下载、读取、检查成功。

## Phase 3 — 数据清洗与EDA

Codex任务：

建立统一数据格式，完成Data Explorer和质量检查。

验收：

统计数量与论文规模大致一致，关键字段没有错误映射。

## Phase 4 — 标签与特征

Codex任务：

生成逐日预测快照，创建24小时标签，实施严格的历史特征构建。

验收：

时间泄漏测试全部通过。

## Phase 5 — Baseline

Codex任务：

实现基础模型与时间切分。

验收：

所有baseline能独立运行并输出指标。

## Phase 6 — Main Models

Codex任务：

实现XGBoost、LightGBM、超参数搜索与概率校准。

验收：

模型可以训练、保存、加载与预测。

## Phase 7 — Prediction UI

Codex任务：

完成用户配对选择、时间选择、预测概率显示以及真实历史回测。

验收：

页面正常显示模型计算结果。

## Phase 8 — Evaluation

Codex任务：

完成模型比较、PR曲线、校准曲线、SHAP和消融实验。

验收：

可以生成完整可复现实验报告。

## Phase 9 — 项目审查

Codex任务：

检查所有代码、数据流程、界面交互和测试。

验收：

```bash
python -m pytest -q
```

所有关键测试通过，且README中的运行步骤真实有效。

---

# 10. 给Codex的执行原则

你是负责完成 Encounter Lab 项目的AI工程师。

请遵守以下规则：

1. 首先读取本操作手册，理解完整架构。
2. 优先使用官方数据来源。
3. 不允许虚构真实数据、字段或实验结果。
4. 开始每个阶段前简要列出实施步骤。
5. 每完成一个阶段执行必要的验证。
6. 如果发生错误，先分析原因，再修改代码。
7. 不要为了让测试通过而删掉关键测试。
8. 不要通过未来信息提高预测分数。
9. UI必须连接真实后端功能。
10. 保留清晰、必要的代码注释。
11. 所有图表必须注明数据范围和指标定义。
12. 下载失败时提供可操作的恢复方式。
13. 大文件使用缓存与分块处理，避免内存耗尽。
14. 优先确保项目能运行，再进行性能优化。
15. 不要擅自扩大项目范围或引入不必要的复杂架构。
16. 不要一次性实现全部阶段。
17. 每完成一个Phase，报告修改文件、验证结果和剩余问题，然后等待下一步指令。

**现在只执行 Phase 1。完成后停止，等待我输入 next。**

---

# 11. 最终研究成果

项目最终应能够：

1. 下载并分析真实的人类接触网络数据。
2. 构建没有未来信息泄漏的预测数据集。
3. 根据两名匿名参与者的历史接触信息预测未来24小时的接近概率。
4. 比较不同机器学习模型的表现。
5. 量化增加历史信息对预测能力的影响。
6. 研究罕见或非规律接触是否具有可预测性。
7. 在交互式UI中展示模型结果。
8. 输出可复现的实验报告。

最终研究问题：

**How much historical information is needed to predict whether two people will encounter each other within the next 24 hours?**

中文：

**究竟需要多少历史信息，才能预测两个人在未来24小时内是否再次相遇？**

项目属于探索性研究，不预设90%准确率，也不声称能预测命运。
