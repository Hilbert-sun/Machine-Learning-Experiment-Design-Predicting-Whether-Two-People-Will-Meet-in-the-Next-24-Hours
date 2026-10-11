# Explore — P02 usage and data boundaries

Planning baseline:ab4dc3f20e5bcd587a5d4caf5611f5bc3fb0afbb. P02 is incremental: P01 scoring rules/welcome and the12 research routes remain intact. P03 redesign, new models, datasets, training, downloads, report regeneration, tags and main merge are outside scope.

## Three entry points

Overview presents Play, Explore and Research. Play opens the existing questionnaire; Explore opens [Encounter Insights](pages/13_Encounter_Insights.py); 深入研究 opens the original Overview statistics/data links on demand. First load does not scan raw/processed/model inventories. 收起科研概览 hides the research area. The existing Data Manager/Model Training/Prediction Lab links and research statistics remain available there and through original navigation.

There are14 registered pages:12 original research pages, P01 Play and P02 Explore. This is a small entry adjustment, not a new routing system or P03 redesign. Narrow windows use Streamlit's existing more menu and responsive columns.

## Personal explanation flow

Play → submit valid questionnaire → 查看我的偶遇分析 → Explore. Only the current session's submitted Questionnaire and EntertainmentResult are used. [Analysis logic](src/encounter_insights.py) calls the unchanged P01 evaluator to verify the stored result matches the submitted answers; it does not create a second formula. Missing, stale, out-of-scope, unconfirmed, inconsistent, insufficient or invalid inputs display guidance without a personal index.

Known Keyword structures determine the result text, source-grounded cards and factor bars. Unknown/unanswered factors are named separately, not zero-filled or included in the average. Values are fixed entertainment-rule points, not learned importance, SHAP or true encounter probabilities. Relationship categories never change the index.

修改我的信息 returns to the Play form; editing clears the old submitted result and Explore-only state. New submission recalculates through P01. P01 reset removes both questionnaire/result and optional Explore mutual/focus state. Page switching does not alter a valid score; a fresh session has no personal demonstration score. No personal analysis or optional relationship values enter shared cache, URL, file, logs, exports or research reports.

## The A/B clue diagram

[Graph implementation](src/encounter_graph.py) uses existing NetworkX + Plotly only. A canonical node/edge order, fixed seed42 and80 spring-layout iterations provide repeatable force-directed positions. Dark background, soft edges, hover explanations, point-selection details, A/B focus controls and 恢复默认视图 are provided. The layout is static and reproducible, not a continuously simulated or draggable-node force engine.

A/B are symbolic questionnaire endpoints, not research IDs. Nodes represent only known Keyword fields; a known weak/conflicting-routine clue is labeled as such, not asserted to be a shared schedule. Unknown factors produce no node. Edges associate self-reported questionnaire fields with endpoints; they do not assert friendship, identical routines or causal influence. Color distinguishes factor type with text labels; clue-node size follows the P01 rule points, while A/B and mutual-summary sizes are fixed display markers, with no score assigned to the summary. Focus dims nodes outside the selected endpoint's neighborhood.

The optional common-acquaintance selector has stable keys none/one/two/three_five/more/unknown. Known nonzero ranges produce exactly one aggregate node such as 自述大约3–5人, never3 or5 individual friend nodes. None/unknown/unprovided produces no such node. This question does not enter P01 scoring.

Built diagrams have at most8 nodes/12 edges; renderer hard caps15 nodes/30 edges, rejects non-questionnaire provenance and handles empty/single/edgeless cases. No anonymous research ID or research edge is inserted. The separate research-network entry links to the existing Encounter Network page, which requires legitimate verified local caches and retains its own historical time/filter/render limits. Public aggregate reports contain no true edge lists, so this page does not invent a sample network or default-load large Parquet data. Research contacts are not social friendships or the user's real contacts.

## Public stories and actual provenance

| Question | Data and method | Meaning and limits |
| --- | --- | --- |
| 过去看得越久，系统预测得越好吗？ | T22_ROBUSTNESS.json + T22_METRICS.csv; load XGBoost1/3/7d records and reconcile metrics, row counts, prevalence, date counts and shared-candidate protocol | Same T22 test population only. Average Precision is a ranking metric, not a user's chance of encountering someone. Technical fold discloses actual sample/date support, prior exposure, no significance or independent long-term validation. T17/T30 cohorts are not mixed in. |
| 人们每天的接触活动一样多吗？ | T31_SOURCE_SUMMARY.json network.activity, only confirmed seconds/relative Study Day sources | Actual record/active-pair counts; dynamic narrative derives the largest publicly visible day. Null/suppressed remains blank, connectgaps=false; a genuine public0 means no recorded events, not no encounters or complete observation. No calendar-date inference. |
| 有些人会接触更多不同的人吗？ | T31_NETWORK_METRICS.csv reconciled to source JSON; source degree_histogram only when aggregate groups are public | Counts describe recorded anonymous nodes/pairs; largest published bin is read from data. Suppressed/missing small groups are not reconstructed or filled with0. Node count/density does not establish which population is more social. |

Source paths:

- [T22 frozen report](reports/window_study/T22_ROBUSTNESS.json), [T22 metrics](reports/window_study/T22_METRICS.csv)
- [T31 source summary](reports/multisource/T31_SOURCE_SUMMARY.json), [network metrics](reports/multisource/T31_NETWORK_METRICS.csv), [feasibility](reports/multisource/T31_FEASIBILITY.json), [positive retrieval](reports/multisource/T31_RETRIEVAL_METRICS.csv)

Workplace2013/2015 have recorded daily activity; High School has short verified duration and cannot support7d research. MIT Reality Mining retains static descriptive counts with unknown tick units and no daily curve. Social Evolution remains unavailable, with no placeholder curve or network. Contact records are not meeting counts; source namespaces remain independent. T31 observed-positive retrieval, T30 Unknown/selection bias, T32 snapshot/performance limits remain unchanged.

Public source summaries reuse the existing content-versioned aggregate-only cache (deep-copy results); T22 and network CSV are small read-only files with cross-checks. No questionnaire result is cached globally. Default page execution does not read raw data, Parquet, model weights, train, download or regenerate reports. There is no verified hourly aggregate input here; the page explicitly declines a real activity heatmap. No word cloud/text-mining claim is made.

## Welcome, privacy and verification

The existing [P01 welcome](src/welcome.py) is unchanged: one native dialog, Boolean tab-scoped acknowledgement, documented storage/refresh limits. Explore adds no second disclaimer. Local provenance/method labels remain necessary to distinguish entertainment points, public research aggregates and optional historical networks.

Tests cover P01 session validation/staleness/reset and isolation, exact factor reuse/unknowns, deterministic bounded graph/summary-only acquaintances, data-driven T22/T31 figures and source/suppression/cohort guards, three homepage entries/lazy scans, all original routes and P01 scoring/welcome integrity. All tests use public aggregates and synthetic temporary questionnaire/record fixtures. Real browser desktop/narrow checks are recorded only if actually performed; no filled-questionnaire screenshots, private inputs or individual research graph exports are published.

```sh
python -m pytest -q tests/test_encounter_insights.py tests/test_encounter_graph.py tests/test_encounter_insights_ui.py
python -m pytest -q
python -m src.final_audit
python tools/check_repository_safety.py
python -m tools.run_secret_scan
```

Final acceptance requires the actual P02 final-head unit-tests, streamlit-smoke and repository-safety jobs all completed/success, matching remote SHA. Historical P01 green CI is not substituted; final SHA/run/counts are attested in the execution reply without an untested receipt commit. Stop after P02; P03 remains TODO.
