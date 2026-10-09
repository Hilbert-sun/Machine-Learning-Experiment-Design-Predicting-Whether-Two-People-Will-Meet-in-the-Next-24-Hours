# Encounter Lab — 软件交付说明

验证日期：2026-10-09（Asia/Kuala_Lumpur）。

## 交付范围与状态

T01–T16的软件实现、完整测试和运行验证已完成。源码包含八个Streamlit页面、数据获取/验证/清洗、标签/历史特征、七个模型、校准/保存/加载、历史网络、预测和评估导出。Overview现已显示当前清洗缓存的实测统计，不再始终显示初始化占位值。

**研究实验尚未完成。** 当前真实SocioPatterns缺少可靠扫描日志，主要评估可用样本为0；项目没有真实研究模型、预测概率或性能分数。Copenhagen全量蓝牙未下载。通讯可用时间和星期约定未确认的字段保持未知；E3不填造分数。

## 复现与启动

在项目根目录、Python3.11和已有OpenMP运行库环境下：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
python -m pytest -q
streamlit run app.py
```

默认地址为 `http://localhost:8501`。`requirements-lock.txt`记录本次已验证环境的51个运行/测试包精确版本；`requirements.txt`保留允许范围。锁定环境已在Python3.11/macOS arm64验证，未声称在所有平台实测。macOS模型库若提示缺少libomp，按README使用已有Homebrew安装该运行库。

## 验收证据

完整测试：**168 passed in 8.13s**。`pip check`无依赖冲突；Streamlit1.65.0入口命令启动成功，根页面和健康接口均HTTP200；临时检查服务器已停止。八个页面的AppTest检查全部通过。

| 规范测试 | 主要证据 | 验证范围 |
| --- | --- | --- |
| A — Schema Validation | tests/test_schema.py、test_downloader.py | 实际表头别名、分隔符、gzip、数值/ID及畸形行检查 |
| B — No Future Feature | test_features.py、test_labels.py、test_network.py、test_prediction.py | 历史窗口、候选/网络仅用过去；未来事件不改早期特征；未来模式不读结果 |
| C — Label Correctness | test_labels.py、test_delivery.py | 合成原始事件验证 `(t,t+24h]` 的端点、正负与未知 |
| D — Temporal Split | test_leakage.py、test_calibration.py | 整时点分组、训练/验证/测试及校准/调参间严格清除跨界标签 |
| E — Pair Symmetry | test_preprocessing.py、test_prediction.py | 规范化无向配对、班级与端点对应、逆序配对一致 |
| F — Missingness | test_preprocessing.py、test_labels.py、test_data_manager.py | 空扫描保留；低/未知覆盖不改成负例；无可靠分母不显示正例率 |
| G — Model Pipeline | test_training.py、test_main_models.py、test_calibration.py、test_delivery.py | 实际估计器训练/校准/保存/加载/预测；原始合成扫描贯通整个流程 |
| H — UI Integration | test_ui.py、test_training_ui.py、test_prediction.py、test_evaluation_ui.py、test_delivery.py | 页面用实际计算结果；缓存/范围变化失效；缺少模型时不造概率/分数 |

模型测试使用明确标识的合成样本；这里的“实际估计器”不是对真实研究效果的声明。原始扫描端到端测试直接调用真实标签、特征、校准、模型保存、预测及冻结最终评估代码，没有跳过这些步骤。

## 真实本地数据检查

- 已有SocioPatterns清洗缓存：327名参与者、188,508条接触记录、5,818个有效配对、5个Study Day。
- 现有标签/特征：10,742行，其中4,023个有正接触证据、6,719个未知；主要评估可用为0。Overview正例率显示“未知”，模型状态为“未训练”。
- 真实关系网络能渲染；Prediction Lab和Model Evaluation没有真实模型产物时保持可操作的空状态。
- Copenhagen仅先前的小片段和电话/短信/说明文件核对过；不能据此声称其全量蓝牙验证或训练成功。

本地机器可查看忽略的 `reports/delivery_ui_check.json`、`reports/delivery_startup_check.json` 及之前各阶段验证记录。新克隆不包含这些机器产物，应自行执行验证。

## 数据来源与使用条件

- Copenhagen：Sapiezynski、Stopczynski、Lassen、Lehmann（2019），[Figshare官方数据/许可](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433)，[数据DOI](https://doi.org/10.6084/m9.figshare.7267433)，[论文](https://www.nature.com/articles/s41597-019-0325-x)。数据页标注MIT；论文许可单独按论文页面核对。
- SocioPatterns：Mastrandrea、Fournet、Barrat（2015），[官方数据/许可](https://sociopatterns.org/datasets/high-school-contact-and-friendship-networks/)，[论文及引用](https://doi.org/10.1371/journal.pone.0136497)。官方数据为CC BY-NC-SA，应保留署名及非商业/相同方式共享条件。

应用Data Sources页包含出处、真实字段、许可与研究局限；数据匿名，不包含真实身份或完整地理轨迹。Bluetooth接近和RSSI不等于交谈或精确距离。

## 开始真实实验

1. Data Manager选择Copenhagen，从当前Figshare清单选择真实主文件 `bt_symmetric.csv`；文件名、大小、MD5以API为准。当前交付不自动下载大文件。
2. 验证、预处理、生成24小时标签和历史特征；检查实际覆盖率、有效正负目标及历史长度。不能为了启动训练而把未知改成负例。
3. Model Training先查看实际时间切分和清除数量，选择模型/历史窗口/校准。模型与实验记录保存在本地忽略目录。
4. Prediction Lab使用窗口匹配且在预测时刻之前完成选择的模型；回测才显式读取结果。
5. Model Evaluation在验证集确定实验方案，最终测试仅报告冻结模型；导出保留来源、范围和实验状态。

Candidate Pair扩展、可选walk-forward、可靠通讯可用时间接入、星期原点确认及Copenhagen全量性能/研究实验不在本次已验证成果中。请将后续真实实验视为新任务，不把软件测试当成研究结论。

## 仓库与本地文件

GitHub目的地：[Encounter Lab仓库](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours)。最终发布提交由Git历史记录。

源码、配置、文档、测试和空目录标记是提交范围；原始/衍生数据、模型权重、特征/标签、报告、虚拟环境和密钥均忽略。GitHub同步作为本次最终交付的最后步骤，最终结果记录于PROGRESS.md及执行回复。
