# Encounter Lab — Product and Research Demonstration

Start with `streamlit run app.py` in the verified Python 3.11 environment. Keep individual pair details local; do not publish screenshots with participants or probabilities. No screenshots or per-sample demo files are included in this delivery.

## 无私有数据的产品演示

1. 从 Home 点击“开始偶遇预测”，首次访问确认原生欢迎弹窗。
2. 使用明确虚构的七项粗粒度回答：朋友、步行可达、过去30天3–5次、最近7天、区域偶尔相同、时间偶尔相似、没有见面约定。固定规则结果为66 /100（中等）；这不是模型概率。
3. 点击“查看我的偶遇分析”，阅读实际 Keyword 卡片、因素图与 A/B 线索图。可选共同熟人仅生成一个汇总节点，指数不变；触屏用节点说明选择器查看来源。
4. 修改距离为经常处于同一建筑或区域，重新提交得到71 /100；未提交前旧分析失效。重置后个人分析提供引导。
5. Explore 的公开标签无需问卷、原始数据或模型。展示 Copenhagen 同队列窗口图与 Workplace 聚合活动；MIT 不生成日趋势，Social Evolution 显示不可用。
6. 从全局 Research 进入分类目录，查看原训练/评估/Time Machine 入口和按需科研概览，再用 Home 返回。演示不运行训练、下载或私有预测导出。

导航是四个全局入口、Research 分类和15个注册页面；原12条科研路由保留。390/768/1440px实际浏览器检查已记录在 [产品交付说明](PRODUCT_DELIVERY.md)，不代表实体设备或全面无障碍认证。

## 有匹配本地研究材料的五分钟演示

| Time | Action | Evidence and explanation |
| --- | --- | --- |
| 0:00–0:40 | Home → Research → 打开科研概览, then Dataset Catalog | Predict recorded anonymous-device proximity within 24 hours. Show which lawful local sources exist and why contact-only archives cannot supply reliable negatives. |
| 0:40–1:30 | History Window Study with existing frozen default run | Show 1/3/7-day shared-cohort comparisons. Seven-day XGBoost AP 0.691366, four dates, 25,569 samples; bounded inputs and same labels make this comparison meaningful. Do not change settings/train. |
| 1:30–2:10 | Open ASOF_AUDIT.md alongside the app | T30 has no dedicated navigation page. Show 38,005 candidates, 10,185 Unknown, 27,802 prediction/label intersection. Higher AP with changed prevalence and worse Brier is not a same-population improvement. |
| 2:10–3:30 | Time Machine | With matching private saved models, select a supported historical Study Day after model deadlines, pair and 1/3/7-day windows. Predict → Freeze → Reveal. Explain historical features, frozen coverage policy, Contact/No Contact/Unknown and version invalidation. Do not enable prospective mode for an old archive. |
| 3:30–4:20 | Multi-Dataset Exploration | Show workplace fixed-rule Top-K Observed Positive Retrieval and source-specific graphs. No unobserved negatives, no binary AP/Precision; MIT tick mapping and Social Evolution remain unavailable. |
| 4:20–5:00 | GitHub Actions | Open the latest branch workflow run; verify exact commit SHA and all three jobs. Distinguish public synthetic/aggregate checks from private research reproduction. |

Public-only alternative: show reviewed [window metrics](../reports/window_study/T22_METRICS.csv), [T30 audit](../ASOF_AUDIT.md), [T31 study](../MULTISOURCE_STUDY.md) and meaningful UI empty states. Do not present fixture probabilities as genuine results. A deliberately synthetic AppTest demonstration must be labeled synthetic fixture, never a real-data experiment.

All15 registered paths, including the original12 research routes, are in [README](../README.md). Data Manager downloading and legacy training are explicit user actions, not prerequisites for public tests. No acquisition, model fit or new export should occur during this demo. For local source/model/version prerequisites and verification commands see [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
