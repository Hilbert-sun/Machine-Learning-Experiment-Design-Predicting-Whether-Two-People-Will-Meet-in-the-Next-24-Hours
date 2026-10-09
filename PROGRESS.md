# Encounter Lab — Progress

Date: 2026-10-09 (Asia/Kuala_Lumpur)

## Result

**T01–T04 DONE.** T01 was reused; T02, T03 and T04 were implemented and verified sequentially under the user's explicit range authorization. T05–T16 remain TODO. Stop development here.

## Implementation summary

- T02: `app.py`, shared UI, eight `pages/` views, `.streamlit/config.toml` and UI tests. Chinese-first top navigation, dark/light theme support, working page links, persistent dataset choice and honest empty model/metric states. Data Sources includes official attribution and license links.
- T03: `src/downloader.py`, Data Manager integration and tests. Live Figshare metadata supplies names/URLs/sizes/MD5; streaming downloads have progress, timeouts, retries, atomic writes, skip-existing checks and partial cleanup. Manual upload refuses path traversal and silent overwrite. README documents recovery.
- T04: `src/loader.py`, validation UI and tests. Chunked source parsing checks full-file structure, numeric types and IDs; actual aliases are mapped without guessing. Copenhagen relative time, SocioPatterns UNIX time, Bluetooth -1/-2 markers, missed-call duration=-1, repeated timestamps, direction and duplicate rows are preserved for T05.
- Data Manager caches validation summaries by file size/mtime. Changed files lose Ready status. Ready requires a validated primary contact file, not just phone/SMS data; errors display Validation Failed and recovery guidance. Supplementary Facebook/gender/README/notebook files are listed but not schema-validated.
- Updated `README.md`, `TASKS.md`, `AGENTS.md`, dependencies (Streamlit minimum 1.65) and config comments. No cleaning, labels, features, models or fabricated results were added.

## Verification

- Final focused regression covering all current modules: `.venv/bin/python -m pytest -q tests/test_schema.py tests/test_data_manager.py tests/test_ui.py tests/test_downloader.py tests/test_environment.py`: **63 passed in 1.96s**.
- `.venv/bin/python -m pip check`: **No broken requirements found**.
- Real headless Streamlit server started successfully and returned HTTP 200 from its health endpoint; temporary verification server was stopped afterwards. AppTest exercised all eight registered routes.
- T03 live acquisition: six small Copenhagen files were downloaded and verified against official sizes/MD5; duplicate requests were skipped. SocioPatterns gzip downloaded successfully (653,252 bytes), with no publisher checksum. Local evidence: `reports/download_verification.json` and `reports/copenhagen_metadata.json`.
- T04 strict-parser live verification: complete calls.csv **3,600 rows**; complete sms.csv **24,333 rows**; complete SocioPatterns contacts **188,508 rows**.
- Copenhagen Bluetooth: requested/read at most **8,192 bytes** and validated **674 complete rows** from that bounded source sample. This is **not full-dataset validation**. Full bt_symmetric.csv (98,257,835 bytes according to official metadata) was not downloaded. The sample is stored under ignored reports, not the raw data directory, so it cannot mark Copenhagen Ready.
- Actual source headers: Bluetooth `# timestamp,user_a,user_b,rssi`; calls `timestamp,caller,callee,duration`; SMS `timestamp,sender,recipient`; SocioPatterns five whitespace-separated columns without a header.
- Raw/derived data, models, reports, caches, virtual environment and secrets are ignored; directory markers remain trackable.

## Resolved failures and limits

- T02 initial UI test: dataset choice reset after navigation (1 failed / 10 passed). Fixed independent persistent selection state; rerun passed.
- T04 extra-field test at a chunk boundary initially failed because Pandas C parsing silently truncated the extra field (1 failed / 23 passed). Switched to Python parsing with parser warnings treated as errors. All 24 schema tests and the full 63-test regression passed, including later-chunk field-count errors.
- Initial sandbox GitHub authentication check reported invalid credentials because network access was unavailable. Network-enabled check confirmed the existing keyring login and push permission; no token was exposed or credentials changed.
- No outstanding implementation blocker. Full Copenhagen Bluetooth validation remains a data acquisition step for the user. Data cleaning/coverage and later research tests belong to T05 onward.

## GitHub destination

User requested saving this project to their newly created repository. Identified `Hilbert-sun/-24-` (created 2026-10-09, empty main branch), confirmed push permission and configured it as origin. Source, configuration, documentation and tests are the publication scope; all downloaded datasets and local reports remain excluded. Git history and the remote branch record the publication result.

## Next recommended task

**T05 — 数据清洗和统一格式.** Wait for the user's instruction. Do not automatically start T05.
