# Zero-Money Restaurant Lead Generator

## Project Goal

Build a local-only web application that discovers U.S. restaurants through
OpenStreetMap, researches their official websites, scores AI-receptionist sales
opportunities with public evidence, and creates up to ten grounded outreach
drafts for manual review.

The application must cost nothing to operate beyond the user's existing Mac
and internet connection. It must never send email, guess contact information,
or use paid lead providers.

## Source of Truth

The approved full design is:

`docs/superpowers/specs/2026-07-24-zero-money-restaurant-lead-generator-design.md`

When a task description and the approved design disagree, the approved design
wins. Changes to product behavior require updating the design before coding.

The implementation sequence is:

`doc/implementation-plan.md`

The active coding phase is tracked in:

`doc/coding-sessions.md`

## Primary User

A solo operator selling an AI phone receptionist to restaurants. The operator
wants researched, evidence-backed prospects and reviewable email drafts without
automatic outreach.

## Version 1 Outcomes

The user can:

1. Open a local web interface.
2. Enter any U.S. city and two-letter state.
3. Discover up to 100 OSM restaurants, defaulting to 30.
4. Monitor persisted run progress.
5. Review official-site facts, contacts, validation results, score arithmetic,
   evidence, and failures.
6. Add notes and update manual outreach status.
7. Review no more than ten grounded local drafts.
8. Download qualified and rejected CSV files.
9. Restart the application without losing completed work.

## Fixed Product Rules

- Bind the web application only to `127.0.0.1`.
- Use OpenStreetMap Overpass as the only discovery source.
- Query only `amenity=restaurant`.
- Take official websites only from OSM `website` or `contact:website`.
- Crawl the homepage plus no more than five permitted same-domain pages.
- Honor `robots.txt`, conservative pacing, timeouts, response limits, and
  public-network-only URL safety.
- Accept only public business emails shown on the official website.
- Never guess an address, search for personal data, or probe SMTP mailboxes.
- Validate email syntax, domain resolution, and MX separately.
- Preserve the exact approved scoring weights and qualify at `score >= 6`.
- Store source URLs and evidence for every applied scoring component.
- Treat blocked or incomplete absence-based research as `unknown`, worth zero.
- Use SQLite as the source of truth.
- Preserve historical runs, manual notes, and manual statuses.
- Export `qualified_leads.csv` and `rejected_leads.csv` from SQLite.
- Generate no more than ten drafts per run.
- Never integrate Gmail, SMTP, automatic sending, or sequences.

## Ollama Configuration

The default local drafting model is:

`gemma4:e2b-it-qat`

Version 1 generation defaults:

| Setting | Value |
| --- | --- |
| Context | 8,192 tokens |
| Temperature | 0.4 |
| Maximum output | 220 tokens |
| Timeout | 45 seconds |
| Concurrency | One request |

Ollama receives only verified fact packets and evidence identifiers. Unsupported
model claims are rejected. Missing or invalid model output automatically uses a
deterministic template.

## Technical Direction

- Python 3.12.
- FastAPI and Uvicorn.
- Server-rendered Jinja templates.
- Vendored HTMX or small vanilla JavaScript for progress polling.
- SQLite with numbered migrations, foreign keys, WAL mode, and busy timeout.
- One durable in-process worker and one active run.
- HTTPX for network adapters.
- Selectolax or Beautiful Soup for bounded HTML parsing.
- `email-validator`, dnspython, `tldextract`, and `phonenumbers`.
- Pytest, Ruff, mypy, and Playwright.

No Docker, Redis, Celery, React build system, cloud service, paid API, or
multi-process worker is included.

## Quality Bar

A task is complete only when:

- Its new behavior was introduced test-first.
- Focused tests pass.
- The complete existing test suite passes.
- Ruff passes.
- Mypy passes after typed application code exists.
- No secret, `.env`, database, generated export, virtual environment, cache, or
  downloaded model is staged.
- The task's acceptance criteria are checked against current evidence.

## Release Acceptance

Version 1 is ready when:

- Fixture-driven tests cover discovery, crawling, extraction, scoring,
  validation, deduplication, recovery, drafting, exports, and review workflows.
- Playwright proves the local operator flow.
- No normal test calls live Overpass, websites, DNS, or Ollama.
- A bounded opt-in smoke run makes no more than one Overpass discovery request.
- The web server binds only to `127.0.0.1`.
- No route, package, button, or adapter can send outreach.
- SQLite, CSV exports, and drafts survive restart.
