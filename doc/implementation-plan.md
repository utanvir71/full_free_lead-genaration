# Zero-Money Restaurant Lead Generator Implementation Plan

> **For agentic workers:** Use `superpowers:test-driven-development` for each
> task and `superpowers:verification-before-completion` before marking it done.
> Execute only tasks included in the phase currently marked `next session` in
> `doc/coding-sessions.md`.

**Goal:** Build the approved local restaurant discovery, research,
qualification, review, and draft-preparation application.

**Architecture:** A FastAPI modular monolith serves a local Jinja interface and
runs one durable in-process worker. SQLite stores canonical businesses,
immutable run snapshots, evidence, jobs, drafts, review state, and errors.
External systems are isolated behind testable adapters.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Jinja2, vendored HTMX, Pydantic
v2, SQLAlchemy 2, Alembic, SQLite, HTTPX, Selectolax, dnspython,
email-validator, tldextract, phonenumbers, Pytest, Ruff, mypy, and Playwright.

## Global Constraints

- The approved design at
  `docs/superpowers/specs/2026-07-24-zero-money-restaurant-lead-generator-design.md`
  is authoritative.
- Bind only to `127.0.0.1`.
- OpenStreetMap Overpass is the only discovery source.
- Discover only `amenity=restaurant`.
- Official websites come only from OSM `website` or `contact:website`.
- Crawl no more than the homepage plus five same-domain pages.
- Honor `robots.txt`, one-second host pacing, URL safety, bounded timeouts, and
  response limits.
- Never guess emails, retain personal mailboxes, or perform SMTP probing.
- Preserve the exact scoring weights and qualification threshold of 6.
- SQLite is authoritative; CSVs are projections.
- Generate at most ten local drafts and never send outreach.
- Default Ollama model: `gemma4:e2b-it-qat`.
- Ollama defaults: 8,192-token context, temperature 0.4, maximum 220 output
  tokens, 45-second timeout, one request at a time.
- Missing or rejected Ollama output must use the deterministic fallback.
- No Docker, Redis, Celery, paid API, cloud deployment, Gmail, or SMTP.
- Every production behavior begins with a failing test.

## Task Execution Contract

For every task:

1. Read the task and its dependencies.
2. Write the smallest failing test for one acceptance criterion.
3. Run that focused test and confirm the expected failure.
4. Implement only enough production behavior to pass it.
5. Repeat the red-green-refactor cycle for the remaining criteria.
6. Run the task's focused tests.
7. Run the full existing suite and quality checks.
8. Inspect the diff and stage only the task's intended files.
9. Commit the independently testable task.

Until Task 1 creates the project commands, use the exact commands introduced by
that task. After Task 1, the standard quality gate is:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
```

## Phase 1: Foundation, Domain, and Persistence

### Task 1: Scaffold the Local Application

**Deliverable:** A packaged Python 3.12 FastAPI application with a health route
and reproducible quality commands.

**Dependencies:** None.

**Files:**

- Create `pyproject.toml`.
- Create `.gitignore`.
- Create `README.md`.
- Create `app/__init__.py`.
- Create `app/main.py`.
- Create `tests/test_health.py`.

**Interfaces:**

- Produce `app.main:create_app() -> FastAPI`.
- Produce `GET /health` returning `{"status": "ok"}`.

**Acceptance criteria:**

- A FastAPI test client receives HTTP 200 from `/health`.
- The documented server command binds Uvicorn to `127.0.0.1`.
- Pytest, Ruff, and mypy commands run in a local `.venv`.
- `.gitignore` excludes `.env`, `.venv`, caches, SQLite files, exports, model
  files, and local credentials.

**Focused verification:**

```bash
.venv/bin/pytest tests/test_health.py -q
.venv/bin/ruff check .
.venv/bin/mypy app
```

**Commit:** `chore: scaffold local lead generator`

### Task 2: Add Typed Configuration

**Deliverable:** Validated settings for all operational and safety limits.

**Dependencies:** Task 1.

**Files:**

- Create `app/config.py`.
- Create `.env.example`.
- Create `tests/test_config.py`.
- Modify `app/main.py`.
- Modify `README.md`.

**Interfaces:**

- Produce `Settings.load(environ: Mapping[str, str] | None = None) -> Settings`.
- Produce typed values for database path, Overpass URL, User-Agent, discovery
  limits, HTTP timeouts, crawl delay, body limit, Ollama endpoint/model,
  context, temperature, output cap, timeout, and export directory.

**Acceptance criteria:**

- Default candidate limit is 30 and accepted limits are 1–100.
- Ollama defaults exactly match the global constraints.
- Invalid URLs, nonpositive timeouts, invalid limits, and unsafe bind hosts fail
  validation.
- Tests inject settings without reading the developer's actual environment.
- No secret or API key is accepted or required.

**Focused verification:**

```bash
.venv/bin/pytest tests/test_config.py -q
```

**Commit:** `feat: add validated application settings`

### Task 3: Define Domain and Evidence Contracts

**Deliverable:** Framework-independent domain types for research and review.

**Dependencies:** Task 2.

**Files:**

- Create `app/domain/__init__.py`.
- Create `app/domain/enums.py`.
- Create `app/domain/models.py`.
- Create `tests/domain/test_models.py`.

**Interfaces:**

- Produce enums for `RunStatus`, `JobStatus`, `LeadStatus`, `SignalState`,
  `ValidationState`, and `DraftMethod`.
- Produce immutable value models for `Evidence`, `Fact`, `ContactChannel`,
  `DecisionMaker`, `ScoreComponent`, `Assessment`, `Draft`, and `StageError`.

**Acceptance criteria:**

- Every fact can reference source, bounded excerpt/value, capture time,
  extractor version, and validation state.
- Unknown, absent, false, and true cannot collapse to the same value.
- A decision maker has no personal-contact field.
- Drafts record method, evidence IDs, validation result, and version.
- Serialization round trips preserve all identifiers and enums.

**Focused verification:**

```bash
.venv/bin/pytest tests/domain/test_models.py -q
```

**Commit:** `feat: define evidence-first domain contracts`

### Task 4: Create SQLite Schema and Migrations

**Deliverable:** Repeatable database migrations for all authoritative records.

**Dependencies:** Task 3.

**Files:**

- Create `alembic.ini`.
- Create `app/db/__init__.py`.
- Create `app/db/base.py`.
- Create `app/db/session.py`.
- Create `app/db/schema.py`.
- Create `app/db/migrations/env.py`.
- Create `app/db/migrations/versions/0001_initial.py`.
- Create `tests/db/test_migrations.py`.

**Interfaces:**

- Produce `create_engine_for(settings: Settings) -> Engine`.
- Produce `migrate_database(engine: Engine) -> None`.

**Acceptance criteria:**

- Tables cover runs, jobs, businesses, aliases, run candidates, sources, crawl
  pages, facts, contacts, people, assessments, score signals, drafts, notes,
  status history, errors, and exports.
- Foreign keys are enabled.
- WAL mode and busy timeout are configured.
- Uniqueness constraints protect stable identities and idempotency keys.
- Applying migrations twice is safe.

**Focused verification:**

```bash
.venv/bin/pytest tests/db/test_migrations.py -q
```

**Commit:** `feat: add authoritative SQLite schema`

### Task 5: Implement Repositories and Transactions

**Deliverable:** Repository methods that preserve canonical state and immutable
run history.

**Dependencies:** Task 4.

**Files:**

- Create `app/application/ports.py`.
- Create `app/db/repositories.py`.
- Create `app/db/unit_of_work.py`.
- Create `tests/db/test_repositories.py`.

**Interfaces:**

- Produce repository protocols for runs, jobs, businesses, evidence,
  assessments, drafts, reviews, errors, and exports.
- Produce `SqlAlchemyUnitOfWork`.
- Produce atomic `checkpoint_restaurant(...)`.

**Acceptance criteria:**

- A restaurant checkpoint saves its related stage records atomically.
- Failed transactions leave no orphaned relational data.
- Later canonical updates do not mutate earlier run snapshots.
- Notes and lifecycle state are separate from extracted evidence.
- Integration tests use temporary SQLite files.

**Focused verification:**

```bash
.venv/bin/pytest tests/db/test_repositories.py -q
```

**Commit:** `feat: add transactional lead repositories`

### Task 6: Implement Run Lifecycle and Recovery

**Deliverable:** Validated run/job transitions and startup interruption
reconciliation.

**Dependencies:** Task 5.

**Files:**

- Create `app/domain/lifecycle.py`.
- Create `app/application/runs.py`.
- Create `app/worker/recovery.py`.
- Create `tests/domain/test_lifecycle.py`.
- Create `tests/application/test_runs.py`.

**Interfaces:**

- Produce `transition_run(current: RunStatus, target: RunStatus) -> RunStatus`.
- Produce `RunService.start(...)`, `RunService.progress(...)`, and
  `recover_expired_jobs(...)`.

**Acceptance criteria:**

- Invalid transitions are rejected.
- Only one run can be active.
- Persisted records, not process memory, determine progress.
- Expired running jobs become pending or interrupted according to retry state.
- Restart reconciliation never deletes completed lead stages.

**Focused verification:**

```bash
.venv/bin/pytest tests/domain/test_lifecycle.py tests/application/test_runs.py -q
```

**Commit:** `feat: add durable run lifecycle`

## Phase 2: OpenStreetMap Discovery and Safe Crawling

### Task 7: Build City and State Overpass Queries

**Deliverable:** Deterministic Overpass QL for an unambiguous U.S. city inside a
specified state.

**Dependencies:** Task 3.

**Files:**

- Create `app/adapters/overpass/__init__.py`.
- Create `app/adapters/overpass/query.py`.
- Create `app/data/us_states.py`.
- Create `tests/adapters/overpass/test_query.py`.

**Interfaces:**

- Produce `build_restaurant_query(city: str, state: str, limit: int) -> str`.

**Acceptance criteria:**

- The state uses its exact `ISO3166-2` identifier.
- The city boundary is constrained inside that state.
- Only `amenity=restaurant` nodes, ways, and relations are requested.
- Tags and center geometry are requested.
- User values are escaped safely.
- Snapshot tests distinguish identical city names in different states.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/overpass/test_query.py -q
```

**Commit:** `feat: build restaurant-only Overpass query`

### Task 8: Implement the Overpass Client and Parser

**Deliverable:** A bounded client that converts Overpass responses into
normalized discovery candidates.

**Dependencies:** Tasks 2 and 7.

**Files:**

- Create `app/adapters/overpass/client.py`.
- Create `app/adapters/overpass/parser.py`.
- Create `app/adapters/overpass/errors.py`.
- Create `tests/fixtures/overpass/restaurants.json`.
- Create `tests/adapters/overpass/test_client.py`.
- Create `tests/adapters/overpass/test_parser.py`.

**Interfaces:**

- Produce `OverpassClient.discover(request: DiscoveryRequest)`.
- Produce `parse_elements(payload: Mapping[str, object]) -> list[Candidate]`.

**Acceptance criteria:**

- Requests use the configured User-Agent and one query per run.
- Identical City + State discovery responses are cached for 24 hours.
- Rate limits, server failures, and timeouts retry no more than three times with
  jitter while honoring `Retry-After`.
- Invalid JSON and Overpass error payloads become typed failures.
- The client does not spray requests across fallback public endpoints.
- Nodes use coordinates; ways and relations use center geometry.
- OSM type, ID, tags, and source identity are retained.
- Normal tests never contact live Overpass.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/overpass -q
```

**Commit:** `feat: add bounded Overpass discovery adapter`

### Task 9: Normalize and Deduplicate Restaurants

**Deliverable:** Conservative canonical matching with immutable run snapshots.

**Dependencies:** Tasks 5 and 8.

**Files:**

- Create `app/domain/normalization.py`.
- Create `app/application/discovery.py`.
- Create `tests/domain/test_normalization.py`.
- Create `tests/application/test_discovery.py`.

**Interfaces:**

- Produce normalizers for OSM identity, registrable domain, phone, and address.
- Produce `DiscoveryService.reconcile(run_id, candidates)`.

**Acceptance criteria:**

- Exact OSM type and ID match first.
- Exact domain, normalized phone, and full-address fingerprint are conservative
  secondary matches.
- Name-only similarity never merges records.
- Ambiguous matches become `Needs Review`.
- Rerunning a city reuses canonical records and creates new run snapshots.

**Focused verification:**

```bash
.venv/bin/pytest tests/domain/test_normalization.py tests/application/test_discovery.py -q
```

**Commit:** `feat: reconcile duplicate restaurant identities`

### Task 10: Enforce Safe URL and Domain Policy

**Deliverable:** A reusable URL policy that prevents SSRF and off-domain
crawling.

**Dependencies:** Task 2.

**Files:**

- Create `app/adapters/crawler/__init__.py`.
- Create `app/adapters/crawler/url_policy.py`.
- Create `tests/adapters/crawler/test_url_policy.py`.

**Interfaces:**

- Produce `UrlPolicy.validate_initial(url)`.
- Produce `UrlPolicy.validate_redirect(source, target)`.
- Produce `UrlPolicy.same_official_domain(left, right) -> bool`.

**Acceptance criteria:**

- Only HTTP and HTTPS are allowed.
- Embedded credentials, malformed URLs, loopback, private, link-local,
  multicast, and non-public destinations are rejected.
- Every DNS resolution and redirect is revalidated.
- `www` and ordinary subdomains of the same registrable domain are accepted.
- Reservation providers and social networks may be recorded but not fetched.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/crawler/test_url_policy.py -q
```

**Commit:** `feat: protect official-site crawling boundaries`

### Task 11: Enforce Robots Rules

**Deliverable:** Per-run robots retrieval, parsing, caching, and evidence.

**Dependencies:** Task 10.

**Files:**

- Create `app/adapters/crawler/robots.py`.
- Create `tests/adapters/crawler/test_robots.py`.

**Interfaces:**

- Produce `RobotsPolicy.allowed(url: str) -> RobotsDecision`.

**Acceptance criteria:**

- Disallowed pages are never fetched.
- Decisions retain robots URL, rule outcome, and error state.
- Missing robots files allow crawling; timeouts use the design's conservative
  documented outcome and remain visible.
- Rules are cached only for the active run.
- Allow, deny, wildcard, missing, and timeout fixtures pass.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/crawler/test_robots.py -q
```

**Commit:** `feat: honor website robots policies`

### Task 12: Implement the Bounded Page Fetcher

**Deliverable:** A paced HTML fetcher with typed permanent and retryable errors.

**Dependencies:** Tasks 10 and 11.

**Files:**

- Create `app/adapters/crawler/fetcher.py`.
- Create `app/adapters/crawler/errors.py`.
- Create `tests/adapters/crawler/test_fetcher.py`.

**Interfaces:**

- Produce `PageFetcher.fetch(url: str, budget: RequestBudget) -> FetchedPage`.

**Acceptance criteria:**

- Same-domain, robots, and public-network checks happen before content is
  accepted.
- Host requests respect the configured one-second delay.
- Redirect, timeout, response-size, and retry budgets are bounded.
- Rate limits, server failures, and timeouts retry no more than twice.
- Permanent HTTP failures, robots denial, unsafe targets, and invalid content
  are not retried.
- Binary, oversized, blocked, unsafe, and non-success responses become typed
  persisted-friendly errors.
- Tests mock HTTP and time.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/crawler/test_fetcher.py -q
```

**Commit:** `feat: fetch official pages within safety limits`

### Task 13: Rank Links and Enforce the Six-Page Crawl

**Deliverable:** Homepage-first crawl orchestration with a complete manifest.

**Dependencies:** Task 12.

**Files:**

- Create `app/adapters/crawler/link_ranker.py`.
- Create `app/adapters/crawler/site_crawler.py`.
- Create `tests/adapters/crawler/test_link_ranker.py`.
- Create `tests/adapters/crawler/test_site_crawler.py`.

**Interfaces:**

- Produce `rank_relevant_links(homepage) -> list[RankedLink]`.
- Produce `SiteCrawler.crawl(official_url) -> CrawlResult`.

**Acceptance criteria:**

- Ranking recognizes contact, reservation, event/private dining, catering,
  locations, about/team, FAQ, and menu links.
- Duplicate and fragment-only URLs are removed.
- The crawler fetches no more than homepage plus five internal pages.
- The manifest records considered, selected, skipped, blocked, fetched, and
  failed URLs.
- Crawl completeness is explicit for absence-based scoring.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/crawler/test_link_ranker.py tests/adapters/crawler/test_site_crawler.py -q
```

**Commit:** `feat: enforce bounded restaurant site crawl`

## Phase 3: Evidence Extraction, Contact Validation, and Scoring

### Task 14: Extract Visible Text and Evidence Excerpts

**Deliverable:** Stable sanitized page text and bounded source evidence.

**Dependencies:** Tasks 3 and 13.

**Files:**

- Create `app/adapters/extraction/__init__.py`.
- Create `app/adapters/extraction/page_text.py`.
- Create `app/adapters/extraction/evidence.py`.
- Create `tests/adapters/extraction/test_evidence.py`.

**Interfaces:**

- Produce `extract_visible_text(html: str) -> PageText`.
- Produce `EvidenceFactory.from_match(...) -> Evidence`.

**Acceptance criteria:**

- Scripts, styles, hidden elements, and repetitive navigation do not pollute
  primary text.
- Evidence stores source URL, bounded excerpt, locator, timestamp, and version.
- Excerpts preserve matched phrases without exceeding the configured length.
- Identical HTML produces stable evidence identities.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/extraction/test_evidence.py -q
```

**Commit:** `feat: create stable website evidence`

### Task 15: Extract Business and Reservation Facts

**Deliverable:** Provenance-preserving core facts from OSM, JSON-LD, and HTML.

**Dependencies:** Tasks 9 and 14.

**Files:**

- Create `app/adapters/extraction/business.py`.
- Create `app/adapters/extraction/reservations.py`.
- Create `tests/adapters/extraction/test_business.py`.
- Create `tests/adapters/extraction/test_reservations.py`.

**Interfaces:**

- Produce `BusinessExtractor.extract(...) -> list[Fact]`.
- Produce `ReservationExtractor.extract(...) -> list[Fact]`.

**Acceptance criteria:**

- Extract name, address, phone, website, cuisine, hours, coordinates,
  locations, reservation method/provider/form, and call-to-reserve language.
- OSM and website facts retain separate provenance.
- Conflicts remain conflicting evidence rather than being overwritten.
- Missing fields remain unknown.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/extraction/test_business.py tests/adapters/extraction/test_reservations.py -q
```

**Commit:** `feat: extract restaurant and reservation facts`

### Task 16: Extract Public Business Contact Channels

**Deliverable:** Conservative official-site email, phone, and form extraction.

**Dependencies:** Tasks 14 and 15.

**Files:**

- Create `app/adapters/extraction/contacts.py`.
- Create `tests/adapters/extraction/test_contacts.py`.

**Interfaces:**

- Produce `ContactExtractor.extract(pages) -> list[ContactChannel]`.

**Acceptance criteria:**

- Every email is visibly present on a fetched official page.
- Explicitly obfuscated public business addresses may be decoded.
- No address is synthesized from a name, role, pattern, or domain.
- Named personal mailboxes and suspicious personal addresses are excluded.
- Public phone and contact-form evidence are retained separately.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/extraction/test_contacts.py -q
```

**Commit:** `feat: extract only public business contacts`

### Task 17: Validate Email Syntax, DNS, and MX

**Deliverable:** Independent validation states without mailbox probing.

**Dependencies:** Tasks 2 and 16.

**Files:**

- Create `app/adapters/validation/__init__.py`.
- Create `app/adapters/validation/email.py`.
- Create `tests/adapters/validation/test_email.py`.

**Interfaces:**

- Produce `EmailValidator.validate(contact) -> EmailValidationResult`.

**Acceptance criteria:**

- Syntax, domain resolution, and MX are separate results.
- Missing MX, null MX, NXDOMAIN, and timeout are distinguishable.
- DNS timeout retries once and remains unknown after repeated timeout.
- No SMTP connection or mailbox-existence claim occurs.
- DNS tests use fakes and never query the public network.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/validation/test_email.py -q
```

**Commit:** `feat: validate public email infrastructure`

### Task 18: Extract Public Decision Makers

**Deliverable:** Official-site name-and-role evidence without personal contact
enrichment.

**Dependencies:** Task 14.

**Files:**

- Create `app/adapters/extraction/decision_makers.py`.
- Create `tests/adapters/extraction/test_decision_makers.py`.

**Interfaces:**

- Produce `DecisionMakerExtractor.extract(pages) -> list[DecisionMaker]`.

**Acceptance criteria:**

- Recognized roles include owner, founder, operator, general/restaurant/
  operations manager, events/catering manager, and marketing manager.
- A result requires nearby name-and-role evidence.
- Ambiguous names and staff lists without roles remain unpromoted.
- No inferred identity, social search, personal email, or personal phone is
  attached.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/extraction/test_decision_makers.py -q
```

**Commit:** `feat: capture official decision-maker evidence`

### Task 19: Extract Versioned Pain Signals

**Deliverable:** Raw evidence-backed inputs for every approved score component.

**Dependencies:** Tasks 14–18.

**Files:**

- Create `app/domain/signal_policy.py`.
- Create `app/adapters/extraction/pain_signals.py`.
- Create `tests/adapters/extraction/test_pain_signals.py`.

**Interfaces:**

- Produce `SCORING_V1_SIGNAL_POLICY`.
- Produce `PainSignalExtractor.extract(research) -> SignalInputs`.

**Acceptance criteria:**

- Detect calling required, online booking, private events, catering, multiple
  locations, phone prominence, complex hours, FAQ/menu counts, entrée prices,
  fast-food/low-ticket positioning, contact presence, and closure evidence.
- Large FAQ means at least 10 Q&A pairs.
- Large menu means at least 40 items.
- High-ticket means median of at least five entrée prices is at least $30.
- Low-ticket means the median is below $15 or explicit quick-service evidence.
- Absence signals cite a complete crawl manifest; incomplete coverage is
  unknown.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/extraction/test_pain_signals.py -q
```

**Commit:** `feat: derive versioned receptionist pain signals`

### Task 20: Implement Exact Scoring and Qualification

**Deliverable:** Pure score arithmetic, evidence-linked components, and the
threshold classification.

**Dependencies:** Tasks 3 and 19.

**Files:**

- Create `app/domain/scoring.py`.
- Create `app/application/qualification.py`.
- Create `tests/domain/test_scoring.py`.
- Create `tests/application/test_qualification.py`.

**Interfaces:**

- Produce `score_v1(inputs: SignalInputs) -> Assessment`.
- Produce `QualificationService.assess(...)`.

**Acceptance criteria:**

- Exact deltas are `+3,+2,+2,+2,+2,+1,+1,+1,+1,-3,-3,-2` for the approved
  signals in the approved order.
- Unknown signals add zero.
- Every component records state, delta, explanation, and evidence IDs.
- Score 6 qualifies and score 5 rejects.
- No closure or contact hard override changes qualification arithmetic.
- New assessments do not mutate previous run assessments.

**Focused verification:**

```bash
.venv/bin/pytest tests/domain/test_scoring.py tests/application/test_qualification.py -q
```

**Commit:** `feat: apply exact evidence-backed scoring`

## Phase 4: Pipeline, Recovery, Exports, and Drafting

### Task 21: Orchestrate One Restaurant Research Pipeline

**Deliverable:** Discovery candidate through persisted research and assessment.

**Dependencies:** Tasks 9, 13, and 15–20.

**Files:**

- Create `app/worker/restaurant_pipeline.py`.
- Create `tests/worker/test_restaurant_pipeline.py`.

**Interfaces:**

- Produce `RestaurantPipeline.process(run_id, business_id) -> PipelineResult`.

**Acceptance criteria:**

- External adapters and repositories are injected.
- Each completed stage checkpoints before the next begins.
- A stage failure produces a typed error without corrupting earlier output.
- Idempotent retry does not duplicate facts, components, or errors.
- A full restaurant fixture produces exact expected facts and score.

**Focused verification:**

```bash
.venv/bin/pytest tests/worker/test_restaurant_pipeline.py -q
```

**Commit:** `feat: orchestrate one restaurant research workflow`

### Task 22: Run the Complete Durable Batch

**Deliverable:** Sequential candidate processing with persisted progress and
partial-result survival.

**Dependencies:** Tasks 6, 8, 9, and 21.

**Files:**

- Create `app/worker/runner.py`.
- Create `app/worker/workflow.py`.
- Create `tests/worker/test_runner.py`.
- Create `tests/worker/test_workflow.py`.

**Interfaces:**

- Produce `JobRunner.claim_next()` and `JobRunner.run_once()`.
- Produce `RunWorkflow.execute(run_id)`.

**Acceptance criteria:**

- Only one run executes.
- One failed restaurant does not stop unrelated candidates.
- Counters remain correct after every checkpoint.
- Final state is completed, completed-with-errors, failed, or interrupted as
  persisted evidence requires.
- Restarted work resumes without duplicating completed stages.
- The workflow exposes a terminal-state hook used by the export service in
  Task 23.

**Focused verification:**

```bash
.venv/bin/pytest tests/worker/test_runner.py tests/worker/test_workflow.py -q
```

**Commit:** `feat: execute resilient lead generation runs`

### Task 23: Export Qualified and Rejected CSVs

**Deliverable:** Two deterministic RFC 4180 projections generated from SQLite.

**Dependencies:** Tasks 5, 20, and 22.

**Files:**

- Create `app/application/exports.py`.
- Create `app/adapters/csv_export.py`.
- Create `tests/application/test_exports.py`.
- Modify `app/worker/workflow.py`.
- Modify `tests/worker/test_workflow.py`.

**Interfaces:**

- Produce `ExportService.generate(run_id) -> ExportResult`.

**Acceptance criteria:**

- Qualified and rejected files contain `date_found`, `restaurant_name`, `city`,
  `state`, `website`, `address`, `phone`, `recipient_email`, `contact_name`,
  `contact_role`, `reservation_method`, `pain_signal`,
  `personalization_fact`, `lead_score`, `score_breakdown`, `source_url`,
  `evidence_urls`, `email_confidence`, `outreach_status`, `date_contacted`,
  `follow_up_date`, `reply_status`, `notes`, `run_id`, `business_id`, and
  `last_seen`.
- Rows have deterministic order and escaping.
- Empty results produce header-only files.
- A temporary file is flushed and atomically renamed.
- Exporting never mutates or duplicates source data.
- Completed, completed-with-errors, failed, cancelled, and interrupted runs
  trigger exports containing all completed results.

**Focused verification:**

```bash
.venv/bin/pytest tests/application/test_exports.py -q
```

**Commit:** `feat: export qualified and rejected lead snapshots`

### Task 24: Select Draft Candidates and Build Fact Packets

**Deliverable:** Deterministic selection and minimal grounded inputs for up to
ten leads.

**Dependencies:** Tasks 17, 18, 20, and 22.

**Files:**

- Create `app/domain/draft_policy.py`.
- Create `app/application/fact_packets.py`.
- Create `tests/domain/test_draft_policy.py`.
- Create `tests/application/test_fact_packets.py`.

**Interfaces:**

- Produce `select_draft_candidates(leads, limit=10)`.
- Produce `FactPacketService.build(business_id, assessment_id)`.

**Acceptance criteria:**

- Only score-qualified, not-closed leads with fully validated public business
  email and at least one verified fact are eligible.
- Ordering is score, evidence completeness, normalized name, then stable ID.
- The cap is always ten.
- Fact packets contain only stored verified facts and evidence IDs.
- Personal contacts and unsupported decision makers are absent.

**Focused verification:**

```bash
.venv/bin/pytest tests/domain/test_draft_policy.py tests/application/test_fact_packets.py -q
```

**Commit:** `feat: select grounded draft candidates`

### Task 25: Add the Local Ollama Adapter

**Deliverable:** Optional readiness and generation calls for the approved local
model.

**Dependencies:** Tasks 2 and 24.

**Files:**

- Create `app/adapters/ollama/__init__.py`.
- Create `app/adapters/ollama/client.py`.
- Create `tests/adapters/ollama/test_client.py`.
- Modify `README.md`.

**Interfaces:**

- Produce `OllamaClient.readiness() -> OllamaReadiness`.
- Produce `OllamaClient.generate(packet, schema) -> OllamaResult`.

**Acceptance criteria:**

- Default request uses `gemma4:e2b-it-qat`, context 8192, temperature 0.4,
  output cap 220, timeout 45 seconds, and structured JSON schema.
- Missing service, missing model, timeout, and malformed response are distinct
  nonfatal outcomes.
- The application never installs Ollama or pulls a model.
- Tests fake the local API.

**Focused verification:**

```bash
.venv/bin/pytest tests/adapters/ollama/test_client.py -q
```

**Commit:** `feat: connect optional local Ollama drafting`

### Task 26: Generate and Validate Grounded Drafts

**Deliverable:** Structured subjects and bodies whose personalized claims cite
stored evidence.

**Dependencies:** Tasks 24 and 25.

**Files:**

- Create `app/application/draft_prompt.py`.
- Create `app/application/draft_guard.py`.
- Create `app/application/draft_generator.py`.
- Create `tests/application/test_draft_guard.py`.
- Create `tests/application/test_draft_generator.py`.

**Interfaces:**

- Produce `build_draft_prompt(packet)`.
- Produce `validate_generated_draft(result, packet) -> DraftValidation`.
- Produce `DraftGenerator.generate(packet)`.

**Acceptance criteria:**

- Prompts contain only verified structured facts.
- Personalized claims cite allowed evidence IDs.
- Unknown evidence IDs, new proper names, unsupported numbers/services,
  fabricated pain claims, and malformed output are rejected.
- Raw website text cannot become model instructions.
- One malformed response may receive one structured repair attempt; a second
  failure returns a rejected result for Task 27's fallback.
- Rejected model text is never stored as an approved draft.

**Focused verification:**

```bash
.venv/bin/pytest tests/application/test_draft_guard.py tests/application/test_draft_generator.py -q
```

**Commit:** `feat: guard Ollama drafts against unsupported claims`

### Task 27: Add Fallback Drafts and Persistence

**Deliverable:** Always-available evidence-backed drafts stored for local
review.

**Dependencies:** Tasks 5 and 26.

**Files:**

- Create `app/application/fallback_draft.py`.
- Create `app/application/drafts.py`.
- Create `tests/application/test_fallback_draft.py`.
- Create `tests/application/test_drafts.py`.

**Interfaces:**

- Produce `build_fallback_draft(packet) -> Draft`.
- Produce `DraftService.generate_for_run(run_id)`.

**Acceptance criteria:**

- Missing, timed-out, malformed, or rejected Ollama output uses the fallback.
- The fallback contains one verified restaurant fact, a factual receptionist
  value statement, and one permission CTA.
- Saved drafts record method, evidence, validation, version, and timestamp.
- At most ten drafts exist for a run.
- No Gmail, SMTP, send endpoint, or sending dependency exists.

**Focused verification:**

```bash
.venv/bin/pytest tests/application/test_fallback_draft.py tests/application/test_drafts.py -q
```

**Commit:** `feat: persist safe fallback outreach drafts`

## Phase 5: Local Review Interface and Release Verification

### Task 28: Build the Local Web Shell and Run Form

**Deliverable:** Server-rendered pages for creating and revisiting runs.

**Dependencies:** Tasks 2, 6, and 22.

**Files:**

- Create `app/web/__init__.py`.
- Create `app/web/routes/runs.py`.
- Create `app/web/security.py`.
- Create `app/web/templates/base.html`.
- Create `app/web/templates/runs/index.html`.
- Create `app/web/static/app.css`.
- Create `app/web/static/htmx.min.js`.
- Create `tests/web/test_runs.py`.
- Modify `app/main.py`.

**Interfaces:**

- Produce `GET /runs`.
- Produce CSRF-protected `POST /runs`.

**Acceptance criteria:**

- City, two-letter state, and 1–100 limit are validated.
- Limit defaults to 30.
- Invalid input shows inline errors and creates no run.
- Run history survives restart.
- The interface requires no frontend build system or CDN.
- Host, Origin, CSRF, autoescape, and CSP protections are active.

**Focused verification:**

```bash
.venv/bin/pytest tests/web/test_runs.py -q
```

**Commit:** `feat: add local run dashboard`

### Task 29: Show Persisted Progress and Errors

**Deliverable:** Polling-based run progress sourced only from SQLite.

**Dependencies:** Tasks 22 and 28.

**Files:**

- Create `app/web/routes/progress.py`.
- Create `app/web/templates/runs/detail.html`.
- Create `app/web/static/progress.js`.
- Create `tests/web/test_progress.py`.

**Interfaces:**

- Produce `GET /runs/{run_id}`.
- Produce `GET /runs/{run_id}/progress`.

**Acceptance criteria:**

- Counts show discovered, pending, processing, qualified, rejected, drafted,
  and failed.
- Browser refresh does not lose state.
- Interrupted and completed-with-errors states are distinct.
- Safe errors identify restaurant, stage, and message without stack traces.
- Polling stops at a terminal run state.

**Focused verification:**

```bash
.venv/bin/pytest tests/web/test_progress.py -q
```

**Commit:** `feat: display durable run progress`

### Task 30: Build Evidence-First Lead Review

**Deliverable:** Qualified/rejected lists and a complete restaurant review page.

**Dependencies:** Tasks 20 and 29.

**Files:**

- Create `app/web/routes/leads.py`.
- Create `app/web/templates/leads/index.html`.
- Create `app/web/templates/leads/detail.html`.
- Create `tests/web/test_leads.py`.

**Interfaces:**

- Produce `GET /runs/{run_id}/leads`.
- Produce `GET /leads/{business_id}`.

**Acceptance criteria:**

- Detail shows identity, reservation facts, contacts, decision makers, signal
  inputs, score arithmetic, source excerpts, crawl manifest, limitations, and
  typed errors.
- Every applied score component links to its evidence.
- Unknown signals are visually distinct from false signals.
- OSM attribution is visible.
- Review pages do not modify extracted facts or score.

**Focused verification:**

```bash
.venv/bin/pytest tests/web/test_leads.py -q
```

**Commit:** `feat: add evidence-first lead review`

### Task 31: Add Notes and Manual Status History

**Deliverable:** Safe manual workflow tracking that survives research reruns.

**Dependencies:** Tasks 5 and 30.

**Files:**

- Create `app/application/reviews.py`.
- Create `app/web/routes/reviews.py`.
- Create `tests/application/test_reviews.py`.
- Create `tests/web/test_reviews.py`.
- Modify `app/web/templates/leads/detail.html`.

**Interfaces:**

- Produce `ReviewService.add_note(...)`.
- Produce `ReviewService.change_status(...)`.
- Produce protected POST routes for notes and status.

**Acceptance criteria:**

- Allowed states are New, Needs Review, Draft Ready, Contacted, Replied, and
  Rejected.
- Rejected may be selected only from a pre-contact state.
- Every status change is timestamped.
- Contacted and Replied are manual only.
- Notes and status survive rediscovery and reassessment.
- Manual edits cannot alter evidence or computed score components.

**Focused verification:**

```bash
.venv/bin/pytest tests/application/test_reviews.py tests/web/test_reviews.py -q
```

**Commit:** `feat: track manual lead review status`

### Task 32: Add Draft Review and CSV Downloads

**Deliverable:** Local draft inspection/copying and authoritative export access.

**Dependencies:** Tasks 23, 27, and 31.

**Files:**

- Create `app/web/routes/drafts.py`.
- Create `app/web/routes/exports.py`.
- Create `app/web/templates/drafts/index.html`.
- Create `app/web/templates/drafts/detail.html`.
- Create `tests/web/test_drafts.py`.
- Create `tests/web/test_exports.py`.

**Interfaces:**

- Produce `GET /runs/{run_id}/drafts`.
- Produce `GET /drafts/{draft_id}`.
- Produce qualified and rejected CSV download routes.

**Acceptance criteria:**

- A run displays no more than ten drafts.
- Draft method, evidence, and validation are visible.
- Subject and body can be copied locally.
- There is no send button, Gmail action, SMTP action, or external copy.
- Downloads match current SQLite projections.

**Focused verification:**

```bash
.venv/bin/pytest tests/web/test_drafts.py tests/web/test_exports.py -q
```

**Commit:** `feat: review drafts and download lead exports`

### Task 33: Add Full Fixture and Browser Coverage

**Deliverable:** Offline integration and Playwright proof of the complete
operator workflow.

**Dependencies:** Tasks 21–32.

**Files:**

- Create `tests/fixtures/sites/`.
- Create `tests/fixtures/dns/`.
- Create `tests/fixtures/ollama/`.
- Create `tests/integration/test_full_pipeline.py`.
- Create `tests/e2e/conftest.py`.
- Create `tests/e2e/test_operator_workflow.py`.

**Interfaces:** Exercise only public application interfaces and fake adapters.

**Acceptance criteria:**

- Fixtures cover high-scoring, low-ticket, closed, missing-site, robots-denied,
  partial-crawl, invalid-email, no-MX, timeout, duplicate, and hallucinated
  model cases.
- Exact components, qualification, persistence, dedupe, errors, CSVs, and
  fallback drafts are asserted.
- Browser flow starts a run, observes progress, reviews evidence, updates notes
  and status, reviews drafts, and downloads both CSVs.
- Refresh and interrupted-run recovery are tested.
- No normal integration or browser test uses live services.

**Focused verification:**

```bash
.venv/bin/pytest tests/integration tests/e2e -q
```

**Commit:** `test: cover complete local operator workflow`

### Task 34: Verify Security, Documentation, and Release

**Deliverable:** Reproducible local setup and fresh evidence that version 1
meets every approved requirement.

**Dependencies:** Tasks 1–33.

**Files:**

- Create `docs/architecture.md`.
- Create `docs/scoring-policy.md`.
- Create `docs/testing.md`.
- Create `docs/release-checklist.md`.
- Modify `README.md`.
- Modify `doc/coding-sessions.md`.

**Interfaces:** No new product behavior.

**Acceptance criteria:**

- Documentation covers install, migrate, test, start, review, exports, manual
  Ollama setup, and recovery.
- A fixture demo works with Ollama absent.
- Security regression tests cover local bind, CSRF/Origin, CSP, SSRF, unsafe
  redirects, robots, prompt injection, and absence of send surfaces.
- Full Pytest, Ruff, mypy, and Playwright checks pass.
- An opt-in live smoke run is bounded to one city, one Overpass request, and
  zero outreach.
- SQLite, CSVs, and drafts survive restart.
- The phase tracker records the final commit and verification evidence.

**Focused verification:**

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest tests/e2e -q
git status --short
```

**Commit:** `docs: verify local lead generator release`

## Deferred Work

The following work is outside all five coding phases:

- Gmail, SMTP, sending, sequences, or campaign automation.
- Search engines, Google Places, Yelp, social scraping, or paid enrichment.
- Guessed/personal email discovery or SMTP mailbox probing.
- Cloud deployment, remote access, accounts, permissions, or collaboration.
- CRM integrations, automatic reply tracking, analytics dashboards, or maps.
- Automatic Ollama/model installation or model training.
- Distributed crawling, Redis, Celery, Docker, or multiple workers.
- Machine-learned or automatically tuned scoring.
- Manual editing of extracted evidence or score arithmetic.
