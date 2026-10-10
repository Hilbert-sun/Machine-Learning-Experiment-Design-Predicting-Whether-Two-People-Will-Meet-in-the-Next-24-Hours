# Encounter Lab — Progress

Date: 2026-10-10 (Asia/Kuala_Lumpur)

**T34 — IN_PROGRESS / phase one awaiting this implementation commit's remote CI.** The user resumed with 继续 after saving partial work. Only phase one is authorized: implement/audit/test, safe commit and push research-v2.2, verify all three jobs at the new exact SHA, then STOP. Do not perform phase two DONE confirmation. The accepted starting commit is ae623111871407a74185777f4d3a74c642b0dcde (T33 run38054089678); its CI does not establish T34 acceptance.

## Delivered implementation and documentation

- src/final_audit.py is a read-only public CLI: validate historical frozen Git bytes first, then reconcile T17/T21/T22/T30 CSV/JSON metrics and cohort prevalence, the T30 reliable/predictable/Unknown partitions, T31 source/time/retrieval/network formulas, T32 before/after arithmetic/cache modes/snapshot limitations, and historical T33 evidence references. Output safe aggregate JSON only; fail nonzero with a located inconsistency. No source/model reads, fitting, network or report rewriting.
- Public output explicitly says public_aggregate_verified and not_verifiable_without_local_artifacts. It does not claim independent raw reconstruction or query current Actions.
- Added tests/test_final_audit.py and tests/test_documentation.py: public-only execution, frozen tampering/deletion, count/formula/Unknown/source failures, valid local links, all12 real navigation paths, metric claims, inference/reveal semantics and unchanged CI/security policies.
- FINAL_RESEARCH_AUDIT.md indexes T17–T33 with evidence, populations, contracts, real results and limits. REPRODUCIBILITY.md defines public/saved-local/interactive levels and verified read-only commands. PORTFOLIO_GUIDE.md diagrams actual boundaries; DEMO_GUIDE.md offers a bounded five-minute script. FINAL_RELEASE_CHECKLIST.md keeps both phases distinct.
- README.md now presents Research Edition2.2; prior README preserved as historical DEVELOPMENT_HISTORY.md. CI_VERIFICATION.md records the actual accepted final T33 run; TASKS.md and AGENTS.md preserve phase-one scope.
- No UI feature, new dependency, dataset acquisition, model refit, threshold selection, main merge or tag.

## Tests and checks actually performed

- Full `.venv/bin/python -m pytest -q`:377 passed in33.34s.
- New audit/documentation focused suite:39 passed in1.85s.
- Workflow-equivalent Streamlit smoke command (the10 explicit existing UI test files):61 passed in7.60s, covering all12 registered pages and interactive/empty/coverage cases.
- Repository safety rejection tests:27 passed in1.45s. Actual staged-index scanner PASS:195 tracked files,44 approved reports and51 frozen objects unchanged. Pinned Gitleaks provider rejection self-test plus full reachable-history and exact index scans PASS. Current-head remote CI is still pending and will be attested in the execution reply.
- pip check: no broken requirements. Public CLI PASS:51 frozen public objects,117 retrieval aggregate rows and24 benchmark aggregate rows checked; distinct test/population counts260170/25569/38005/27820/10185/27802.
- Read-only `python -m src.window_verify`: exit0, five stages,36 saved-model full-prediction equivalence checks, metric recomputation and statistical freeze passed; T17 unchanged.
- Read-only `python -m src.asof_audit --verify-only`: exit0; all T30 aggregate metrics/funnels/reliability/errors reproduced from frozen private samples. These are saved-artifact checks, not a new raw acquisition/reconstruction.
- Real-local-artifact AppTest semantic review: Overview (3 charts), Catalog, History Window Study (8 frozen charts), Time Machine (actual saved1/3/7d model Predict→Freeze→Reveal, frozen probabilities unchanged), Multi-Dataset Exploration (real graphs and unavailable-source empty state). No individual receipts/screenshots are published.
- Preservation inventory:2708 protected pre-existing files unchanged out of2713 entries (only the five current doc/progress files allowed to change).44 public reports and7 research documents match trusted T32 commit5f3be86; original research/statistical source, local data/model weights and experiment files preserved. CI workflow, Gitleaks policy, scanner and existing security tests unchanged.
- Local temporary receipts use encounter-t34-* filenames outside Git. Arrow sandbox CPU-cache sysctl warnings occurred during successful real-artifact checks; they were not test failures.

## Failures found and repaired

Initial saved test draft had invalid parametrization syntax and failed collection; corrected. After adding stricter duplicate-source comparisons, one negative test expected a later error rather than the earlier CSV inconsistency; corrected expected location. A public-only missing-input fixture initially omitted trusted Git metadata and failed at historical object lookup; fixture now supplies read-only object access and verifies the missing frozen filename is reported. Final suites pass; no assertions or CI rules were weakened. README's nonexistent LICENSE link was removed; project code licensing is explicitly unspecified.

## Outstanding acceptance and scientific limits

- Legacy History Window Study Case Explorer reveal in src/asof_ui.py still omits model min_scan_coverage and defaults to0.5. Nondefault-policy absence outcomes there are not validated. Independent Time Machine uses the verified frozen common policy correctly. This audit records the issue without altering frozen modules; final completion needs explicit disposition or a separately authorized fix.
- No callable browser-control runtime is available in this session. Real-artifact AppTest semantic checks passed, but manual browser visual/layout acceptance is NOT verified. Do not report it as passed.
- Four principal test dates, proxy scan evidence, selected reliable T30 subset and previously exposed dates do not establish long-term/independent population generalization or significance.
- Workplace retrieval is not binary AP/Precision; High School lacks7d support, MIT tick mapping is unverified and Social Evolution unavailable. T31 complete raw ranking reconstruction and the original T32 benchmark were not rerun by T34; aggregate checks only for those experiments.
- Snapshot ingestion_time remains unavailable, with stable-archive and disclosed TOCTOU/live-transaction limits. Anonymous IDs are not a privacy guarantee. Public CI checks synthetic code/aggregate/frozen evidence, not genuine raw research reproduction.

## Publication gate and next action

Review and publish only safe T34 source/tests/docs. Keep T34 IN_PROGRESS while awaiting its own new-head Actions. Verify status completed/conclusion success and all unit-tests/streamlit-smoke/repository-safety jobs, with exact remote HEAD=headSha; report actual run ID, URL, SHA and counts in the final reply. Never use historical T33 CI as substitute or append an unvalidated receipt commit just to record a future run ID. STOP after phase one. Phase two is a separate instruction and must address outstanding acceptance limits before final DONE.
