# Encounter Lab — Binding research and engineering contracts

These sections were moved verbatim from AGENTS.md on 2026-10-28 (CONTRACT-TESTS). They remain binding: AGENTS.md requires reading the matching section before touching a module. Each section lists the tests that enforce its machine-checkable parts; `tests/test_contract_index.py` fails if a section is dropped or a listed test disappears. Rules that are review or process duties stay binding even where no test can check them.

## Prediction data contract

- T07 candidates use contacts strictly before t; labels use (t, t+24h]. Unknown/low-coverage samples are excluded from primary evaluation, and absent events without adequate scans keep a null label.
- T08 features use [t-window, t) only. Join labels/features by timestamp, user_min and user_max; never include future label coverage or eligibility fields in model inputs.
- Communication, RSSI, weekday and coverage fields unavailable from reliable sources remain null, not zero. Default weekday origin is unconfirmed. SocioPatterns currently has no samples eligible for the primary evaluation policy.
- T09 splits whole prediction times chronologically and purges labels with t+24h >= the next set's start. Calibration uses early validation, tuning uses later validation, with the same strict label-window separation.
- Fit preprocessing/models on train only; all-null train columns are removed. Parameters, calibration and thresholds use validation only. Keep final test scores for the final evaluation task.
- Phase-three initial verification used synthetic fixtures. T17 subsequently trained genuine Copenhagen models; reports/T17_REAL_EXPERIMENT.md and T17_METRICS.json are the real evidence. SocioPatterns still has zero primary-eligible samples. Never relabel unknowns or present fixture metrics as research results.
- Prediction Lab requires t strictly after the saved model's validation-label information deadline. Future mode must not read/display actual outcomes. Feature-window policy must match the saved model; preserve legacy full-bank models with a null window contract.
- Evaluation uses frozen models/thresholds and exact saved input signatures. All window/communication ablations run on validation only. E3 stays unavailable without verified communication availability; never fabricate scores.
- Native TreeSHAP applies to XGBoost/LightGBM base raw margins, not calibrated probabilities. Other local sensitivity methods must not be labeled SHAP or causal. Keep synthetic-fixture provenance in pages, figures and exports.
- T17's held-out test scores have now been reported. Do not use them to choose new thresholds/features/hyperparameters; later tuning needs a new validation design. Preserve the original T17 results, including worse Logistic Regression probability scores and raw/calibrated XGBoost variants.
- Reports remain ignored except the five T17, fifteen T18–T22, nine T23–T27, seven T30, five T31 and three T32 reviewed aggregate deliverables explicitly whitelisted by filename in .gitignore. Do not broaden that whitelist to per-run private manifests, individual samples, large HTML bundles or model files.

Enforced by: `tests/test_labels.py::test_exact_label_window_boundaries`, `tests/test_labels.py::test_low_coverage_never_creates_a_negative_label`, `tests/test_leakage.py::test_grouped_chronological_split_purges_equal_boundary_and_preserves_test`, `tests/test_leakage.py::test_calibration_and_tuning_are_purged_and_separate`, `tests/test_leakage.py::test_cohort_excludes_unknown_and_low_coverage_without_imputing_targets`, `tests/test_prediction.py::test_actual_probability_pair_symmetry_and_future_mode_hides_outcome`, `tests/test_prediction.py::test_model_information_deadline_self_pair_and_window_mismatch_rejected`

## Research window contract (T18–T22)

- Main cohort is shared1d historical candidates, full7d source span, original0.5 future scan coverage, exact dataset/time/pair keys and labels; all windows share split hashes. Source span is not proof of continuous observation.
- Research features are bounded_window_v1 from window_features.py; never feed legacy E2 banks as equivalent strict budgets. All counts/activity/network/RSSI/scan/frequency/recency use the selected1/3/7d interval only.
- Research WindowModel reuses ModelRegistry estimators/persistence but requires neutral bounded features and matching history_window_days. Local models use models/.window_study to stay out of legacy UI selectors.
- Parameters/seed/split/threshold/calibration/fold/uncertainty rules were frozen before new test scores. Raw models are reported because3 validation dates cannot support independent calibration plus>=2 tuning dates after purge.
- Four primary test days are below the8-day bootstrap-CI gate; paired daily and leave-one-day-out ranges are descriptive, not confidence intervals. Prespecified expanding folds are dependent robustness evidence; no significance or long-term claim.
- Separate7d candidate expansion reports reach counts only; its population differs from the main1d pool. Do not compare expanded-pool AP as a pure history-window effect. Do not compare T17/new raw AP as identical-cohort improvements.

Enforced by: `tests/test_window_features.py::test_older_history_and_future_perturbations_respect_every_feature_budget`, `tests/test_window_cohort.py::test_candidates_are_past_only_and_common_span_and_hashes_hold`, `tests/test_window_cohort.py::test_twenty_day_support_preserves_purge_and_disables_impossible_calibration`, `tests/test_window_robustness.py::test_forward_folds_have_complete_grouped_days_and_strict_future_boundaries`, `tests/test_window_robustness.py::test_paired_day_ranges_refuse_mismatched_labels_and_do_not_fake_ci`

## Research edition delivery (T23–T27)

- History Window Study default settings reuse verified frozen evidence. Altered settings produce separately versioned validation-only jobs. Never use displayed frozen test scores to choose new parameters/windows/coverage.
- Case Explorer must generate candidates from[t-1d,t) contacts and bounded features from raw pre-t contacts/observations, never a future-filtered evaluation bank. Use times strictly after every saved training/selection-label deadline. Actual outcomes belong to the separate explicit-backtest reveal API; unreliable absence stays Unknown.
- DatasetAdapter namespaces every source, validates schema/time/IDs and keeps calendar capacity separate from reliable observation. Unknown processed tick units must not become seconds/days. Missing contacts must not become negatives.
- New public source downloads require verified license/real URL and a bounded schema probe first. Do not infer data license from a site's source-code footer, or infer access restriction from an outage. No bypass of restricted sources.
- Manual imports validate before publishing and refuse replacement of existing raw files. Schema/time/license policy changes invalidate adapter caches. Parsed data and manifests are local except reviewed aggregate deliverables.
- Full verification uses project .venv pytest, window_verify, research_delivery and real UI/export checks. Ten navigation pages are delivered. Research interfaces use hidden bounded-window model registries; legacy model UI contracts remain intact.

Enforced by: `tests/test_dataset_catalog.py::test_parser_namespace_missing_days_and_unknown_negatives`, `tests/test_dataset_catalog.py::test_processed_time_ticks_are_not_invented_as_seconds_or_days`, `tests/test_dataset_catalog.py::test_manual_import_validates_before_publishing_and_never_overwrites_raw`, `tests/test_dataset_catalog.py::test_schema_and_unit_policy_changes_invalidate_catalog_cache`

## T28 as-of inference contract

- Use as_of_candidates/as_of_features/predict_as_of; no evaluation cohort, eligibility field, future scan coverage or stored evaluation-bank membership may determine inference inputs. All reads constructing inputs are clipped strictly beforet.
- Verify namespace, source time origin,24h target, bounded_window_v1 feature/window identity, saved model checksum/calibration identity and training/validation/threshold/calibration label endpoints. Unknown provenance or any endpoint>=t rejects. Existing metadata is adapted read-only; do not edit old manifests to invent earlier cutoffs.
- historical_blind_replay is historical simulation, with an already time-valid model. prospective_inference requires an independently verified aware UTC anchor and fresh pre-t observations for both devices; file mtime/download date is not evidence. Static archives without an anchor reject live mode.
- reveal_outcome is a separate explicit backtest action, never called by blind inference. Only adequately observed complete horizons justify negative outcomes; unique observed bins, not duplicate row counts, determine coverage.
- Expanded as-of membership is not covered by old future-filtered-cohort performance/calibration guarantees. Re-evaluation and trusted live clock/feed provenance are suggested future work, not started by T28.

Enforced by: `tests/test_asof_inference.py::test_all_data_reads_for_prediction_have_pre_t_filter`, `tests/test_asof_inference.py::test_every_label_information_deadline_at_or_after_t_rejects`, `tests/test_asof_inference.py::test_prospective_requires_verified_current_clock_and_both_fresh_devices`, `tests/test_asof_inference.py::test_outcome_requires_explicit_backtest_before_any_read`, `tests/test_asof_inference.py::test_unreliable_absence_incomplete_horizon_or_duplicate_scans_stay_unknown`

## T29 Time Machine contract

- Use pages/10_Time_Machine.py and time_machine.py/time_machine_ui.py. Inference uses T28 directly; no old future-filtered case/feature bank or offline study prerequisite.
- Prediction succeeds before Freeze is enabled; Freeze precedes independent Reveal. Serialized frozen probability/input/model-version records remain immutable; reveal never recomputes probabilities. Outcomes remain Contact/No Contact/Unknown with coverage/completeness reasons.
- Date/hour, pair, dataset, mode, selected windows/models and normal data/model/evidence file-version edits reset active prediction/freeze/reveal state. Future edits may invalidate a version but cannot change the stored frozen record or pre-t features/probabilities on re-prediction.
- Records are session-only and private, not Git artifacts. Model provenance and label deadlines are shown. Static archives reject live mode via T28 clock/freshness guards.
- Version metadata checks before/after actions are not atomic ingestion snapshots or proof of historical upload availability. Those concerns/performance caches belong to T32; new population-quality audit belongs to T30. Do not implement those tasks during T29.

Enforced by: `tests/test_time_machine.py::test_lifecycle_requires_predict_and_freeze_and_frozen_payload_is_immutable`, `tests/test_time_machine.py::test_context_covers_date_pair_mode_windows_models_and_processed_version`, `tests/test_time_machine.py::test_prediction_never_reveals_and_absent_future_scans_reveal_unknown`

## T29-FIX label coverage contract

- Read each selected model's min_scan_coverage through unchanged T28 read_model_contract, not freely supplied row/widget values. Selected window policies must agree for a unified prediction/reveal; reject mixed policies before inference/outcome access.
- Freeze common future_label_policy and per-model verified_min_scan_coverage alongside probabilities; the existing full frozen JSONSHA protects these fields. Reveal validates consistency and passes the frozen threshold explicitly to reveal_outcome. Missing/invalid legacy policy never falls back to0.5.
- Prediction schema2 is included in context identity to invalidate old sessions, including cached pre-fix revealed outcomes. New Predict/Freeze is required. Coverage-policy metadata is known before prediction; actual future scan evidence is still read only by explicitReveal.

Enforced by: `tests/test_time_machine_coverage.py::test_mixed_verified_window_policies_fail_before_prediction_or_reveal`, `tests/test_time_machine_coverage.py::test_frozen_policy_tampering_or_missing_legacy_policy_cannot_read_future`, `tests/test_time_machine_coverage.py::test_workflow_upgrade_clears_cached_legacy_reveal`

## T30 audit interpretation

- asof_audit.py freezes all pre-t candidate probabilities before any outcome/old-cohort read. Common prediction validity is past-only; future known/Unknown and strict covered populations are separate.
- Observed positive evidence is known even with low future coverage; absent events need complete sufficiently scanned horizons. Unknown never becomes0 and never enters binary metrics. Reliable-subset metrics do not identify unbiased performance of all candidates.
- Extra candidates have strongly selective positive-only known labels; AP=1 in added known-only samples is degenerate, not perfect prediction. Compare population/prevalence/Unknown rates alongside model metrics.
- Four dates and repeated participants/pairs allow descriptive differences/leave-one-day sensitivity only, no significance/CI claim. No threshold/parameter/calibration selection on these exposed dates.
- Individual predictions/labels/errors/HTML stay under ignored data/processed/asof_audit/<run_id>. Seven aggregate report files are explicitly whitelisted; no broad report/data whitelist. --verify-only recomputes metrics/funnels/groups/reliability/errors from local frozen samples.

Enforced by: `tests/test_asof_audit.py::test_batch_predictions_match_individual_T28_and_future_rows_cannot_change_them`, `tests/test_asof_audit.py::test_reveal_requires_authorization_before_any_future_read`, `tests/test_asof_audit.py::test_unknowns_excluded_common_population_metrics_and_error_counts_recompute`, `tests/test_asof_audit.py::test_empty_reliable_subset_has_no_invented_metrics`

## T31 multi-source exploration contract

- positive_retrieval.py uses ONLY [t-1d,t) candidates, bounded [t-window,t) record frequency/last recency/common-neighbor scores, descending stable rankings and ascending source/minID/maxID ties. Fixed K5/10/20; no fitted model, test-driven rule/window selection or binary labels.
- Explicit backtest separately reads (t,t+24h] positive contact keys AFTER scores/rankings freeze. Unrecorded candidates remain Unknown; no binary Precision/AP/ROC/etc. Capture denominators are observed in-pool positives; all-positive capture and candidate reach separately expose outside-pool positives. Zero denominators stay null.
- Per-window dates differ; compare windows only on common_7d dates/shared1d candidates. Both Workplaces have only3 complete7d dates; HighSchool only2 complete1d dates and0 complete3/7d dates. These are descriptive short-span findings, no significance or cross-source quality leaderboard.
- Source namespace is mandatory. Exact canonical(timestamp,pair) duplicates count once in this NEW study; old raw/processed files remain untouched. Unknown RealityMining tick units prohibit day/24h conversion. SocialEvolution needs verified lawful actual schema/time/license and raw-only provenance before use; unavailable is not successful acquisition.
- CLI python -m src.multisource_exploration uses existing verified catalog caches read-only; missing caches go only under new ignored multisource directory. No downloads, no refits. Private score/future/pair records/HTML never leave ignored data/processed/multisource/<run_id>.
- Only five exact reports/multisource/T31 filenames are whitelisted. Public graphs use these measured aggregate outputs only; small nonzero count/ratio families and histograms are suppressed, no participant/pair IDs. Privacy coarsening is not a formal anonymity guarantee. actual_k is summed selected ranks over snapshots in public aggregates; per-snapshot values stay local.
- Event timestamps and complete archive span are not badge-online coverage or historical ingestion evidence. T32 remains a separate future task.

Enforced by: `tests/test_positive_retrieval.py::test_future_invariance_and_history_change`, `tests/test_positive_retrieval.py::test_reveal_boundaries_unknown_and_authorization`, `tests/test_positive_retrieval.py::test_empty_denominators`, `tests/test_positive_retrieval.py::test_time_unit_and_span_guards`, `tests/test_multisource_exploration.py::test_unverified_social_file_cannot_enter_study`

## T32 performance/cache/snapshot contract

- Keep original immutable data/processed/performance/T32_BASELINE.json, INPUTS/PRESERVATION/BASELINE_RECEIPT and all5-repeat raw records local. optimized_release is the verified final cold/warm series; earlier optimized/optimized_v2/optimized_final are diagnostics, not final claims. Report actual medians/ranges/native process RSS, same-host/input/cache-mode comparisons and explicit security-overhead regressions. No tracemalloc-only or cold-vs-warm speedup claim.
- snapshot_manager pins byte-verified read-only copies of normalized contacts/observations, selected model manifest/weights and provenance. Bind namespace/report/processing/protocol/time identity; nested reads must use bound paths. Check live and copied bytes before returning; source_snapshot_changed aborts without automatic source-version retry or pending cache publication. Corrupt INACTIVE copies may re-pin the SAME verified source bytes into a new immutable version; active corruption aborts.
- SafeCache only stores private JSON/Parquet bundles under ignored data/processed/t32_cache (or explicit ENCOUNTER_CACHE_ROOT). Final hashed commit manifest and version pointer publish after outer snapshot verification; interrupted writes preserve old pointers. No probabilities cached. Keys include relevant source/policy/time/window/coverage/algorithm; model clones key exact manifest/weights and retain dependency/object checks. Every prediction STILL checks model deadlines, namespace/window/calibration and prospective clock/freshness.
- bounded_history reads raw pre-t max-window contacts/scans once and independently filters each window through unchanged frozen T20 feature math. Do not alter window_features/model_registry/evaluate or frozen statistical sources for performance. Positive retrieval incrementally dedups exact canonical records, preserving adjacent times/distinct pairs. No unit reinterpretation or new negatives.
- TimeMachine schema3 adds frozen source snapshot identity, establishment time and ingestion_time_status=unavailable; invalidates old active sessions. Establishment/download/mtime is NOT ingestion time. Model/time/pair/source changes reset state; explicit Reveal and verified frozen coverage policy remain unchanged. Snapshots provide stable trusted archive consistency, not atomic live acquisition, adversarial-owner immutability, atomic multi-pointer commits or power-loss durability. Final-check/publication TOCTOU and orphan-version retention remain explicit limits.
- Public aggregate report memoization is content-hash checked and copied, never a shared private prediction. Old DatasetCatalog explicit scans/HistoryWindowStudy statistical flows remain intact. Only three exact reports/performance/T32 filenames are whitelisted. No raw measurement JSON, pickle parity receipts, cached model copies, individual scores/predictions or host paths in Git.
- New optimized T31 full reproductions auto-route to data/processed/performance/research/<run_id>/aggregate_export; never replace published T31 reports/root study or old run. performance_audit checks all T30 probabilities/funnels/Unknown/metrics and full T31 records/topology/scores/rankings/117 aggregates before publishing performance summaries. T33 must use public synthetic tests without these private reproduction artifacts.

Enforced by: `tests/test_safe_cache.py::test_interrupted_publish_preserves_prior_valid_pointer`, `tests/test_safe_cache.py::test_source_change_guard_does_not_retry_or_publish`, `tests/test_snapshot_consistency.py::test_changed_while_copying_never_commits`, `tests/test_snapshot_consistency.py::test_nested_requests_must_use_bound_dependencies_and_copy_integrity`

## T33 public CI and repository integrity

- .github/workflows/ci.yml: Ubuntu/Python3.11, trusted official SHA-pinned checkout/setup-python, read-only contents, persist-credentials=false, no cache restoration, full Git history, bounded timeouts; push/PR research-v2.2. Three mandatory acceptance jobs(unit-tests/streamlit-smoke/repository-safety), no continue-on-error, skip or full-suite filtering.
- Install requirements.txt, pip check and all native imports in real Linux runners. macOS requirements-lock.txt is not a Linux lock. Do not download research data or copy ignored artifacts into CI. Tests use synthetic tmp_path/mocks/public aggregates; default pytest HTTP guards requests and urllib. Private real reproduction is separate, never fabricated by fixtures.
- tools/check_repository_safety.py scans actual Git index bytes, not merely ignore rules. Only44 reviewed report paths and empty data/model markers; private/binary/model/env/oversized/credential/personal-path content rejects. Frozen44 reports plus7 research documents compare against trusted commit5f3be86, not candidate-generated hashes. Changing frozen evidence or trusted baseline needs separate human authorization.
- Pinned/hash-verified upstream Gitleaks8.30.1 scans all reachable history and exact tracked/staged content with redaction and fail exits. Provider-risk runtime self-test must fail. .gitleaks.toml preserves every default/provider rule; only13 reviewed row_hash digests in exact sample_key_hash/key_hash fields under five frozen paths are exempt from generic-api-key. Do not broaden to whole paths/commits or ignore actual credentials.
- Success requires actual completed/success run with exact FINAL HEAD and all3 jobs success, actual counts/timestamps/pip/native/safety evidence. After editing documentation/status and pushing a new commit, wait again; final run metadata can be attested in final response to avoid self-referential commit churn. No private raw logs/envs/tokens in Git. CI is not full real-data reproduction, formal anonymity, unreviewable immutable policy or branch protection configuration. T34 was the final research task. The separately authorized current product scope above controls this session; after its final acceptance STOP and await a new instruction.

Enforced by: `tests/test_ci_environment.py::test_workflow_retains_complete_tests_and_minimal_read_only_permissions`, `tests/test_ci_environment.py::test_live_http_is_refused_before_any_network`, `tests/test_repository_safety.py::test_index_bytes_are_scanned_including_force_added_ignored_env`, `tests/test_repository_safety.py::test_real_historical_public_evidence_unchanged`, `tests/test_repository_safety.py::test_gitleaks_exceptions_only_cover_known_frozen_digest_lines`

Addendum (2026-10-28, user-authorized): tools/check_repository_safety.py REVIEWED_MEDIA allows exactly one binary file, docs/media/demo.gif, pinned to its SHA256 and GIF signature (≤1 MB). Any change to that GIF needs a new human review and hash update; never add other paths without the user's explicit authorization. Enforced by `tests/test_repository_safety.py::test_only_the_exact_reviewed_demo_gif_is_allowed`.

## T35 rolling-origin contract

- src/rolling_validation.py freezes protocol plus the full fold plan (data/processed/rolling/<run_id>/PROTOCOL_FROZEN.json) before fitting. Folds: one test time; 3 validation times; >=4 train times; t+24h strictly before the next set; >=20 per class per set. Unchanged T21/T22 models/parameters/seed/max-F1 threshold, no calibration/tuning. Any fit failure drops the fold for all models.
- 11 evaluated test days (study days 17–27) were all previously exposed (T17/T22 walk-forward/T21–T22 test); report as fixed-protocol re-evaluation, never a pristine holdout. Day-block bootstrap intervals describe day-to-day variation only; participants/pairs repeat.
- Pooled rows mix folds with different training sizes and include T19 train/purged/validation dates; never compare T35 AP to T22 AP as the same population.
- Private predictions/receipt stay in ignored data/processed/rolling/<run_id>. Public aggregates live only in studies/rolling_validation/ (JSON/Markdown, no CSV, no IDs) because reports/ is fixed by the trusted baseline whitelist. --verify-only recomputes the public JSON from local predictions.
- T36 Hawkes must reuse this frozen fold plan and contrasts; decay choices only on fold validation.

Enforced by: `tests/test_rolling_validation.py::test_fold_plan_purges_label_windows_and_needs_history`, `tests/test_rolling_validation.py::test_end_to_end_synthetic_rolling_summary_has_bootstrap_and_no_selection`, `tests/test_contract_index.py::test_public_study_aggregates_carry_no_private_fields`

## T36 Hawkes contract

- src/hawkes_baseline.py fits per-(t, pair) exponential-kernel Hawkes (mu, alpha<=0.99) by MLE on that pair's distinct [t-7d,t) contact times only; no labels. Forecast 1-exp(-Lambda) ignores within-horizon excitation (lower bound).
- Half-life grid {0.5,2,8,24}h is chosen per T35 fold on validation AP only. Every fold chose the 0.5h boundary; extending the grid now would be post-exposure selection and needs a new validation design.
- Reads the verified frozen T35 receipt/predictions; private scores stay in ignored data/processed/hawkes/<run_id>; public aggregates only in studies/hawkes_baseline/ (no IDs, no 'key' field names). --verify-only recomputes them.

Enforced by: `tests/test_hawkes_baseline.py::test_scores_only_read_strict_past_contacts`, `tests/test_hawkes_baseline.py::test_half_life_is_selected_on_validation_only`

## T37 Hawkes-feature contract

- src/hawkes_features.py feeds XGBoost (unchanged T21/T22 parameters/seed/threshold rule, no calibration/tuning) 7d bounded features plus all four T36 Hawkes grid scores; no half-life selection. Uses the frozen T35 folds; reuses checksum-verified T36 scores and scores missing train times with the same function (one reused time is recomputed for equality). Reference AP must match T36 exactly.
- Result: +0.0031 AP over 7d XGBoost ([0.0003, 0.0062], 9/11 days): report as a negligible increment on previously exposed dates, not a generalizable improvement. Private predictions in ignored data/processed/hawkes_features/<run_id>; public aggregates only in studies/hawkes_features/.

Enforced by: `tests/test_hawkes_features.py::test_fit_drops_train_all_null_columns_and_uses_hawkes_signal`, `tests/test_hawkes_features.py::test_fold_predictions_only_cover_evaluated_test_times`

## Documentation layout (DOCS-PRESENT)

- Guides live in docs/ (docs/README.md indexes them); supplementary studies in studies/. Root keeps only README, AGENTS, PROJECT_SPEC, TASKS, PROGRESS, generated DATASET_CATALOG.md and the 7 FROZEN_DOCUMENTS, which the trusted baseline pins by path and must not move.
- README headline figure docs/figures/rolling_ap.svg is generated by docs/figures/build_readme_figure.py from public T35/T37 JSON only; regenerate it rather than hand-editing.
- deliverables/ is the REPORT-FULL record at 478a320; its plain-text file names refer to the pre-move layout and stay byte-identical.
- The local T32 preservation manifest (data/processed/performance/T32_PRESERVATION.json) was already stale before this move (70 protected files changed during P01–P03); it is not a current publication gate.

Enforced by: `tests/test_documentation.py::test_document_local_links_exist`, `tests/test_contract_index.py::test_frozen_documents_stay_at_repository_root`

## Online demo boundary (DEMO-DEPLOY)

- Public deployments must use demo_app.py (fail-closed), never app.py. src/demo_mode.py DEMO_PAGES = Home, Data Sources, Play, Explore, Research Hub; they read only tracked repository files. All other routes render a local-only notice. Never add a page that downloads, imports, trains, scans local data or shows pair-level records to DEMO_PAGES.
- Two layers are mandatory: demo_app.py blocks locked routes, and every non-DEMO page starts with `stop_if_locked(__file__)`, because a cold server can route a first request through legacy pages/ routing and run a page without the entry script (reproduced and fixed 2026-10-28). Enforced by `tests/test_demo_mode.py::test_locked_page_refuses_even_when_run_without_the_demo_entry`.
- The demo server has no data/ or models/; never upload raw data, models or per-sample outputs to a deployment. Deploying/sign-in is the user's action.

Enforced by: `tests/test_demo_mode.py::test_demo_entry_blocks_local_research_pages`, `tests/test_demo_mode.py::test_demo_set_is_public_only_and_normal_app_unchanged`

## T38 participant-holdout contract

- src/participant_holdout.py: 5 prespecified salted hash partitions; train/threshold only on A–A pairs of each frozen T35 fold; test B–B and A–B; unchanged T21/T22 protocol. References are T35 all-participant XGBoost and T36 Hawkes on the same rows.
- The A–A training set is 23–29% of full training rows, so the −0.009 to −0.023 AP gap mixes unseen people with less data; never report it as a pure stranger effect. Partitions share people and are not independent replications.

Enforced by: `tests/test_participant_holdout.py::test_held_out_people_never_reach_training_or_thresholds`, `tests/test_participant_holdout.py::test_fold_gate_drops_folds_without_class_support`

## T39 day-analysis contract

- src/day_analysis.py is descriptive only: frozen T35/T36 predictions and T20 7d features, per-day AP, AP/prevalence and Spearman rho over 11 dependent days. No fitting/selection. Never label days as weekdays/weekends (origin unconfirmed); compare days on AP/prevalence as well as AP.

Enforced by: `tests/test_day_analysis.py::test_day_table_reports_lift_over_prevalence_per_day`

## T40 wide Hawkes-grid contract

- src/hawkes_short.py reuses the T36 per-pair MLE with a prespecified 5–1440 minute grid and a log-sum-exp excitation recursion (must match T36 within 1e-6 on shared half-lives). Per-fold validation selection only. Grid extension was motivated by T36 selections after T36 test scores were seen: report as a follow-up check.
- Result: optimum interior at 15–30 minutes; test AP −0.0028 vs T36 (interval includes 0). Do not further tune the grid on these dates.

Enforced by: `tests/test_hawkes_short.py::test_stable_excitation_matches_t36_form_and_survives_short_half_lives`, `tests/test_hawkes_short.py::test_grid_is_prespecified_ascending_and_includes_t36_grid`

## Report v2 (REPORT-UPDATE)

- deliverables/v2/build_report_v2.py composes v2 from the unchanged v1 Markdown plus deliverables/v2/chapter_11.md; every new number is read from studies/*/T3x_RESULTS.json and asserted. v1 Markdown, figures and REPORT_VERIFICATION.json stay byte-identical (build asserts this). v2 links reuse v1 figures; only figure_11_1.svg is new.
- PDFs and page renders stay local (not in Git). The v2-only reportlab kinsoku patch hangs full-width punctuation in the 12pt right guard; build_report.py v1 behaviour is unchanged (make_pdf gained optional output/cover parameters with v1 defaults).

Enforced by: review — deliverables/v2/build_report_v2.py asserts v1 byte-identity and study numbers at build time in the separate document environment (not run in CI).

## License

- LICENSE is the unmodified official GNU GPL-3.0 text (sha256 3972dc97…6986, asserted by tests/test_documentation.py), chosen by the user. It covers repository code and documentation only; third-party datasets keep their own licenses. Never alter LICENSE text or relicense without the user's instruction.

Enforced by: `tests/test_documentation.py::test_license_is_official_gpl3_and_scoped_to_code`

## Play research reference (PLAY-REF)

- src/play_reference.py builds studies/play_reference/PLAY_REFERENCE.json from local T07 labels and T08 features once; Play reads only that reviewed public JSON, never datasets or models. The fixed-rule entertainment index (src/chance_encounter.py, byte-pinned) is unchanged.
- Cells with fewer than 200 samples or fewer than 20 of either class are suppressed; no IDs. The card must always state it describes Copenhagen study pairs and is not the user's probability; answers outside the 28-day data (超过30天/从未/不确定/不记得) show an honest unavailable message.

Enforced by: `tests/test_play_reference.py::test_public_table_is_complete_suppressed_and_aggregate_only`, `tests/test_play_reference.py::test_lookup_ready_suppressed_and_unavailable_answers`, `tests/test_play_reference.py::test_result_page_shows_reference_without_changing_index`, `tests/test_chance_encounter_ui.py::test_standalone_page_never_opens_research_artifacts`

