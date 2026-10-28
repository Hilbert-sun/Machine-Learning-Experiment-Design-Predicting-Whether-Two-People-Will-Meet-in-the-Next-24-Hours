# Encounter Lab — Latest Progress

Date:2026-10-28

**T35 — DONE：滚动起点重评估与按人排序指标。** 用户选择先补强基线：先做新的滚动验证，再单独做 Hawkes 基线（T36，TODO）。

- 新增 src/rolling_validation.py、tests/test_rolling_validation.py、studies/rolling_validation/{README.md,T35_RESULTS.json}。没有修改冻结的 window_study/window_features/model_registry/evaluate/baselines，也没有改动 reports/ 白名单或安全基线。
- 协议与折计划先冻结、后拟合。20 个队列时刻中，11 个满足条件并完成评估（研究日 17–27），9 个历史不足；没有拟合失败。真实运行约 3 分 47 秒。
- 结果（合并 AP）：7d XGBoost 0.6619，3d 0.6120，1d 0.5716；7d logistic 0.5907，7d historical_frequency 0.4762。7d−1d XGBoost 差 +0.0902，95% 日块区间 [0.0728, 0.1033]，11/11 天为正；7d XGBoost−logistic 差 +0.0712，区间 [0.0275, 0.1238]，9/11 天为正。按人 NDCG@5 为 0.7856（3,350 个单位）。
- 限制：测试日都曾被看过；区间只描述日间波动；与 T22 总体不同，AP 不能直接比较。
- 验证：tests/test_rolling_validation.py 4 passed；`python -m src.rolling_validation --verify-only` 从本地预测重算公开 JSON，一致。两次独立的完整重跑得到逐样本完全相同的预测。公开 JSON 的哈希字段改名为 cohort_rows_sha256，以免触发 Gitleaks generic-api-key 误报，没有扩大豁免。全量 pytest 504 passed；final_audit PASS（51 份冻结材料不变）；仓库安全扫描和 Gitleaks 历史/索引扫描均 PASS。

下一步建议：T36 Hawkes 自激过程基线，复用本冻结折计划；需要用户授权。

## Earlier record

Date:2026-10-13 (Asia/Kuala_Lumpur)

**REPORT-FULL — DONE：本地正式报告及内容/排版验收完成；发布以本报告提交自己的三项CI为准。** 本轮仅生成报告。审阅基准478a320在main与research-v2.2一致；研究分支CI38130816756及main CI38131208638均已复核500全量/71 Smoke/27安全/12原生检查通过。无重训练、数据下载或新功能。

## 交付与证据

- deliverables/Encounter_Lab_Full_Report.md：正式完整中文报告；正文13,540个汉字（含标题/表图说明，排除重复图alt、摘要、文献及附录），451字摘要，11章、附录A-G、9图、15表、21参考文献。覆盖T01–T34/P01–P03，严格区分T17/T22/T30总体、描述检索与规则娱乐指数。
- deliverables/Encounter_Lab_Full_Report.pdf：本地39页A4纵向，约2.5cm页边距，嵌入常规宋体/黑体，正文12pt/18pt行距、首行24pt；编号目录、三线表、黑白矢量图、统一页眉页脚。为避免中文标点悬挂，正文右侧保留一个汉字宽度；不改变字号或增加彩色元素。PDF通过本机Git exclude精确排除，不进Git，未修改.gitignore/白名单/安全规则。
- deliverables/EVIDENCE_MAP.md、REPORT_VERIFICATION.json：章节证据映射、公开来源与代码SHA256、指标/目录/字体/颜色/页边距检查记录。参考文献外部条目在官方数据页、出版社、作者论文或技术文档核验；内部报告保留文件/版本追溯。
- deliverables/Encounter_Lab_Report_Figures/：9幅纯黑白SVG。数据图由T17/T22/T30/T31公开JSON/CSV生成；其他图明确为源码结构示意，不包含真实参与者。build_report.py/verify_report.py是独立报告生成/校验工具，不属于应用运行或科研拟合通路；复用现有文档运行环境，项目依赖不变。
- README仅新增报告索引；AGENTS/TASKS/PROGRESS同步当前单任务范围。可选DOCX未生成，Markdown为可编辑源。

## 实际验证

- 独立报告校验PASS：T22/T30 JSON-CSV与T32算术对账；T17及窗口附表独立取值核对；T31共同7d频率Top20命中/分母核对。21条正文引用与文献条目对应。图表不使用合成实验数据冒充真实结果。
- 最终PDF39页全部实际渲染；查看全页联系图及封面/目录/关键表图放大页。最后改动仅附表窗口排序，像素比较确认仅第38页变化，已重新查看。全部文字为黑色、绘图为黑白、渲染无彩色像素、白纸背景；中文字体嵌入及字形预检通过，无方框/替代乱码；逐页页码、目录及书签对应真实页码，文本不越出页边距检查。
- .venv/bin/python -m pytest -q tests/test_documentation.py tests/test_final_audit.py tests/test_repository_safety.py：72 passed in2.79s。python -m src.final_audit PASS，51份冻结材料不变。2751个预检对象中2747个保持原样，仅AGENTS/TASKS/PROGRESS/README四个授权当前文档改变；所有原源码、测试、配置、依赖、安全策略、数据、模型、报告均未修改。
- 新增15个文本交付文件（Markdown/JSON/Python/SVG）经现有check_content安全预检PASS；PDF保持本地。发布前继续执行真实Git-index与固定Gitleaks历史/索引/服务商风险自检；只推research-v2.2并等待本报告HEAD三个CI Job completed/success。最终SHA/运行URL由执行回执给出，不增加未验收的自引用元数据提交。

## 修正与剩余范围

排版调试中的KeyError('scope')源自报告脚本误读实际population列，已按真实CSV修正；初次宋体字体面偏重已换成Regular；中文悬挂标点超边界及附表窗口排序已修正并重渲染/重验。Poppler最初字体缓存路径不可写，改用本机临时fontconfig后无渲染错误。没有未解决测试或排版失败。

本次不重新跑真实模型/原始数据复现，不重做性能实测或浏览器设备测试；报告引用这些已验收历史材料并明确其范围。无机构、导师或发表身份推测。只有4个主要窗口测试日、观测代理、Unknown、时间单位/来源不可用、未验证跨群体/实时泛化仍是项目科学限制。

下一步：完成本报告的安全研究分支发布与对应CI核验后STOP，等待用户审阅；不自动开发或创建新研究任务，不合并main、发Tag/Release或部署。

## Earlier accepted documentation/product evidence

**DOCS-P03 — DONE：README 与配套文档补齐及本地验证完成。** 用户本次仅授权完善文档并推送。P03 已在 `390384ca27b9e9e89788a6d17e5c436552d28873` / [Actions38115466252](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38115466252) 正式验收，三个 Job completed/success；500全量、71 Smoke、27安全、12原生依赖检查。维护前核验的远程 research-v2.2 与该 SHA 相同，main 仍为820d080；本轮不修改任何功能或科研结果。

## 本轮范围

README 补充明确开发分支、可直接执行的克隆/安装/启动、不同入口的材料要求与文档索引；产品交付/计划/Explore/CI 记录正式 P03 验收；演示指南、交付清单及作品集同步四入口/15页产品结构。任务与长期指令限定为文档维护。

本轮实际检查：.venv/bin/python -m pytest -q tests/test_documentation.py tests/test_final_audit.py tests/test_repository_safety.py：72 passed in2.88s。python -m src.final_audit PASS，51份冻结材料不变；pip check 无依赖冲突。2751个预检对象中，仅11份授权 Markdown 文档改变，2740个原有对象保留；所有源码、测试、配置、安全规则、数据、模型及报告不变。没有新增测试、浏览器实测或模型实验；原 P03 浏览器记录仅作为历史已验证证据保留。

发布步骤：精确 Git-index 与 pinned Gitleaks 检查成功后，安全提交推送 research-v2.2 并核验本维护提交自己的三个 CI Job及远程 SHA。最终维护提交/Actions 回执由本次执行回复给出；上述500/71/27/12是已发布 P03 的实测记录，不能代替新提交的 CI。每个新提交的验收都依赖其实际成功状态，不在文档中预填未来运行编号。

下一步仅完成本轮发布验证，随后 STOP，等待用户最终验收；不自动创建产品或研究开发任务。

## 已验收的 P03 交付记录

**P03 — DONE: final publication verified at390384c / [Actions38115466252](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38115466252).** All three mandatory Jobs completed/success;500 full,71 Smoke,27 safety,12 native checks. The following implementation notes are historical P03 evidence. Baseline bb05d4ae709e64643a3d436aeeb7e73f880b6202, accepted P02 Actions38111188664. Only P03 is authorized; P01–P03 end here, with no next task, training, download, main merge or release.

## Implemented and preserved

- app.py/src/ui.py:15 registered routes, four native global page links. Original12 route tuples remain unchanged. Lightweight pages/14_Research_Hub.py groups all original tools with Chinese explanations and links to existing reports/reproduction.
- pages/0_Overview.py: pure public Home with headline and three cards; Play primary action. Research statistics move to opt-in src/research_overview_ui.py using identical original rendering body and unchanged src/overview.py. Home and unopened Hub never scan raw/model inventories, including after a previous opened research visit.
- src/product_ui.py shares actual Keyword cards and display-only figure styling; Play groups seven existing questions and emphasizes result→full analysis→edit/reset. No scoring/state privacy changes.
- Explore uses two native tabs, preserves exact src/encounter_insights.py loaders/calculations and real T22/T31 values. src/encounter_graph.py changes presentation only: padded fixed axes, outward/wrapped labels, smaller title; deterministic positions/edges/points remain identical. Touch node selector and restore/removal guards expose descriptions without hovering.
- P01 pure scoring/welcome bytes, scientific training/features/labels/evaluation/inference/model code, datasets, reports and model weights are unchanged. No cache/URL/log/export/persistence for questionnaires, new JS/CSS/framework/third-party tracking or security-policy edits.

## Observed local verification

- Focused product/navigation/P01/P02/old-route tests:127 passed in5.63s; product/documentation checks50 passed in2.92s. New dedicated product tests24; existing navigation/docs parametrization adds3 more cases, taking473→500. Old tests retain every scientific/business assertion; only access steps/page totals change.
- Full .venv/bin/python -m pytest -q:500 passed in37.33s. Workflow-equivalent ten-file Streamlit Smoke:71 passed in9.14s. Safety rejection tests27 passed in1.20s. pip check: no broken requirements.
- Public final_audit PASS:51 frozen files unchanged, correct distinct research populations. Preflight2745 file hashes: authorized UI/tests/current docs only changed;0 pre-existing data/model/report changes. Original Overview calculation/render body matches P02 after relocation/indentation. CI/security files are byte-preserved.
- Actual browser390/768/1440px: four-entry navigation and responsive Home/Research; fictional seven-answer flow66→Explore66→edit(no stale index)→resubmit71; mutual summary/touch description/A focus/restore; Research roundtrip and reset; normal full same-tab refresh did not repeat welcome (dialog count0). Empty personal guidance, real Workplace public charts, MIT unknown-time and Social unavailable states checked. Training/Evaluation/Time Machine opened without running actions. No page-wide horizontal overflow at the measured three widths. Detailed evidence/limits in PRODUCT_DELIVERY.md.
- New navigation tests explicitly exercise the actual modern-router entrypoint despite AppTest resetting legacy directory detection between runs; no production testing bypass. Existing standalone research/UI and welcome tests remain enabled. Initial focused failures were corrected: moved-renderer import binding under tests, new test input type and AppTest entrypoint selection. No known failed test remains.

## Verified publication and final-head gate

Code candidate `4e0476d060497aaea70dfdba408548049c6bbec7` was safely pushed to research-v2.2 and [Actions38115216049](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38115216049) completed/success for unit-tests, streamlit-smoke and repository-safety. Linux logs show500 full tests in92.88s,71 smoke in25.70s,27 safety in0.48s and12 native imports in2.25s. Exact Git-index scanner PASS:216 files/44 approved reports/51 frozen objects; pinned Gitleaks full-history/index/provider-risk self-test PASS, locally and remotely. Preflight hashes confirm2728 protected existing objects unchanged, with only17 authorized UI/tests/current-document changes; old modified test names and assertion counts preserved.

Final P03 status commit `390384ca27b9e9e89788a6d17e5c436552d28873` subsequently passed [Actions38115466252](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38115466252) with500 full tests in114.63s,71 Smoke in23.17s,27 safety in0.52s and12 native checks in2.01s. Remote HEAD matched headSha. P03 acceptance is complete; no pending gate remains for that published version. Later maintenance needs its own current-head CI. No main merge/tag/release/deployment. Local preview is bound only127.0.0.1; no private screenshots/inputs are published. Stop and await final user acceptance; do not create P04/T35.

## Earlier P02/T34 evidence (historical)

**P02 — DONE locally; remote acceptance requires this final P02 commit's own three completed/success CI jobs at exact remote HEAD.** Baselineab4dc3f20e5bcd587a5d4caf5611f5bc3fb0afbb / P01 Actions38108921172 (433 unit/69 smoke/27 safety). Only P02 is authorized; P03 remains TODO. No new data, model fit, experimental result export, main merge, tag/release or deployment.

## Implemented

- pages/13_Encounter_Insights.py and src/encounter_insights_ui.py: independent Explore page, personal analysis and public group stories visibly separated. All12 research pages and P01 remain registered (14 total).
- src/encounter_insights.py: validate current submitted P01 result against unchanged evaluate_questionnaire; no second formula. Missing/stale/ineligible submissions get guidance, no personal example index. Cards and factor chart consume actual Keyword fields; unknowns remain separate, not0. Group window comparison reads/reconciles T22 JSON/CSV, common cohort/protocol/sample/prevalence/date counts; all narratives derive from actual metrics. T31 source/network counts reconcile JSON/CSV; only verified relative daily records render; suppressed/null values remain gaps, genuine public0 remains only a record count. MIT unknown ticks/Social unavailable get no fabricated curves. Copenhagen window chart is explicitly independent of the group selector.
- src/encounter_graph.py: private self-report-only A/B clue graph with canonical seed42/80-iteration layout, dark style, soft edges, hover/click descriptions, A/B focus/restore. Known weak cues are labeled as weak, unknowns omitted. Optional mutual-acquaintance range creates one aggregate node, never fake individuals; summary has no score and fixed display size. Actual graphs<=8 nodes/12 edges, hard caps15/30. Research provenance is rejected by this renderer; real historical networks use a separate explicit entry to the unchanged existing page, never default Parquet scans or invented aggregate edges.
- Play result button enters Explore; modify/reset clears old Explore-only mutual/focus state and invalidates old personal analysis. No private st.cache_data, shared session cache, URL data, logs, export/database/API. Public aggregate cache reuses existing content versions/deep copies only.
- Overview has Play/Explore/Research entries. The original six indicators, charts and data/training links load only after 深入研究; 收起科研概览 hides them. Default home makes no raw/processed/model scan. Existing research model/statistics logic is untouched.
- README, PRODUCT_PLAN, EXPLORE_GUIDE, task/session/progress files updated incrementally. P01 scoring/welcome and research report/CI/safety sources unchanged.

## Actual tests and verification

- New P02 logic/graph/UI suite:37 passed in2.06s. Covers unknown/stale/reset/session isolation, score/relationship preservation, data-driven stories/cohort conflicts, null/suppression/unavailable/time guards, deterministic graph/focus/summary-only friends/bounds/empty/single/edgeless/click validation, lazy homepage, and byte-identical P01 rule/welcome sources.
- Focused P02/P01/navigation/documentation/delivery suite:92 passed in4.30s.
- Full pytest:473 passed in35.54s (original433 +37 dedicated new cases +3 expanded navigation/document cases). Original research and P01 tests/guards retained; no skips or removed assertions.
- Workflow-equivalent smoke:70 passed in9.51s, exercising all14 navigation pages and the original interaction/security boundary cases. Public audit PASS:51 frozen files unchanged. Repository safety regressions27 pass; exact staged-index scanner PASS (210 files,44 approved reports,51 frozen objects), pinned Gitleaks full history/index plus provider-risk self-test PASS; pip check passes. Exact remote CI totals are still gated on this new P02 SHA and attested in the final reply.
- Real browser: homepage three entries; no-questionnaire guidance with genuine public charts; virtual questionnaire Play→Explore keeps index unchanged; optional mutual range does not change it; visible A-label focus, node click details and default restore work; modify→resubmit updates displayed result; P01 reset removes personal index/optional fields. Welcome does not repeat in navigation or final same-tab reload. Actual MIT/Social source switching shows the expected unverified-time/unavailable states without invented curves. 深入研究 exposes the actual original indicators; collapsing hides them.
- Actual390px narrow viewport: homepage entries stack legibly and clue graph/controls remain usable. Viewport restored afterward. Only public homepage screenshot saved outside Git; fictional personal inputs were checked live, with no filled-form/personal graph export.
- Preservation inventory2737 files;2725 protected pre-existing files unchanged except12 authorized current UI/doc/test files. P01 scoring/welcome and original data/models/statistical sources/frozen reports unchanged. The public frozen51-file check and unchanged CI/security policy remain enforced.

## Failures and compatibility repairs

Adding a page_link from a standalone P01 test script failed3 existing cases because the new navigation target was not registered in that single-file entry. A normal button-triggered switch_page preserves standalone scoring and works in the registered app; all old score/edit/reset assertions remain. AppTest retains its explicit page hash after a programmatic switch; the new integration test first asserts the actual rendered target, then binds that observed target for subsequent widget events. Real browser navigation independently passed.

The initial full suite had1 failure/472 passes: old delivery test expected immediate Overview metrics. It now explicitly opens Research and retains all original real six-value, three-chart and stale-cache assertions. An additional visual review removed a misleading arbitrary points field from the mutual-summary marker; it now has a fixed size/no score and regression assertions. A native radio-input click did not toggle in the browser harness; clicking its visible A label worked and the checked state was verified, with node details independently tested. No formula, security policy or scientific assertion was weakened.

## Boundaries and remaining limitations

The A/B diagram is self-reported clue association, not a social network, causal attribution, SHAP or observed GPS/schedule evidence. Optional common acquaintances are only user-described summaries. Spring positions are deterministic/static, not draggable-node live physics. No inline real research network is synthesized from aggregate counts; the explicit old-page entry needs lawful verified local caches. No hour-level source exists here, so no invented heatmap/word cloud.

T22 is the fixed Copenhagen population with only4 main test dates; AP is a ranking metric, not a person's encounter probability or generalization/significance proof. T30 selection/Unknown and T31 positive-only retrieval/T32 stable-archive/performance limits remain intact. Null/suppressed counts are not zero; public0 is not proof of no contact or continuous observation. MIT tick mapping and Social Evolution availability remain unresolved as before. P01 welcome refresh/storage limits are unchanged. No private questionnaire or real participant identities are published.

## Publication and STOP

Run final public/frozen/safety/secret checks, commit safe P02 source/tests/docs, push research-v2.2 only and verify the new exact remote-head three-job CI. Record final run/SHA/counts in the execution reply, not a new untested receipt commit. On failure retain IN_PROGRESS/BLOCKED and repair/reverify. STOP after P02; do not execute P03 without a new instruction.

---

## Previous P01 delivery record (historical)

# Encounter Lab — Latest Progress

Date:2026-10-11 (Asia/Kuala_Lumpur)

**P01 — DONE locally; remote acceptance awaits this P01 commit's own exact-head three-job CI.** Baseline13192b741f5f81dae9af3563ad27e81767072d57. Only Play is authorized; P02/P03 remain TODO. No new research experiment, model fit, data acquisition, main merge, tag or release.

## Implemented

- src/chance_encounter.py: standard-library-only, deterministic questionnaire validation and structured entertainment result/keyword/issue contract. Stable machine option keys; relationship description only; arrangement explicitly yes/unknown/missing refuses scoring. Contradictory past30d frequency/recency refuses scoring.
- Fixed public rule: five past/usual factors mapped to0–100 design points, equal mean of known factors rounded half-up; at least3 known. Unknown/missing omitted from numerator and denominator, never imputed as zero. Levels0–34偏低 /35–69中等 /70–100偏高. These are entertainment design choices, no trained/calibrated probability or measured predictive performance.
- pages/12_Chance_Encounter.py and src/chance_encounter_ui.py: seven choice questions, clear no-login/no-dataset operation, correct excluded/insufficient/conflict messages, index/level and3–5 source-grounded cards, modify/resubmit and Play-only reset. Answers/results are local server-session memory only; no identifiers, geolocation, free text, writes/cache, background analytics, exports or model/API calls.
- src/welcome.py and app.py: native nondismissible st.dialog plus an invisible built-in Streamlit v2 component. Only Boolean acknowledgement is sent; one nonidentifying sessionStorage marker survives normal same-tab refresh. No questionnaire data in browser storage, URL, file or third-party service. Browser hydration is awaited; AppTest storage responses are explicitly simulated, not claimed to execute JavaScript.
- src/ui.py appends the13th page, preserving all12 original research entries exactly; Overview gains one prominent Play link while all prior indicators/functions remain. PRODUCT_PLAN.md documents rule/fields/privacy/refresh/scope; README adds a small Play section/navigation row; task/session instructions updated.

## Actual verification

- Pure engine:34 passed in0.05s; dedicated page/welcome/privacy tests12 pass in the focused/full suites.46 new dedicated tests plus3 expanded navigation/document cases produce49 additional collected tests over original384.
- P01 engine/UI + all navigation + documentation focused suite:84 passed in2.77s.
- Full `.venv/bin/python -m pytest -q`:433 passed in35.26s after isolating all new app tests from private research paths.
- All-page test_ui suite:16 passed in1.99s (13 registered pages plus existing3 behavior tests). No previous research test removed or skipped; documentation page-count assertion expands to13 and the new test verifies the exact original12-path tuple against baseline13192b7.
- Workflow-equivalent Streamlit smoke:69 passed in9.58s. Safety regressions27 pass; exact staged-index scanner PASS (202 files,44 approved reports,51 frozen objects unchanged). Pinned Gitleaks full history/index scans and provider-risk self-test PASS; pip check reports no broken requirements. Public audit PASS. Workflow, safety scanner, secret rules and original security tests remain unchanged.
- Actual browser: first visit welcome shows correct text/button; acknowledgement closes it; Overview same-tab refresh and navigation to Play do not repeat it. Play reload also does not repeat. A new independent tab displays welcome. A fictional seven-answer fixture produces the exact rule result; modifying one answer recomputes, reset returns seven empty choices with no stale score. No filled-form screenshots, real user answers or private logs are saved. Only the public welcome dialog was captured locally outside Git; the blank Play tab is left available.
- AppTest cannot execute component JavaScript. Python gate/restore/pending hydration are separately tested, along with acknowledgement-only bridge payload. Browser checks supply the actual reload evidence.
- P01 inventory2730 existing files;2722 protected files unchanged, excluding only8 authorized shared UI/current-doc/navigation-test files. All51 frozen public objects, old research reports/code/data/models and metrics remain unchanged. Current public audit must pass before publication.

## Failures corrected and remaining limits

Initial old navigation tests exposed a Streamlit v2 component lifetime issue: a module-level renderer survived an AppTest runtime reset but its registration did not (1 failure/15 passes). Registering the identical static definition in the current runtime resolves it using the public API; final existing navigation/all tests pass. No test-only production bypass or disabled welcome was added. New UI tests were explicitly isolated from actual local research paths before final verification.

A first manual check used combobox innerText to infer selection, which does not represent this searchable widget's selected display. The actual recomputed result and DOM reset state confirmed edit/clear behavior; no product defect was concealed. No answers or screenshots of filled forms were exported.

Normal same-tab reload is verified after the acknowledgement write. Blocked/cleared browser sessionStorage or immediate reload before the post-click write may repeat the welcome; native server-session navigation still remembers it. Browser tab duplication/session restore may copy/retain the marker. These limits are documented in PRODUCT_PLAN.md. Questionnaire answers intentionally disappear on refresh. JavaScript/component hydration is required; it is not misreported as acknowledgement. Play scores have no empirical accuracy/calibration claim and must remain separate from Copenhagen device-contact results.

## Publication and STOP

Run public audit, exact staged-index safety and pinned Gitleaks; commit only safe P01 source/tests/docs and push research-v2.2. Verify actual remote HEAD plus its new completed/success unit-tests, streamlit-smoke and repository-safety jobs; report actual SHA/run/counts in the final reply without a new untested receipt commit. If CI fails, retain IN_PROGRESS/BLOCKED and fix/reverify. Stop after P01; next suggested task is P02 only on a new explicit instruction.

---

## Previous README/frontend maintenance record (historical)

# Encounter Lab — Latest Progress

Date:2026-10-11 (Asia/Kuala_Lumpur)

**README-FRONTEND — DONE locally; awaiting this documentation commit's own CI.** User requested GitHub README update and opening files/frontend. T34 remains DONE:9f9164fe12a3d93ae39e1f2f5789c8ce7e1856e8 / Actions38065140435 actually completed/success (384 unit/68 smoke/27 safety/12 native), reverified before editing.

README now includes a Chinese frontend introduction, actual Streamlit/Plotly structure, startup/local URL, four-step viewing route, missing-data states, source entry points and the accepted T34 record. Research metrics/limitations unchanged. Changed only README.md, AGENTS.md, TASKS.md and this progress file. No UI/source/data/model/report changes, new research task or main merge.

Verification:39 focused documentation/public-audit tests passed in2.00s; public CLI PASS with51 trusted frozen objects unchanged. Existing internal links,12 navigation paths and scientific metric claims pass. Exact staged-index safety PASS (195 files,44 approved reports,51 frozen objects); pinned Gitleaks history/index scans and provider-risk self-test PASS.191 other pre-existing tracked files remain byte-identical. New SHA/run is attested in the execution reply. No new low-impact mirror tests were added.

Opened README.md, app.py and src/time_machine_ui.py in Codex panels (queued by the app). The actual local frontend at http://127.0.0.1:8514 was loaded, its Overview heading/real aggregate cards visually checked, shown using Browser visibility and marked as a deliverable. A queued app-browser tab initially lacked an attached webview; a fresh tab successfully loaded the app. Keep the localhost-only preview running for the user's requested inspection. Its cache stays outside Git; no private/pair screenshots or data are published.

Safely push current research-v2.2 only and verify its own three CI jobs at the exact remote head. Report the new run in the final reply without another unvalidated receipt commit. Stop after this maintenance task; no deployment, new features, training, data acquisition or branch merge. Previous scientific completion evidence follows as a historical record.

---

# Encounter Lab — Final Progress

Date: 2026-10-10 (Asia/Kuala_Lumpur)

**T34 — DONE after local acceptance; final delivery requires this final commit's own remote CI success.** The user explicitly authorized phase two with 二阶段. Phase one f49db01f1115428fc68f031c1819098ef24ae3dc passed Actions38063195569 (377 unit/61 smoke/27 safety/12 native). This final implementation/status commit must independently obtain completed/success with unit-tests, streamlit-smoke and repository-safety all successful, exact remote HEAD=headSha. Final run metadata is attested in the execution reply; no untested receipt commit is appended. If it fails, repair and retain IN_PROGRESS until reverified.

## Phase-two acceptance gaps closed

1. Case Explorer in src/asof_ui.py now reuses existing make_prediction/reveal_prediction services. The models' read_model_contract policies must agree before any prediction; the verified common min_scan_coverage reaches explicit backtest Reveal through the prediction record and pinned snapshot. Untrusted descriptor values are ignored. No new input fields, UI pages, feature math, models, thresholds or research scores are introduced. The legacy checkbox remains an explicit same-action backtest; independent Time Machine preserves Predict→Freeze→Reveal.
2. Added seven synthetic AppTest regressions:0.25/0.5/0.75 model policies × future coverage0.4/0.6 with no contacts, correct No Contact/Unknown and unchanged probabilities, no future read during blind prediction, and mixed-policy rejection before prediction/future access. Existing T28/T29 temporal/feature/Unknown guards remain intact.
3. Browser capability was available in phase two. Using the Browser skill, visually inspected the actual localhost Streamlit Overview, Dataset Catalog, History Window Study, Time Machine and Multi-Dataset Exploration. Frozen default study rendered actual comparison rows/charts; CSV download yielded3 aggregate rows and the AP field. Real saved-model Predict enabled Freeze while Reveal stayed disabled; Freeze enabled separate Reveal; actual Unknown outcome preserved all shown probability values. Social Evolution rendered the unavailable empty state. No new study/model training or downloads of research data occurred.
4. Updated README, REPRODUCIBILITY, FINAL_RESEARCH_AUDIT, FINAL_RELEASE_CHECKLIST, CI_VERIFICATION, TASKS and AGENTS to the final scope/status. Phase-one known gaps are now explicitly closed. Documentation tests verify final DONE status, actual links/navigation/metric claims and unchanged CI/security policies.

## Actual local verification

- Full `.venv/bin/python -m pytest -q`:384 passed in34.99s (seven additional coverage-policy regressions).
- As-of/Case Explorer/Time Machine/T30 focused suite:68 passed in10.25s.
- Workflow-equivalent Streamlit smoke (all10 explicit UI test files):68 passed in9.08s, including all12 registered pages. Seven other pages have automated navigation coverage, not a claim of exhaustive manual visual inspection.
- Public audit/documentation tests:39 passed in1.85s after final documentation/status updates.
- `python -m src.final_audit`:PASS,51 frozen public objects,117 retrieval aggregate rows and24 benchmark aggregate rows; correct distinct Copenhagen populations. Output remains public_aggregate_verified / not_verifiable_without_local_artifacts.
- Read-only `python -m src.window_verify`:PASS, five stages,36 saved-model full-prediction equivalence checks, metric recomputation and statistical-source freeze; T17 unchanged.
- Read-only `python -m src.asof_audit --verify-only`:PASS, all frozen T30 aggregate metrics/funnels/reliability/errors reproduced from private saved samples. These checks are saved-artifact reproducibility, not independent raw acquisition/reconstruction.
- Phase-two preflight inventory2722 files;2711 protected pre-existing files unchanged, excluding only the11 explicitly modified UI/test/current-document files.51 public reports/documents still match trusted T32 commit5f3be86. Data, models, saved predictions, statistical sources, CI workflow, security scanner/rules and old security tests unchanged.
- Actual staged-index repository safety PASS:195 tracked files,44 approved reports,51 frozen objects unchanged. Pinned Gitleaks provider-risk self-test plus full reachable-history/exact-index scans PASS; pip check reports no broken requirements. Security/document/public-audit focused verification66 passed in3.12s. Final remote CI is still required; no phase-one result substitutes for it.
- Temporary localhost service bound only127.0.0.1, browser tab closed and service stopped after checks. Only a screenshot of already-public source aggregate counts is retained locally outside Git. No pair IDs, individual probabilities, raw logs or screenshots are published to GitHub.

## Verification notes

Initial sandbox server launch could not bind a socket; the authorized localhost-only launch succeeded with the required execution permission. Arrow emitted sandbox CPU-cache sysctl warnings during successful read-only scientific checks; no research verification failed. The first phase-two full suite and focused regressions passed. No test assertion, CI safety policy or frozen evidence was weakened. The documentation status expectation changed from phase-one IN_PROGRESS to the user's now-authorized final DONE contract.

## Deliverables and scientific boundaries

Final public audit: src/final_audit.py and tests/test_final_audit.py. Evidence/reproduction/portfolio/demo/current-index documentation: FINAL_RESEARCH_AUDIT.md, REPRODUCIBILITY.md, PORTFOLIO_GUIDE.md, DEMO_GUIDE.md, FINAL_RELEASE_CHECKLIST.md, README.md, CI_VERIFICATION.md, with DEVELOPMENT_HISTORY.md preserving the older README. tests/test_documentation.py checks publication/documentation contracts. Phase-two repair is limited to src/asof_ui.py and tests/test_asof_ui.py; time_machine/asof_inference/statistical modules remain unchanged.

Real T22 7d XGBoost AP0.691366 concerns25569 fixed-cohort samples across only4 principal dates. T30 AP0.758930 has a changed reliably observed/predictable population and higher prevalence; it is not a same-population improvement and Brier worsens. Unknown/selection/proxy coverage and exposed dates prevent significance, long-term or external-population claims. Contact-only Workplace supports observed-positive retrieval, not binary AP/Precision; High School lacks7d support, MIT tick mapping remains unverified and Social Evolution unavailable. T31 complete raw ranking reconstruction and original T32 performance measurements were not rerun here; their public aggregate formulas were verified. Snapshots remain stable-archive checks with ingestion_time unavailable and disclosed TOCTOU/live-transaction limits. Anonymous IDs are not formal anonymity. Public CI verifies code/fixtures/aggregates/frozen bytes, not raw-data reproduction or live forecasting. Desktop browser acceptance is not a mobile/accessibility certification.

## Final publication and STOP

Safely commit/push this final candidate to research-v2.2; verify the actual new final-head three-job CI and remote SHA, then STOP. Do not append an unvalidated metadata commit. No next task,2.3, deployment, tag, refit, dataset acquisition or main merge is authorized. Future work requires a new user instruction.
