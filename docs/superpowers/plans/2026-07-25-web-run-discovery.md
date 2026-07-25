# Web Run Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a web-created run perform one real Overpass restaurant discovery and show persisted candidates instead of remaining at zero.

**Architecture:** A synchronous local orchestration service will compose the existing `OverpassClient`, `DiscoveryService`, and run lifecycle repository. The web form queues that service using FastAPI `BackgroundTasks`; the service records a completed or failed terminal state, while the detail page reads candidates from SQLite.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite, httpx, Jinja2, pytest, Playwright.

## Global Constraints

- Make at most one Overpass discovery request per run.
- Use only the existing public Overpass endpoint; add no paid provider.
- Do not add Gmail, SMTP, sending, guessed contacts, crawling, Ollama scoring, or draft generation.
- Keep all automated tests network-free through fake or mocked discovery providers.
- Preserve cancellation as terminal: a cancelled run must never be marked completed.

---

## File Structure

- Create `app/application/web_run_discovery.py`: one bounded discovery orchestration service and its provider protocol.
- Modify `app/main.py`: construct the real Overpass-backed service once per application instance.
- Modify `app/web/routes/runs.py`: queue the service after creating a run.
- Modify `app/web/routes/progress.py` and `app/web/templates/runs/detail.html`: load and render persisted candidates.
- Create `tests/application/test_web_run_discovery.py`: lifecycle outcomes for success, empty results, provider failure, and cancellation.
- Modify `tests/web/test_runs.py` and `tests/web/test_progress.py`: background scheduling and candidate rendering.

## Task 1: Discovery orchestration service

**Files:**
- Create: `app/application/web_run_discovery.py`
- Test: `tests/application/test_web_run_discovery.py`

**Consumes:** `DiscoveryRequest`, `Candidate`, `DiscoveryService`, `RunStatus`, and `transition_run`.

**Produces:** `WebRunDiscovery.execute(run_id: str) -> None`, which changes a `running` run to `completed` after reconciliation or `failed` after a discovery exception.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_execute_reconciles_candidates_and_completes_a_running_run(tmp_path: Path) -> None:
    engine = make_running_engine(tmp_path)
    provider = FakeProvider([candidate()])

    WebRunDiscovery(engine, provider=provider, clock=lambda: NOW).execute("run-1")

    assert provider.requests == [DiscoveryRequest("run-1", "Austin", "TX", 3)]
    assert run_status(engine, "run-1") is RunStatus.COMPLETED
    assert candidate_count(engine, "run-1") == 1


def test_execute_records_failure_and_marks_run_failed(tmp_path: Path) -> None:
    engine = make_running_engine(tmp_path)

    WebRunDiscovery(engine, provider=FailingProvider(), clock=lambda: NOW).execute("run-1")

    assert run_status(engine, "run-1") is RunStatus.FAILED
    assert error_codes(engine, "run-1") == ["discovery_failed"]
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `.venv/bin/pytest tests/application/test_web_run_discovery.py -q`

Expected: collection fails because `app.application.web_run_discovery` does not exist.

- [ ] **Step 3: Implement minimal orchestration**

```python
class DiscoveryProvider(Protocol):
    def discover(self, request: DiscoveryRequest) -> list[Candidate]: ...


class WebRunDiscovery:
    def execute(self, run_id: str) -> None:
        run = self._get_running_run(run_id)
        if run is None:
            return
        try:
            candidates = self._provider.discover(
                DiscoveryRequest(run_id, run.city, run.state, run.candidate_limit)
            )
            DiscoveryService(self._engine, clock=self._clock).reconcile(run_id, candidates)
        except Exception as error:
            self._fail(run_id, str(error))
            return
        self._complete_if_running(run_id)
```

The service writes one `errors` row with `stage="discovery"`,
`code="discovery_failed"`, and a safe message when the provider raises.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `.venv/bin/pytest tests/application/test_web_run_discovery.py -q`

Expected: all new lifecycle tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/application/web_run_discovery.py tests/application/test_web_run_discovery.py
git commit -m "feat: orchestrate web run discovery"
```

## Task 2: Queue discovery from the web form

**Files:**
- Modify: `app/main.py`
- Modify: `app/web/routes/runs.py`
- Modify: `tests/web/test_runs.py`

**Consumes:** `WebRunDiscovery.execute(run_id)` from Task 1.

**Produces:** The successful `POST /runs` route schedules one local discovery task for the newly-created run.

- [ ] **Step 1: Write the failing route test**

```python
def test_creating_a_run_schedules_local_discovery(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    recorder = RecordingDiscovery()
    client.app.state.web_run_discovery = recorder
    form = client.get("/runs")

    response = client.post("/runs", data=valid_form(form), headers=origin(), follow_redirects=False)

    assert response.status_code == 303
    assert recorder.run_ids == [response.headers["location"].rsplit("/", 1)[-1]]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/pytest tests/web/test_runs.py::test_creating_a_run_schedules_local_discovery -q`

Expected: `web_run_discovery` is not called.

- [ ] **Step 3: Construct and schedule the service**

```python
# app/main.py
app.state.web_run_discovery = WebRunDiscovery(
    app.state.engine,
    provider=OverpassClient(app.state.settings),
    clock=lambda: datetime.now().astimezone(),
)

# app/web/routes/runs.py
def create_run(..., background_tasks: BackgroundTasks, ...) -> object:
    ...
    background_tasks.add_task(request.app.state.web_run_discovery.execute, run_id)
    return RedirectResponse(...)
```

- [ ] **Step 4: Run the focused route tests to verify they pass**

Run: `.venv/bin/pytest tests/web/test_runs.py -q`

Expected: all run-form tests pass without network access.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/web/routes/runs.py tests/web/test_runs.py
git commit -m "feat: start discovery from web runs"
```

## Task 3: Render discovered candidates on the detail page

**Files:**
- Modify: `app/web/routes/progress.py`
- Modify: `app/web/templates/runs/detail.html`
- Modify: `tests/web/test_progress.py`

**Consumes:** `run_candidates` persisted by Task 1.

**Produces:** The run-detail page shows a `Discovered restaurants` list with the candidate name and any public OSM website or phone captured for that snapshot.

- [ ] **Step 1: Write the failing rendering test**

```python
def test_progress_page_renders_persisted_discovered_restaurants(tmp_path: Path) -> None:
    client, engine = make_client(tmp_path)
    seed_candidate(engine, run_id="run-1", name="Northstar Grill")

    response = client.get("/runs/run-1")

    assert "Discovered restaurants" in response.text
    assert "Northstar Grill" in response.text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/pytest tests/web/test_progress.py::test_progress_page_renders_persisted_discovered_restaurants -q`

Expected: fails because the detail context has no candidates.

- [ ] **Step 3: Query and render candidates**

```python
candidates = connection.execute(
    select(schema.run_candidates)
    .where(schema.run_candidates.c.run_id == run_id)
    .order_by(schema.run_candidates.c.name_snapshot)
).mappings().all()
```

Pass `candidates` to the template and render a list only when it is non-empty.

- [ ] **Step 4: Run focused progress tests to verify they pass**

Run: `.venv/bin/pytest tests/web/test_progress.py -q`

Expected: all progress and cancellation tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/web/routes/progress.py app/web/templates/runs/detail.html tests/web/test_progress.py
git commit -m "feat: show discovered restaurants on run detail"
```

## Task 4: Full verification and local smoke check

**Files:**
- Modify: `docs/release-checklist.md` only if the existing checklist needs a new web-discovery verification step.

- [ ] **Step 1: Run all automated checks**

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest tests/e2e/test_operator_workflow.py -q
```

- [ ] **Step 2: Run a bounded manual smoke check**

Start the app locally, submit one valid Census place with a candidate limit of
`1`, then confirm the run becomes `completed` or `failed` and never remains
`running` with every counter at zero.

- [ ] **Step 3: Commit and push verified work**

```bash
git add app tests docs
git commit -m "feat: run local restaurant discovery from the web"
git push
```

## Self-Review

- The plan covers one bounded Overpass request, SQLite persistence, terminal
  run status, visible candidates, provider failure, cancellation, unit tests,
  web tests, browser verification, and manual smoke testing.
- It excludes paid providers, Gmail, SMTP, sending, guessed contacts, crawling,
  Ollama scoring, and draft generation.
- All named interfaces are defined in Task 1 before later tasks consume them.
