# 补充研究（T35–T37）

三项研究都只读冻结的 T19 队列和 T20 特征，不改动 `reports/` 中的冻结证据。逐样本结果只保存在本地被忽略的 `data/processed/`，这里只放公开聚合结果。

| 研究 | 内容 | 关键结果 |
| --- | --- | --- |
| [T35 滚动起点重评估](rolling_validation/README.md) | 协议不变，改为滚动起点，得到 11 个测试日；增加按人排序指标 | 7 天 XGBoost 合并 AP 0.662，比 1 天高 +0.090 |
| [T36 Hawkes 基线](hawkes_baseline/README.md) | 不用标签、按配对拟合的指数核自激过程 | 合并 AP 0.629，比 XGBoost 低 0.033 |
| [T37 Hawkes 特征](hawkes_features/README.md) | 把 Hawkes 分数作为 XGBoost 的输入 | +0.003，可以忽略 |
