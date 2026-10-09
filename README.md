# Encounter Lab — 相遇实验室

使用公开、匿名接触数据，研究两名参与者未来 24 小时内发生设备近距离接触的概率。项目按 `TASKS.md` 逐项开发。T01–T04 已完成：环境安装、八页面导航、原始数据下载/上传、分块读取与字段验证。尚未具备数据清洗、训练或预测功能。

## 环境安装

需要 Python 3.11。在项目目录执行：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q tests/test_environment.py
```

macOS 上 XGBoost / LightGBM 需要 OpenMP 运行库。如果导入提示找不到 `libomp.dylib`，可使用已有 Homebrew 安装：

```bash
brew install libomp
```

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
src/                   下载器、源文件读取与共享 UI
tests/                 环境、下载、字段验证与界面测试
```

默认深色主题，可通过 Streamlit 设置切换浅色主题。尚未接入的功能显示明确空状态，指标显示「—」。数据管理读取 `configs/default.yaml` 中的原始数据路径。数据、衍生数据、模型、报告、虚拟环境与密钥均通过 `.gitignore` 排除；空目录标记保留。

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

本次真实验证覆盖完整 calls.csv、sms.csv 和 SocioPatterns 接触文件。Copenhagen 蓝牙仅验证了最多8 KB的真实源片段，未下载或验证其全量文件；没有生成虚构实验结果。本地验证记录保存在忽略的 `reports/`，原始数据不会上传 GitHub。新机器需通过 Data Manager 自行下载数据。

运行当前测试：

```bash
python -m pytest -q
```

## 开发约束

先读 `PROJECT_SPEC.md`、`AGENTS.md`、`TASKS.md` 和 `PROGRESS.md`，每次只执行一个明确任务，通过相关验证后更新进度并停止。所有数据字段应由真实源文件验证，所有预测和指标应来自实际运行；不得使用未来信息构建特征或候选配对。没有观测不能直接当作没有接触。
