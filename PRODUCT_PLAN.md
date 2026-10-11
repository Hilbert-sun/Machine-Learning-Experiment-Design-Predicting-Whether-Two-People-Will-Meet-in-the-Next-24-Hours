# Encounter Lab product extensions

P01 adds Play alongside the existing Research application. Explore and broader navigation work remain future tasks. Research Edition2.2 T01–T34, its12 original pages,51 frozen public materials, saved local models/labels/features and CI/security rules remain intact. Planning baseline:13192b741f5f81dae9af3563ad27e81767072d57.

| Task | Scope | Status |
| --- | --- | --- |
| P01 · Play | Questionnaire, pure-rule index, keyword explanations, edit/reset, entry welcome and one added page | Implemented and locally verified; remote acceptance gated on its own exact-head three-job CI |
| P02 · Explore | Future expanded data/network exploration; specification required | TODO; not implemented or authorized by P01 |
| P03 · Product navigation | Future overall homepage/Play/Explore/Research layout; specification required | TODO; not implemented or authorized by P01 |

## Product and scientific boundary

Play discusses the self-reported tendency of an unarranged chance encounter within24h. Planned meetings, relationships, real GPS/trajectories, weather/traffic and unknown future events are outside scope. Copenhagen research predicts recorded anonymous-device contacts; those models were not trained with questionnaire fields and do not distinguish planned from chance encounters. P01 never loads them.

The output is **趣味偶遇指数**, not a trained/calibrated probability. No accuracy, AUC, sample-supported weights or empirical validity is claimed. Equal weights and cutoffs are transparent product design choices, not measured scientific results. Questionnaires and researcher identities are not joined.

## Stable input and fixed formula

[Pure engine](src/chance_encounter.py) exports Questionnaire, evaluate_questionnaire and structured EntertainmentResult/Keyword/Issue values. Machine keys are independent of Chinese labels. Relationship is descriptive only; arrangement is a gate. This stable callable/output contract is the extension seam for a future independently validated questionnaire engine; no such model is provided by P01.

| Field | Machine values and rule points |
| --- | --- |
| relationship | friend/classmate/coworker/acquaintance/stranger/other; no points |
| distance | same_area100, walkable75, city_far30, different_city0, unknown omitted |
| frequency (unarranged past30d) | zero0, one_two35, three_five70, six_plus100, unknown omitted |
| recency | day100, week75, month45, older15, never0, unknown omitted |
| area | often100, sometimes55, rare0, unknown omitted |
| timing | often100, sometimes55, different0, unknown omitted |
| arrangement | yes:out_of_scope; unknown/missing:needs_confirmation; only no permits scoring |

For n known factors, require n≥3. Index = floor(sum(points)/n +0.5), bounded0–100. Levels:0–34偏低,35–69中等,70–100偏高. Unknown/unanswered fields are excluded from both numerator and denominator, never zero-filled or treated as negative evidence. A real answered zero remains known. Different sets of available factors can change the mean; these indices do not form a calibrated population comparison.

A positive past30d frequency conflicts with older/never recency; zero past30d conflicts with day/week/month recency. Report the conflict rather than invent data. Other coarse answers may legitimately differ and are not overridden. At least3 of the five past/usual-routine factors are needed; relationship and arrangement do not count toward support.

Each of3–5 keyword cards cites its exact user-selected source, names the factor, explains the rule and shows strong/general/weak evidence status. Unknown factors produce no fabricated card. All descriptions are explicitly based on user input, not sensors, real schedules or shared-friend records.

## User path and state

[Overview](pages/0_Overview.py) → 开始偶遇预测 · Play → [Chance Encounter](pages/12_Chance_Encounter.py). The13th navigation page follows all12 unchanged research entries. No new overall navigation redesign is included.

After selecting answers, calculate the index; excluded/invalid/insufficient cases show an explanation with no score. A valid result displays n keyword cards. 修改信息 restores submitted answers; a new submit recalculates. 重新开始 clears only Play questionnaire/result/widget state, preserving research selection and welcome acknowledgement. Page switching can retain Play answers within the same server session; refresh starts a new server session and clears answers.

## Welcome and refresh behavior

[Welcome module](src/welcome.py) uses native st.dialog/st.session_state, plus a tiny built-in Streamlit v2 JavaScript component. It communicates ONLY a Boolean confirmation flag; sessionStorage stores one nonidentifying marker (`encounter_lab_welcome_v1=1`), no questionnaire answers, names, IDs, URL token, cookie or third-party call. Static component code never interpolates user input and loads no external resources.

The dialog waits for the browser's storage response. Unacknowledged visits see one nondismissible welcome with the explicit acknowledgement button; acknowledgement closes it and is written on the next component render. Navigation within the session does not repeat it; after the marker is persisted, normal same-tab refresh restores acknowledgement. A new independent tab/session can show it again. Browser tab duplication/session restore may copy or retain sessionStorage; this is browser behavior, not a fresh-visit identity guarantee.

If browser sessionStorage is blocked/unavailable/cleared, the native server-session acknowledgement still prevents repeats while navigating, but refresh may show the welcome again. An immediate refresh before the post-click storage write may also repeat it. Streamlit requires JavaScript; failure of component hydration is not claimed to be a confirmed welcome. AppTest does not run browser JavaScript: its dialog/restore tests explicitly simulate storage responses, while actual refresh behavior must be checked in a real browser. No test-only production bypass is used.

## Privacy and verification

No login/name/phone/social account/address/location permission/contact upload/free-text question. Answers are processed only in current local server memory, never in files, cache, browser storage, logs, export buttons, databases or model APIs. Native Streamlit transport to the app's server is necessary for widgets; deployers remain responsible for their server environment. There is no third-party inference, background analytics or questionnaire export.

P01 adds pure-engine and page/dialog regression tests. Existing12-page research navigation coverage, scientific leakage/model tests and safety/CI stay enabled; navigation/document tests expand to13 entries without deleting prior assertions. The public checkout needs no genuine data/models. Run:

```sh
python -m pytest -q tests/test_chance_encounter.py tests/test_chance_encounter_ui.py tests/test_ui.py
python -m pytest -q
python -m src.final_audit
python tools/check_repository_safety.py
python -m tools.run_secret_scan
```

Local P01 verification:34 pure-engine tests,12 page/welcome/privacy tests,16 navigation tests and22 documentation tests pass (84 focused); full suite433 passes. This expands the original384 tests by46 dedicated P01 cases plus3 new navigation/documentation cases. The original12 research paths are checked byte-for-byte as a tuple against the planning baseline and still exercised individually. Native browser checks confirm welcome acknowledgement, same-tab reload on Overview/Play without repetition, new independent tab welcome, questionnaire/result/edit/reset; only explicitly fictional test choices were used, with no filled-form export or screenshot. AppTest uses isolated temporary config paths, never private research artifacts.

Final SHA, observed test totals and actual completed/success CI are attested in the execution reply; previous green T34/README runs are not P01 acceptance. Never publish actual questionnaire logs, filled-form screenshots or per-person artifacts. P02/P03, word clouds, relationship graphs, new datasets/model training, main merge, tags/releases are outside this task.
