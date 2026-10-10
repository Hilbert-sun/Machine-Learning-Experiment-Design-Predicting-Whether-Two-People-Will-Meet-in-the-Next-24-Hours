# T29 — Time Machine 历史预测模拟器

在顶部导航打开 **时间机器 · Time Machine**。此页面独立于 Window Study，不需要先运行离线研究。T29只新增交互流程，不训练模型、不新增评估指标、不修改T17–T27冻结实验。

## 操作流程

1. **Select**：选择来源、已保存模型族、1/3/7天窗口、Study Day/小时及匿名A/B。候选只来自`[t-1d,t)`，不读取旧评估队列或未来覆盖筛选后的特征库。来源缺数据、无可核实模型或预测时间不晚于模型截止时间时，会显示具体阻碍。
2. **Predict**：仅调用T28 `predict_as_of`。查看真实模型概率、过去接触次数/接触bins/最近接触间隔/网络等历史统计。模型表显示标签信息截止时间，详情可查看训练、验证、阈值等分项截止时间。缺扫描或不匹配的模型契约会拒绝，缺失统计保持未知。
3. **Freeze Prediction**：预测成功后才可点击。冻结会话内的预测JSON及SHA256，包含选择版本、模型版本/校验值和各窗口结果。Freeze不再次计算概率，也不读取未来结果。
4. **Reveal Next24h**：冻结后才可点击，且只适用于历史回放。独立调用T28 `reveal_outcome(...,backtest=True)`，不重新拟合或计算概率。

`Contact`：未来`(t,t+24h]`存在实际接近记录。`No Contact`：未来窗口完整，两端扫描覆盖达到标准且未记录接触。`Unknown`：窗口不完整、扫描缺失或覆盖不足，无法把未见记录当作可靠负例。页面给出判断依据；扫描覆盖仍是可用性代理，不保证持续在线或绝对没有遗漏。

再次Predict会清除旧Freeze/Reveal状态。重复Reveal在同一版本内复用已揭晓结果，冻结概率与摘要不变。离开/关闭会话可能丢失记录；T29没有将个体预测自动保存到磁盘或上传GitHub。

## 选择与版本失效

日期/小时、配对、来源、模型族、历史窗口、推理模式，以及来源快照/模型文件/时间证据版本，都参与上下文标识。修改它们会清空当前预测、冻结和揭晓状态，必须重新完成流程。源文件不可用、来源不支持推理或模型截止时间冲突时，同样清除旧状态，避免在新选择下显示旧结果。

数据版本使用已验证快照的目录、报告及普通文件系统版本标记（大小/mtime_ns），不扫描未来标签或未来观测内容。模型版本含清单/权重/证据文件标记；预测包还记录实际模型artifact version/SHA256。每次动作前后复查版本，发现普通并发更新即拒绝关联结果。更强的原子快照、采集到达日志与性能缓存属于尚未开始的T32。

**未来数据更新有两种不同含义**：旧冻结记录内容不被改写；当前数据版本变化使活动记录失效。若随后重新预测，T28仅使用`t`之前历史，同一时点的候选、特征和概率不受未来记录变化影响。新记录的选择版本会变化，这是审计版本变化，不是预测变化。

## 历史与实时模式

默认`historical_blind_replay`按记录的事件时间模拟历史预测。当前主模型在Study Day24及以后才满足其已保存选择信息截止时间；更早日期需要当时已经可用的模型，不能将后来训练的模型拿回过去。

`prospective_inference`必须通过T28的可信UTC时间锚点及两端近期扫描检查。静态Copenhagen档案没有核验的实时锚点，页面会明确拒绝，并且不允许Reveal充当实时结果。本任务不提供手填日期冒充认证时钟的控件。底层服务保留传递可信`clock_anchor/now_utc`的接口，实际实时来源仍需未来任务的采集/来源验证。

历史事件时间不等于当时实际上传/可用时间；当前资料没有完整采集到达日志。UI操作顺序不能使此前已经看过的历史结果重新成为独立盲测。旧模型仍来自未来覆盖可评估子集，其AP/概率校准不能直接保证全部as-of候选的表现。T30将独立审计该选择偏差，T29未开始这些研究。

## 实现与验证

- 页面：`pages/10_Time_Machine.py`，通过`src/ui.py`加入顶部导航。
- 状态/服务：`src/time_machine.py`。`TimeMachineSession.select/predict/freeze/reveal`强制顺序，保存不可变序列化副本，揭晓前校验冻结摘要。
- 展示：`src/time_machine_ui.py`，复用T28模型发现、候选、特征和推理，不调用旧`window_ui.case_keys/predict_case`或离线训练。
- 专项测试：`tests/test_time_machine.py`、`tests/test_time_machine_ui.py`；沿用T28测试进行无网络的小型合成模型/Parquet回归。

```bash
.venv/bin/python -m pytest -q tests/test_time_machine.py tests/test_time_machine_ui.py tests/test_asof_inference.py tests/test_asof_ui.py
.venv/bin/python -m pytest -q
.venv/bin/streamlit run app.py
```

完整任务验证结果见`PROGRESS.md`。T30–T34已登记为TODO，尚未实施；完成T29后停止等待`next`。代码和说明安全提交并推送至`research-v2.2`，不合并main，原始数据/模型/逐样本结果始终排除于Git。
