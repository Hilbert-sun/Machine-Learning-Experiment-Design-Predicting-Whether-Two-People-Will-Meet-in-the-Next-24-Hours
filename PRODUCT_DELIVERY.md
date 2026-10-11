# Encounter Lab · P03 Product Delivery

P03 implements the final authorized Product Extension, based on P02 bb05d4ae709e64643a3d436aeeb7e73f880b6202 / successful Actions38111188664. P01 scoring/welcome and scientific results remain separate and unchanged. Final publication acceptance requires this P03 commit's own exact remote HEAD and three successful CI jobs; the execution reply records the observed SHA and Actions URL without an untested receipt commit.

## What visitors can do

Home asks “世界这么大，明天我们会不会刚好遇见？” and provides three clear cards. **开始偶遇预测** is the primary action. No research inventory/model loading happens on Home or the unopened Research directory.

One-minute path: Home → Play → seven coarse answers → calculate → integer index, tendency and source-grounded Keyword cards → **查看我的偶遇分析**. In Explore, inspect the same factors and A/B clue associations; **修改我的信息** returns to answers and invalidates the old result until resubmission. **重新开始** clears questionnaire and optional graph state. Answers stay in the server's current session, never a shared cache, file, URL, export or third-party model. Actual completion time varies; no timed usability-study claim is made.

## Navigation hierarchy

1. Global native links on every routed page: **首页 Home / 玩一玩 Play / 数据分析 Explore / 科研中心 Research**.
2. Research Hub groups: **数据与探索**, **机器学习与评估**, **高级研究**, plus report/reproduction links.
3. Registered original tools: Data Manager, Data Explorer, Encounter Network, Data Sources, Dataset Catalog; Model Training, Prediction Lab, Model Evaluation, History Window Study; Time Machine and Multi-Dataset Exploration.

All12 original file routes remain registered, followed by Play/Explore/Research Hub (15 total). The original Overview route now serves Home; its six scientific indicators, three available-data charts and quick links are preserved in [the moved renderer](src/research_overview_ui.py). Open **Research → 打开科研概览** to inspect them; **收起科研概览** hides them. This is a presentation relocation, not a replacement dataset/statistics implementation. Global Home remains available from every tool. No custom navigation HTML/JavaScript or CSS selector overrides are added.

## Explore: two kinds of evidence

Native tabs separate **我的偶遇分析** and **真实数据中的相遇规律**. With a valid submitted questionnaire, personal analysis opens first; otherwise public stories open and the personal tab provides guidance. Small public aggregates render even when that tab is hidden; raw data/models never load here.

Play/Explore share consistent cards with an icon, text direction, actual selected source, name and explanation. Known factor bars preserve fixed P01 points; Unknown is omitted, not zero. Personal analysis is not SHAP, learned importance or a calibrated probability.

The dark A/B graph retains canonical seed42 positions, real Keyword nodes, bounded edges, hover/click descriptions, A/B focus and restore. Padded axes/outward labels and a wrapped mutual-summary label reduce clipping. **查看节点说明（支持触屏）** exposes complete descriptions without hover; restoring also clears selected details. Optional mutual ranges produce one self-report summary, never invented individual friends or points. This static graph is a questionnaire-association diagram, not a true social network or draggable physics simulation. Dense labels may still overlap on small screens; the selector provides the full text.

Public charts preserve exact existing P02 loaders/calculations: T22 JSON/CSV reconciled XGBoost1/3/7d AP on the same test population, and T31 confirmed relative-day record activity/public neighbor bins. Chart titles wrap and use smaller display type. Source selectors affect group charts, not the separately labeled Copenhagen window chart. Missing/suppressed values stay absent; MIT unknown ticks prohibit daily trends, Social Evolution has no invented curves, and High School cannot support7d research. T17/T30 populations are never mixed into the T22 comparison. See [source and method guide](EXPLORE_GUIDE.md).

Research reports/reproduction links point to the authorized GitHub development branch. Original research tools retain local artifact requirements, time-bound inference, explicit freezing/reveal, Unknown outcomes and validation-only selection. Opening a directory/page does not initiate training/downloads. Real data/model weights are intentionally absent from public Git.

## Install and preview

Use Python3.11:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
streamlit run app.py
```

Streamlit1.65.0 was used for the local UI checks; requirements and CI remain unchanged. Play and public Explore work without private research artifacts. Independent research reproduction needs lawful local source data/models and the contracts in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Verification

Focused product/navigation/old-route checks, full pytest, workflow-equivalent smoke, public frozen audit, exact-index repository safety, pinned Gitleaks history/index/provider self-test and pip check are mandatory. Observed local checks:127 focused product/navigation/P01/P02/old-route tests passed; documentation plus product tests50 passed; full suite500 passed in37.33s; workflow-equivalent Streamlit Smoke71 passed in9.14s; safety rejection tests27 passed in1.20s; pip check found no broken requirements. Public final_audit PASS confirmed51 frozen files. The original scientific Overview rendering body remains identical after indentation/relocation, with real-cache metrics and stale-cache invalidation assertions retained. Of2745 preflight objects, only authorized UI/test/current-document paths changed; no pre-existing data/model/report object changed. Exact staged-index/Gitleaks acceptance is completed before publication; remote Linux counts remain gated on the actual new SHA. Old tests retain business assertions; changed navigation access steps now open statistics through Research Hub.

AppTest resets Streamlit's legacy pages-directory detection between runs. The new global-navigation test fixture explicitly selects the modern-router execution path, matching persistent real browser sessions, so each old route is tested with the actual app entrypoint and global links. Production code has no testing bypass. Existing standalone page tests still run unchanged in scope. AppTest does not execute welcome JavaScript; real browser acknowledgement/refresh checks complement the existing mocked storage-response tests.

## Actual browser checks

Only explicitly fictional coarse questionnaire choices were entered; no filled-form or private research screenshots are published. Native welcome appeared on the fresh test tab; acknowledgement suppressed repeats in subsequent navigation and a normal full same-tab refresh (dialog count0). Play produced66, Explore showed the same value, mutual3–5 generated a single summary with explicit self-report explanation, A focus and restore worked, and the touch selector showed complete provenance. Edit hid the old result; changing distance and resubmitting produced71. Research navigation retained the submitted result; reset cleared answers and personal analysis, leaving public charts usable.

| Simulated viewport | Observed results |
| --- | --- |
| 390×844 | Home cards stack, four links wrap in two rows; seven-question form, result/cards, personal factors and padded graph work. Node description selector is usable; public AP chart Chinese title/axes fit. Research directory wraps with accessible links. Measured document scroll width390, visible chart width358; no page-wide horizontal overflow. |
| 768×1024 | Home has three readable, aligned cards and four links in one row. Personal cards/factors and public tabs render; chart width736 and scroll width768. Research classification links remain reachable. |
| 1440×900 | Home cards/primary action align; global navigation reaches original Training/Evaluation/Time Machine and returns Home. No train/evaluate/predict/download action was invoked. Source switching preserves independent Copenhagen chart; MIT shows unverified tick-unit restriction and only that public AP chart; Social Evolution shows unavailable with no fabricated group curve. Scroll width1440. |

These are actual desktop browser viewport simulations plus rendered screenshots/DOM checks, not physical device tests. Default Workplace2013 displays all three real public graphs. Without questionnaire, public tab is selected; the personal tab explicitly guides the visitor and contains no personal index. Existing automated tests also cover B focus, all15 registered routes, planned/unknown arrangements, source/suppression and isolated sessions. All12 original routes are exercised automatically; the three specified research tools were also opened in the real browser.

## Limitations and delivery boundary

The index is a transparent entertainment rule, unvalidated for predicting real personal encounters. The unchanged welcome only persists a Boolean tab marker; blocked/cleared storage or immediate pre-write refresh may repeat it, and tab duplication/session restore may retain it. Answers themselves do not persist across server sessions.

Archive event times do not establish live ingestion availability. Only four main research test dates, scan-proxy coverage and source-specific Unknown/short spans limit scientific generalization. P03 does not re-evaluate or improve model quality. Browser viewport checks are simulated desktop-browser dimensions, not physical mobile-device, screen-reader or exhaustive browser compatibility certification. Original scientific/report/safety bytes remain protected. P03 ends P01–P03; await final user acceptance, with no automatic next task.
