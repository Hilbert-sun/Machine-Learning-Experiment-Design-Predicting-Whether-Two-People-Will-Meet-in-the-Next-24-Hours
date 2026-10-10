# T33 — Public CI Verification

Status: implementation remotely verified; final delivery requires the NEW final-head run to pass after this documentation/configuration commit. Baseline research-v2.2 at5f3be86bebe089af5dea9b671ce25fe8e0c279f0. T34 not started.

## Test/data preflight

Original inventory:307 tests collected, all307 passed in29.07s from a fresh tracked-only export with no raw datasets, ignored Parquet, weights or local study directories. This is macOS verification using the existing interpreter, NOT evidence of Linux dependency installation or remote Actions success. requirements-lock.txt exists and explicitly records macOS ARM64; CI installs requirements.txt and verifies actual Linux imports/pip consistency. No Linux lock is fabricated.

All existing tests use synthetic tmp_path fixtures, small mock downloads, or reviewed public aggregate reports. No original test is removed, skipped or filtered from the unit job. New default pytest HTTP guards reject requests/urllib live HTTP; package and scanner installation occurs outside pytest. Independent subprocess resource stress uses only generated synthetic rows. No operating-system network sandbox is claimed. Runner freshness tests verify real raw/model/run artifacts and repository .venv are absent when ENCOUNTER_CI_PUBLIC=1; local research checkout may contain ignored artifacts, so local tests also audit tracked bytes rather than require deleting genuine local data.

| Original module | Collected tests | Public fixture scope |
| --- | --- | --- |
|tests/test_asof_audit.py|8|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_asof_inference.py|25|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_asof_ui.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_baseline_audit.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_calibration.py|11|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_data_manager.py|8|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_dataset_catalog.py|7|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_delivery.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_downloader.py|12|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_environment.py|12|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_evaluation_ui.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_experiments.py|9|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_exploration.py|11|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_features.py|8|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_labels.py|14|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_leakage.py|8|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_main_models.py|5|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_multisource_exploration.py|6|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_multisource_ui.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_network.py|5|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_performance_benchmark.py|3|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_performance_parity.py|7|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_positive_retrieval.py|15|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_prediction.py|6|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_preprocessing.py|10|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_real_experiment.py|3|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_safe_cache.py|7|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_schema.py|24|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_snapshot_consistency.py|5|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_streaming_performance.py|3|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_time_machine.py|5|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_time_machine_coverage.py|16|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_time_machine_ui.py|5|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_training.py|8|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_training_ui.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_ui.py|15|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_window_cohort.py|3|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_window_features.py|3|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_window_robustness.py|4|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_window_study.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|
|tests/test_window_ui.py|2|Synthetic tmp_path / mocks / safe aggregates; no private research run required|

Inventory numbers describe actual preflight collection, not a hardcoded CI assertion. New T33 tests expand this list; final counts come from actual pytest logs. Tests named real_experiment/delivery train ONLY explicitly synthetic fixtures. Native XGBoost and LightGBM tests remain in the full suite. All12 registered pages are exercised by test_ui, with additional Time Machine ordering/coverage/invalidation, Unknown, source switching, snapshot and leakage regression tests.

## Workflow and scopes

.github/workflows/ci.yml uses ubuntu-latest/Python3.11, official checkout/setup-python pinned to verified complete v6 commit SHAs, contents:read, persist-credentials:false, full Git history, bounded timeouts, push/PR targeting research-v2.2 plus optional workflow_dispatch. No pull_request_target, shell interpolation of PR text, PAT/license/dataset secrets, write permission, continue-on-error or pytest exclusions. libgomp1 provides Linux OpenMP runtime; ML libraries are not removed. Each ML job installs requirements.txt with pip, runs pip check; unit additionally verifies native imports and collects/runs the entire suite. The FINAL workflow restores no dependency/home/research caches; every runner installs its dependencies anew. The first implementation run used only public pip-download caching; it did not restore private data. Normal installer-created caches/toolchains are not historical research data or personal configuration.

Three mandatory task-acceptance jobs:

- unit-tests: fresh dependencies, pip check, all native imports, full collection/full pytest.
- streamlit-smoke: explicit UI/as-of/TimeMachine/coverage/multisource/window tests plus DataManager/Catalog/training/evaluation UI cases.
- repository-safety: standard-library scanner and pytest only, actual Git index/frozen evidence scan, pinned Gitleaks full available history plus exact staged index. No ML installation in this job.

Jobs must all conclude success for the FINAL head SHA. This task does not change GitHub branch protection/settings or merge main. Actual push triggers initial validation; workflow_dispatch availability on a nondefault branch is not assumed.

## Repository safety and secret scope

The scanner reads actual Git index blobs, including force-added ignored files; .gitignore alone is insufficient. Reject private data/model/cache paths (empty directory markers only), Parquet/joblib/pickle/database/weights/HTML/env/key files, disguised binary magic, large files, private pair/sample JSON/CSV structures, malformed report structures, common credential patterns and personal home paths. Reports are limited to44 exact reviewed names read from the TRUSTED historical baseline .gitignore, not the candidate's potentially edited ignore rules. Future legitimate report additions require explicit policy review.

Frozen protection compares44 prior public reports plus7 research documents against commit5f3be86bebe089af5dea9b671ce25fe8e0c279f0 using SHA256 of Git blobs. The expected bytes are taken from that immutable historical commit, never regenerated from the current candidate. Changed/deleted evidence fails. This public CI cannot inspect ignored genuine data/weights or rerun the actual research. Full local commands such as window_verify, asof_audit --verify-only and performance_audit need lawful matching sources, saved36 models and private artifacts; they are not run or imitated by CI.

Gitleaks8.30.1 comes from the official release, exact archive SHA256 checked before extracting only its executable. The scanner runs with redaction and failure exit status; all reachable commits in checkout refs plus exact index export are scanned. A runtime-generated inert GitHub-token shape must be rejected inside a normally reviewed report path before real scanning. No online credential verification and no inaccessible/deleted server-side history audit is claimed.

Initial history scan correctly failed with39 generic-api-key findings. Every finding was verified as a64-hex SHA256 in sample_key_hash (28 occurrences) or key_hash (11), generated by src/window_cohort.row_hash; these are integrity digests, not authentication secrets. Five frozen JSON paths and13 exact known digest values are covered by a rule-specific AND(path, exact field/value line) exception. All default rules and all provider-token rules stay enabled. No whole commit/path is suppressed, no default rule disabled, no baseline ignore file, and unknown/new digests are not exempt. Frozen evidence checks independently prevent alteration of those report contents. No frozen report was edited for scanner success. A first directory scan used absolute paths and exposed that the narrow relative-path exception did not match; corrected only the boundary to permit the same frozen suffix, retaining exact fields/values and path conditions.

This is a bounded repository/credential audit, not formal anonymity, comprehensive DLP or a proof that arbitrary future data cannot be disguised. CI-policy changes still require human review; contents:read does not create an immutable branch-protection policy.

## Real remote acceptance record

Verified implementation run (read directly from GitHub API and complete job logs):

- Repository: Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours.
- Workflow: Encounter Lab Public CI.
- Run ID:38053176593; [actual run](https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours/actions/runs/38053176593).
- Branch:research-v2.2; event:push; head_sha:8d0ea53d87da17e23f76e3407ff654c1de7bd1c4.
- status:completed; conclusion:success; started2026-10-10T12:46:08Z; completed/updated2026-10-10T12:48:50Z.
- unit-tests success:335 passed in102.80s; native imports12 passed in2.17s; pip check reports no broken requirements.
- streamlit-smoke success:61 passed in14.87s; pip check succeeds.
- repository-safety success:24 tests passed in0.43s;51 frozen files unchanged; both Gitleaks history/index scans no credential findings after the documented exact digest exception; risky provider-token self-test rejected.

This record proves ONLY that exact implementation commit. The new final commit additionally disables dependency-cache restoration and adds three model-format rejection cases; it MUST obtain its own successful run. Expected test totals are never substituted for final logs. The final SHA/run URL/result are verified again in the delivery reply and public Actions history; no further untested commit is appended.

After an implementation run passes, its verified metadata can be recorded in a documentation commit. That new commit must itself run all three jobs successfully before final delivery. The final response/GitHub run attests the final SHA; a commit cannot contain its own future run ID without changing that SHA again. No unvalidated documentation commit is appended after final acceptance.
