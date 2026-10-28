# Encounter Lab — Session Instructions

Use incremental, task-based development with limited Codex usage.

## Scope and workflow

- Default to one requested task per execution. If the user explicitly authorizes a range, complete it sequentially, verifying and recording each task before the next. Never start a task outside the authorized range.
- Read `PROJECT_SPEC.md` first, then this file, `docs/CONTRACTS.md`, `TASKS.md`, and `PROGRESS.md`. Consult relevant specification sections before implementation.
- Check task dependencies and acceptance criteria. If definitions are missing, document the blocker; never invent requirements.
- Before editing source, inspect only files relevant to the current task.
- Implement the smallest working solution. Reuse existing code, dependencies, configuration, and tests.
- Never regenerate the project or rewrite completed modules unless necessary for the requested task.
- Minimize tool calls, context, and token usage. Do not download large datasets unless the current task explicitly requires them.
- Never invent dataset fields, model scores, or experiment results.
- Run focused tests for the requested task. Mark it DONE only after verification succeeds.
- If tests fail, retain IN_PROGRESS or mark BLOCKED and document the exact failure.
- Maintain `TASKS.md` with the complete checklist, dependencies, statuses, and acceptance criteria. Maintain `PROGRESS.md` with the latest summary, test results, blockers, and next recommended task.
- Report task ID, files changed, tests performed, result, issues/blockers, and next task. Then STOP and wait for the user's instruction.

Valid task statuses: TODO, IN_PROGRESS, DONE, BLOCKED.

## Task boundaries and authorization

The first execution was limited to T01 and is complete. The user subsequently authorized T01–T04 together: reuse T01, implement and verify T02, then T03, then T04, updating status after each; stop after T04. For later requests, default to one task unless the user explicitly authorizes a range. The task board defines T01 as project/dependency initialization and T02 as the Streamlit UI framework; keep these tasks separate even though specification Phase 1 covers both. The user's one-task constraint takes precedence over broader execution instructions embedded in the specification.

## Standing publication authorization

The user subsequently instructed: “以后做完全部推送” (push all completed work going forward). After each authorized task is complete and verified, review and commit only safe task files, push all unpublished completed-task commits on the current development branch to origin, and verify synchronization. This standing authorization includes publishing the completed T28 research-v2.2 branch. Do not ask again for ordinary branch pushes. A later explicit no-push instruction overrides this default for its scope. Never upload raw/private data, individual predictions, model artifacts or credentials; never force-push, merge into main, or publish unrelated branches without authorization. This rule overrides earlier historical no-push notes in project documents; it does not authorize starting another task.

## Current authorized range

All work the user authorized on 2026-10-28 is DONE and published on research-v2.2: T35–T40 (rolling validation, Hawkes baseline/features, participant holdout, day analysis, wider Hawkes grid), DOCS-PRESENT, DEMO-DEPLOY (live demo https://hjm59payrde6ronekgiqsn.streamlit.app/ from demo_app.py), REPORT-UPDATE (report v2), README-EN, LICENSE (GPL-3.0, user's choice) and CONTRACT-TESTS. No task is in progress. STOP and await a new instruction; do not start research, tuning on exposed dates, main merges, tags, releases or new deployments without explicit authorization.

## Local environment

- Use Python 3.11 and the project-local `.venv`.
- Run focused tests with `.venv/bin/python -m pytest`.
- Treat dataset and model directories as local artifacts; never commit data, trained models, secrets, or the virtual environment.
- The GitHub destination authorized by the user is `https://github.com/Hilbert-sun/Machine-Learning-Experiment-Design-Predicting-Whether-Two-People-Will-Meet-in-the-Next-24-Hours` (renamed from `Hilbert-sun/-24-` during publication); preserve existing remote history and never force-push.

## Core invariants (details and enforcing tests: docs/CONTRACTS.md)

Read the matching section of docs/CONTRACTS.md before touching any research, inference, cache, CI, demo, report or license file; every rule there is binding. In short:

- Inputs use only data strictly before t; labels use (t, t+24h]; split boundaries purge crossing label windows; thresholds, calibration and any selection use validation data only.
- Unknown or low-coverage absence is never a negative or zero and never enters binary metrics; observed positives stay positive.
- Exposed test dates are never used to choose thresholds, features, parameters, windows or grids; follow-up studies say so explicitly.
- Frozen evidence (51 files pinned by the trusted baseline, including the 7 root FROZEN_DOCUMENTS) is never edited or moved; frozen code whose hash defines a run id is not modified.
- Raw data, models, per-sample predictions, credentials and PDFs/renders stay out of Git; public outputs are reviewed aggregates without participant/pair IDs.
- Public deployments use demo_app.py only; no page that downloads, imports, trains or reads local data joins DEMO_PAGES.
- Never weaken repository safety, CI, the Gitleaks policy or the GPL-3.0 LICENSE text.

