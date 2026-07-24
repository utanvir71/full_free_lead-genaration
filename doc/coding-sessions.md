# Coding Session Tracker

This file controls which part of the Zero-Money Restaurant Lead Generator may
be implemented in a coding session.

Before coding, read:

1. `doc/project-plan.md`
2. `doc/implementation-plan.md`
3. `doc/coding-sessions.md`
4. `docs/superpowers/specs/2026-07-24-zero-money-restaurant-lead-generator-design.md`

The approved design is authoritative. The implementation plan defines the task
order. This tracker defines the only phase currently permitted to start.

## Session Status Tracker

Allowed status values:

- `done`
- `next session`
- `in queue`

Current status:

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 1: Foundation, Domain, and Persistence | `done` | Completed through `748db6f`; 49 tests passed, Ruff passed, and mypy passed. |
| Phase 2: OpenStreetMap Discovery and Safe Crawling | `next session` | Start Tasks 7–13 in the next coding context window. |
| Phase 3: Evidence Extraction, Contact Validation, and Scoring | `in queue` | Start only after Phase 2 is done and verified. |
| Phase 4: Pipeline, Recovery, Exports, and Drafting | `in queue` | Start only after Phase 3 is done and verified. |
| Phase 5: Local Review Interface and Release Verification | `in queue` | Start only after Phase 4 is done and verified. |

After finishing any phase, update this status tracker before ending the
session:

- Change the completed phase status to `done`.
- Change the next phase status from `in queue` to `next session`.
- Add a short note with the completion commit, test commands, and test result.
- Do not mark a phase `done` while tests or lint are failing.
- Keep exactly one phase marked `next session` until all phases are done.
- Do not begin work from an `in queue` phase.

## Global Session Rules

- Work on a non-main branch.
- Execute only the tasks assigned to the active phase.
- Follow task order unless a documented dependency requires a narrower change.
- Use test-driven development for all production behavior.
- Watch each new test fail for the expected reason before implementation.
- Preserve unrelated user changes.
- Never stage `.env`, SQLite databases, CSV exports, downloaded model files,
  virtual environments, credentials, caches, screenshots, or generated data.
- Never add Google, paid providers, Gmail, SMTP, or sending behavior.
- Run focused tests after each task.
- Run the complete existing suite and quality checks before completing a phase.
- Fix failures and rerun until the full gate passes.
- Do not mark a phase `done` while any required check fails.
- Update this tracker with exact commands and results before ending.

## Phase 1: Foundation, Domain, and Persistence

**Tasks:** 1–6

### Goal

Create the tested application shell, typed configuration, domain contracts,
authoritative SQLite schema, repositories, and durable run lifecycle needed by
all later phases.

### Scope

- FastAPI health application and Python packaging.
- Local-only bind documentation.
- Pytest, Ruff, and mypy quality commands.
- Typed operational configuration.
- Evidence-first domain models.
- SQLAlchemy/Alembic SQLite persistence.
- Transactional repositories.
- Run and job lifecycle with restart reconciliation.

### Out of scope

- Live Overpass requests.
- Website crawling or extraction.
- Scoring.
- Ollama.
- CSV exports.
- Lead-review pages beyond the health route.

### Required verification

After Task 1 creates the environment and commands:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
git diff --check
git status --short
```

Also verify:

- Uvicorn's documented host is `127.0.0.1`.
- Migration tests pass twice against a temporary database.
- No ignored runtime artifact is staged.

### Expected phase summary

Record:

- Tasks 1–6 completion commits.
- Test, Ruff, and mypy totals.
- Migration version.
- Run recovery behaviors proved by tests.
- Any approved deviations from exact planned files or interfaces.

### Phase 1 Completion Record

**Completion commit:** `748db6f`

**Task commits:**

- Task 1: `297507e` (`chore: scaffold local lead generator`)
- Task 2: `6ae94e4` (`feat: add validated application settings`)
- Task 3: `ad4eb62` (`feat: define evidence-first domain contracts`)
- Task 4: `af72dfc` (`feat: add authoritative SQLite schema`)
- Task 5: `5f113ed` (`feat: add transactional lead repositories`)
- Task 6: `748db6f` (`feat: add durable run lifecycle`)

**Exact final verification:**

```text
.venv/bin/pytest -q
49 passed in 0.61s

.venv/bin/ruff check .
All checks passed!

.venv/bin/mypy app
Success: no issues found in 20 source files

git diff --check
Passed with no output.
```

Playwright was not required for Phase 1.

Migration `0001` was applied twice against a temporary SQLite database. Tests
proved foreign keys enabled, WAL mode active, a 5,000 ms busy timeout, all 17
authoritative tables present, and uniqueness constraints protecting
idempotency.

Recovery tests proved that expired running jobs with retries remaining return
to pending, exhausted jobs become interrupted, completed jobs remain
completed, and persisted job counts are rebuilt from SQLite after creating a
fresh service instance.

No later-phase behavior or provider integration was added. `FactState` was
added alongside the planned enums so unknown, absent, false, and true remain
distinct as required by the approved design.

## Phase 2: OpenStreetMap Discovery and Safe Crawling

**Tasks:** 7–13

### Goal

Discover restaurant candidates from one bounded Overpass request and crawl only
safe, permitted, official-site pages within the six-page budget.

### Scope

- U.S. City + State Overpass query construction.
- Overpass response parsing and typed failures.
- Conservative canonical deduplication.
- Official URL normalization and SSRF prevention.
- Robots decisions and caching.
- Paced bounded HTML fetching.
- Relevant-link ranking and crawl manifests.

### Out of scope

- Search engines, directories, or alternate discovery providers.
- Website lookup when OSM has no website.
- Crawling reservation providers or social networks.
- Fact/contact extraction.
- Scoring and drafting.
- Web review interface.

### Required verification

```bash
.venv/bin/pytest tests/adapters/overpass tests/adapters/crawler tests/domain/test_normalization.py tests/application/test_discovery.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
git diff --check
git status --short
```

Also verify:

- Normal tests make zero live Overpass or website requests.
- Query snapshots contain only `amenity=restaurant`.
- A crawl can never exceed six fetched pages.
- Private targets and off-domain redirects are rejected in tests.

### Expected phase summary

Record:

- Tasks 7–13 completion commits.
- Full quality-gate results.
- Overpass query fixture coverage.
- URL/robots/fetch safety cases proved.
- Exact maximum page count proved.

## Phase 3: Evidence Extraction, Contact Validation, and Scoring

**Tasks:** 14–20

### Goal

Transform bounded website content into traceable facts, safe public business
contacts, decision-maker evidence, deterministic pain signals, and exact score
components.

### Scope

- Visible-text and stable evidence extraction.
- Business and reservation facts.
- Official-site public business contacts.
- Syntax, DNS, and MX validation.
- Official-site decision-maker name and role evidence.
- Versioned pain-signal thresholds.
- Exact scoring and qualification at 6.

### Out of scope

- Personal contact enrichment or social search.
- SMTP probing.
- Ollama fact discovery.
- Full run orchestration.
- CSV exports and drafts.
- Web review interface.

### Required verification

```bash
.venv/bin/pytest tests/adapters/extraction tests/adapters/validation tests/domain/test_scoring.py tests/application/test_qualification.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
git diff --check
git status --short
```

Also verify:

- Every applied score component links to evidence.
- Unknown absence signals add zero.
- Score 6 qualifies and score 5 rejects.
- DNS tests make no live network requests.
- No test or code synthesizes an email address.

### Expected phase summary

Record:

- Tasks 14–20 completion commits.
- Full quality-gate results.
- Exact scoring table coverage.
- Contact exclusion and validation cases.
- Versioned signal thresholds implemented.

## Phase 4: Pipeline, Recovery, Exports, and Drafting

**Tasks:** 21–27

### Goal

Execute the complete persisted research workflow, retain partial results,
export SQLite projections, and create up to ten safe local drafts using Ollama
or deterministic fallback.

### Scope

- Per-restaurant pipeline.
- Durable batch runner and retry/recovery behavior.
- Qualified and rejected CSV generation.
- Draft eligibility and deterministic ordering.
- Verified fact packets.
- `gemma4:e2b-it-qat` local adapter.
- Structured draft grounding guard.
- Deterministic fallback and draft persistence.

### Out of scope

- Sending or reading email.
- Gmail, SMTP, or external draft creation.
- Automatic Ollama installation or model pulls.
- Parallel runs or distributed workers.
- Final web review pages.

### Required verification

```bash
.venv/bin/pytest tests/worker tests/application/test_exports.py tests/domain/test_draft_policy.py tests/application/test_fact_packets.py tests/adapters/ollama tests/application/test_draft_guard.py tests/application/test_draft_generator.py tests/application/test_fallback_draft.py tests/application/test_drafts.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
git diff --check
git status --short
```

Also verify:

- Ollama absence produces a valid fallback.
- Model settings are context 8192, temperature 0.4, output 220, timeout 45.
- Unsupported model claims never become approved drafts.
- A run creates at most ten drafts.
- The dependency tree contains no Gmail or SMTP package.

### Expected phase summary

Record:

- Tasks 21–27 completion commits.
- Full quality-gate results.
- Partial-result and restart cases proved.
- CSV row counts for fixtures.
- Ollama failure modes and fallback cases.
- Draft cap and evidence-guard cases.

## Phase 5: Local Review Interface and Release Verification

**Tasks:** 28–34

### Goal

Deliver the complete local operator interface and prove the approved version 1
workflow with offline fixtures, browser tests, security checks, and release
documentation.

### Scope

- Local run dashboard and history.
- Persisted progress and safe error display.
- Qualified/rejected evidence review.
- Manual notes and status history.
- Draft review and local copying.
- Qualified/rejected CSV downloads.
- Fixture-driven full integration coverage.
- Playwright operator workflow.
- Security, setup, recovery, and release documentation.
- One explicitly opt-in bounded live smoke procedure.

### Out of scope

- Public hosting or remote access.
- Accounts, roles, or multi-user features.
- Sending, scheduling, Gmail, SMTP, or automatic reply tracking.
- Additional providers or product analytics.
- Unbounded live testing.

### Required verification

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest tests/e2e -q
git diff --check
git status --short
```

Also verify:

- The server binds only to `127.0.0.1`.
- Host, Origin, CSRF, CSP, and SSRF tests pass.
- No visible route or button can send outreach.
- The operator workflow survives refresh and interrupted state.
- SQLite, CSVs, and drafts survive restart.
- Live smoke instructions make at most one Overpass discovery request and zero
  outreach actions.

### Expected phase summary

Record:

- Tasks 28–34 completion commits.
- Full test, Ruff, mypy, and Playwright results.
- Security controls verified.
- Browser workflow proved.
- Live smoke result if the user explicitly authorized it.
- Final release commit and artifact locations.

## New-Session Prompt

Copy this into a fresh Codex session:

```text
Read every file in the doc folder first:
- doc/project-plan.md
- doc/implementation-plan.md
- doc/coding-sessions.md

Then read the approved design:
- docs/superpowers/specs/2026-07-24-zero-money-restaurant-lead-generator-design.md

Start only the phase marked `next session` in doc/coding-sessions.md.
Use a non-main branch.
Implement its tasks in order with test-driven development.
After each task, run its focused tests.
Before completing the phase, run the full test suite, Ruff, and mypy; run
Playwright when the phase requires it.
If any check fails, fix it and rerun until it passes.
Do not add paid providers, Gmail, SMTP, sending, guessed contacts, or work from
later phases.
Before ending, update doc/coding-sessions.md with the completed phase status,
next-session status, exact test results, and completion commit.
Summarize changed files and verification results, commit intentionally, and
push only if a Git remote is configured and the user has authorized publishing.
```
