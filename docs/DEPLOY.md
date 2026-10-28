# 在线演示部署（Streamlit Community Cloud）

当前线上地址：<https://hjm59payrde6ronekgiqsn.streamlit.app/>（2026-10-28 部署，入口为 `demo_app.py`）。

在线演示必须使用 [`demo_app.py`](../demo_app.py) 作为入口，**不要用 `app.py`**。`demo_app.py` 默认锁定：只开放首页、Play、Explore、科研中心目录和数据来源说明，这五个页面只读取仓库里已审查的公开文件。其余 10 个科研页面（数据管理、训练、预测、Time Machine 等）在线上只显示"需本地运行"的提示，不渲染下载、导入、训练或选择控件，也不会在服务器上执行任何操作。锁定范围定义在 [src/demo_mode.py](../src/demo_mode.py)，由 [tests/test_demo_mode.py](../tests/test_demo_mode.py) 逐页验证。

部署环境中没有 `data/` 和 `models/` 的真实内容，也不应该上传任何原始数据、模型或逐样本结果。

## 部署步骤

1. 用 GitHub 账号登录 <https://share.streamlit.io>，授权它读取本仓库。
2. 点击 **Create app** → **Deploy a public app from GitHub**，填写：
   - Repository：`Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours`
   - Branch：`research-v2.2`
   - Main file path：`demo_app.py`
   - App URL：可自定义，例如 `encounter-lab`
3. 打开 **Advanced settings**，Python version 选 **3.11**。不需要填写任何 Secrets。
4. 点击 **Deploy**。首次构建需要安装依赖，并按 [packages.txt](../packages.txt) 安装 libgomp1，通常需要几分钟。
5. 部署完成后打开链接，检查：首页的 Play、Explore 可以正常使用；直接访问 `/Data_Manager` 等科研页面时显示"在线演示只开放……"的提示。

## 注意

- 访问者在 Play 中填写的问卷只保存在服务器当前会话，刷新即清空，不写入磁盘。
- Community Cloud 的应用长时间无人访问会休眠，再次打开时需要等它唤醒。
- 每次向 `research-v2.2` 推送，线上应用都会自动重新部署。
