# Encounter Lab — Progress

Date:2026-10-10 (Asia/Kuala_Lumpur)

**T23–T27 — DONE. All T01–T27 task statuses are DONE within documented source eligibility/access limits.** The user authorized the remaining five tasks in one execution. Implemented and verified sequentially; stopped after T27. No remote push. Historical T17 progress is in f116951; T18–T22 progress is in c5da210. Their frozen statistical code, raw data, labels/features, models and reports remain unchanged.

## T23 — History Window Study DONE

Added pages/8_History_Window_Study.py, src/window_ui.py and top navigation. Four regions:Experiment Setup/Cohort Audit/Window Comparison/Case Explorer. Dataset/candidate/coverage/window/model/seed/calibration controls invoke real jobs; default settings verify/reuse frozen evidence, altered settings create source/settings-hashed validation-only jobs. Reuses existing strict cohort/features/registry/calibration code. Invalid dataset evidence, unsupported calibration, missing files or insufficient days fail explicitly. Different controls/source/artifact signatures invalidate displayed results.

Real metric/PR/reliability/per-day/paired-delta charts, class prevalence, filter funnel, split date/purge audit, CSV/JSON/standalone HTML downloads and saved-model case probabilities work. Case times must follow model-selection information deadline; future mode never reads targets; only explicit backtest reads matching exported outcomes, otherwise Unknown. Research models remain hidden from legacy UI selectors.

Focused initial tests:14 passed in2.17s. Actual Copenhagen AppTest verified frozen charts,3 downloads, model case and dataset switch invalidation. T27 additionally exercised new-source selection/eligibility block and future/backtest behavior.

## T24 — Dataset Catalog DONE

Added source registry, src/dataset_catalog.py, pages/9_Dataset_Catalog.py and source tests. Extensible DatasetAdapter validates declared schema, finite integer timestamps/IDs, canonical isolated pairs, source/processed hashes, duplicates/missing dates and calendar-complete1/3/7d snapshots. Calendar capacity is separate from actual primary eligible observation; Copenhagen requires empty-scan evidence and eligible purged chronology. New public acquisitions require confirmed source/license/real URL plus a bounded first schema probe; full files reuse the existing streaming downloader. Manual imports validate before publication and refuse replacement of existing raw files. Source/schema/license/unit/version changes invalidate catalog caches. No archive paths are extracted.

Initial catalog/downloader/navigation verification:28 passed in2.35s. Original source scan reproduced Copenhagen2,426,279 contacts/692 contact IDs and High School188,508/327. New-source manifests are stored locally under data/processed/catalog. No existing loader/downloader/statistical source was changed.

## T25 — Reality Mining DONE; exploratory_only

Verified Netzschleuder metadata/Bluetooth-edge semantics and Mendeley processed redistribution. Public frontend file-list API/root-folder parameter returned actual filename/download URL/size/SHA256.32KB probe preceded10,848,197-byte full acquisition under CC BY4.0; official SHA256 ededff41b0befdd6ba370602d496dc8b93cc38c3a39d2e47ecd82443d093bf49 matched.

Measured96 IDs,1,086,403 rows,2,539 pairs;1,058,831 repeated canonical endpoint/tick records,27,572 unique combinations. Third-column ticks0–233 have unknown scale: no seconds/day conversion, observed-day span or24h labels invented. No online/empty-scan evidence; exploratory_only, no AP. Mirror reports1,086,404 edges (one-row redistribution difference disclosed); mirror data license was not established from its site-code footer, so no full mirror download. Source/dictionary/limitations reports saved.28 focused catalog/schema tests passed after tick/duplicate safeguards.

## T26 — Other source verification DONE; research limits retained

Official public-domain Workplace2015/2013 files passed bounded gzip/ZIP probes before full download.2015:217 IDs/78,249 rows/4,274 pairs, timestamps28,840–1,022,380,11.499306 days.2013:92/9,827/755,28,820–1,016,440,11.430787 days. Each has two dates without positive records;1/3/7d complete-span snapshots9/7/3.7d time-only60/20/20 purge gives0/0/1 train/validation/test dates:insufficient_days. Both lack independent online logs, so exploratory_only with zero reliable primary dates; no AP and no cross-source merging.2013 publisher calendar description differs from timestamp-derived extent; actual seconds/Study Days retained without silently repairing the discrepancy.

Social Evolution live official overview/dictionary connections failed; not evidence of403/authentication restriction. Indexed official dictionary describes endpoints/prob2, six-minute sensing and whole-period interpolation risk. Actual header/timezone/license/lawful full path remain unverified; catalog not_yet_verified and no real file acquired. Explicit schema/timezone parser is tested on labeled synthetic fixtures, not claimed as real-source parsing.42 focused catalog/schema/downloader tests passed in1.65s. Reports distinguish completed investigation from unavailable real prediction eligibility.

## T27 — Final research delivery DONE

Created RESEARCH_REPORT.md, WINDOW_STUDY.md, DATASET_CATALOG.md and a read-only src/research_delivery.py command. Aggregate CSV/JSON combine genuine T17 and1/3/7d evidence while separating cohorts/prevalence/calibration. Source JSON records all six independent dataset states. Report-generation command never trains or downloads. Exact selected report/CSV/JSON hashes and checks are in reports/T27_VERIFICATION.json.

Main Copenhagen XGBoost AP1d/3d/7d remains0.5887225/0.6274940/0.6913660;7d−1d+0.1026435. Only4 test days and prior T17 overlap:descriptive same-source evidence, not pristine independent validation or significance. Raw calibration policy and few-day CI refusal preserved. T17 raw/calibrated values, all comparator results including poor1d-frequency probabilities, subgroup/date/forward-fold diagnostics are unchanged. Different T17/new cohorts make raw AP directly incomparable.

## Verification commands/results

- `.venv/bin/python -m pytest -q`: **196 passed in9.49s**. Includes ten-page navigation AppTest and meaningful source/window/model/UI safeguards.
- Final focused catalog/window/new navigation tests:22 passed in2.38s after import/source integration.
- Real manual AppTest:all10 pages load; frozen study8 charts/3 downloads; actual future and explicit backtest cases; changed-source invalidation/ineligible-source block;6-source catalog scan. Local details:reports/T27_UI_CHECK.json.
- Genuine changed-seed43/Logistic Regression1d+7d job ran on validation only; exported metrics recomputed and completed job cache reused. No reported test used for this selection. Unsupported independent calibration was correctly rejected. Local receipt:reports/T27_VALIDATION_JOB_CHECK.json.
- `.venv/bin/python -m src.window_verify` via final delivery/verification:all5 frozen stages' binary metrics recompute,36 saved models reproduce complete exported probabilities, original T17 evidence and frozen T21/T22 statistical hashes match.
- `.venv/bin/python -m src.research_delivery`: six local source manifests/hashes verified;14 actual frozen model/window metric rows exported; no implicit fit/download.
- Real CSV/JSON/standalone bundled Plotly HTML exported and validated; large HTML remains ignored. Aggregate reports contain no individual IDs or home paths.
- Temporary localhost-only Streamlit server started; root and health endpoints HTTP200; server stopped. Local receipt:reports/T27_STARTUP_CHECK.json.
- Git diff checks and explicit staged-file safety audit cover original frozen files, raw/individual/model/credential exclusion. Local safe commit ID is reported in the reply/Git history; no push.

## Corrected failure and remaining limitations

T24 initial focused tests:27 passed/1 failed because a test searched pandas' truncated table-string representation for a hidden column value. Replaced with direct eligibility_status column comparison;28 focused tests then passed and final full196 pass. No inaccurate eligibility status was found. Early Mendeley API without root-folder parameter returned a public error payload; inspecting the public frontend confirmed folder_id=root, after which official metadata/probe/hash checks succeeded. Nonfatal PyArrow CPU-probe/bare Streamlit warnings persisted.

External data limitations remain scientific/source outcomes:Reality Mining time units and scanner availability unverified; Workplace insufficient7d prediction dates and observation evidence; Social Evolution source/license/raw provenance unavailable. No source was reclassified as trainable merely because a parser opened it. Copenhagen recorded scan bins/coverage are proxies, targets are device proximity, observations are short and pairs/users recur. No fake results, future-information features, random split or repeated-test tuning was added.

## Files and stop

Changed/new runtime files:src/ui.py, src/window_ui.py, src/dataset_catalog.py, src/research_delivery.py;two research/catalog pages;source registry and focused tests. Updated AGENTS/TASKS/PROGRESS/README and exact-file ignore exceptions. New public root reports plus nine explicitly reviewed aggregate report files are safe Git scope. Raw sources, parsed/feature/label Parquet, model weights/manifests, individual predictions, private jobs/API receipts and large HTML remain ignored. No extra dependencies installed.

**All requested remaining tasks T23–T27 complete. No next task; STOP.** Social Evolution real-data acquisition/training and other unsupported-source experiments remain unavailable as explicitly documented, not claimed complete research models. No automatic push or new experiment.
