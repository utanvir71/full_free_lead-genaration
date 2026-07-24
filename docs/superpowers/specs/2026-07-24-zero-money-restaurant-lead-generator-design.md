# Zero-Money Restaurant Lead Generator Design

**Status:** Approved design
**Date:** 2026-07-24
**Product:** Local restaurant lead generator for an AI phone receptionist
**Primary user:** A solo operator researching and contacting U.S. restaurants

## 1. Product Promise

The product is a local-only web application that helps one operator discover,
research, qualify, and prepare outreach drafts for U.S. restaurant prospects
without paid data providers. Every qualification reason and personalized draft
claim must be traceable to public evidence.

The system automates repetitive research while preserving a mandatory human
review step. It never sends outreach.

## 2. Problem

Manual restaurant prospecting is slow, inconsistent, and difficult to repeat.
Fully automated prospecting creates different problems: poor source quality,
guessed contact information, unsupported personalization, and messages sent
before the sales process is proven.

The product must provide a practical middle ground:

- Automate OpenStreetMap discovery, bounded website research, contact
  validation, evidence capture, scoring, and first-draft preparation.
- Keep final verification, editing, Gmail entry, sending, and reply tracking
  under the user's control.
- Preserve all research history so previously reviewed restaurants are not
  repeatedly reinvestigated.

## 3. Goals and Success Criteria

| Goal | Version 1 success criterion |
|---|---|
| Evidence-backed qualification | Every applied scoring reason has a source URL, bounded excerpt or structured source value, and capture timestamp. |
| Safe contact discovery | No guessed, inferred, private, or personal email is retained. Every retained email has separate syntax, DNS, and MX results. |
| Deterministic scoring | Fixture tests produce the exact expected component weights, total, and qualification result. |
| Resilient processing | A downstream failure never deletes an earlier successfully persisted stage. |
| Reliable history | Re-running the same location does not duplicate canonical restaurant records or overwrite manual notes and statuses. |
| Useful exports | Qualified and rejected CSV snapshots are generated from SQLite after every terminal run state, including partial runs. |
| Grounded drafts | No accepted draft claim lacks supporting stored evidence, and no run creates more than ten drafts. |
| Local usability | After startup, the user can run discovery, inspect evidence, update status and notes, review drafts, and download exports without using the terminal. |

## 4. Scope

### 4.1 Included

- Localhost-only web interface.
- Required U.S. city and state input.
- Adjustable discovery limit from 1 to 100, defaulting to 30.
- OpenStreetMap Overpass as the only discovery and geographic source.
- Discovery restricted to `amenity=restaurant`.
- Official websites taken only from OSM `website` or `contact:website` tags.
- Robots-aware crawling of the official homepage plus at most five relevant
  same-domain pages.
- Evidence-backed extraction of business details, reservation methods,
  contacts, decision makers, and qualification signals.
- Public official-site business emails only.
- Email syntax, DNS-domain, and MX validation without SMTP probing.
- Exact deterministic lead scoring and a qualification threshold of 6.
- SQLite as the authoritative data store.
- Qualified and rejected CSV exports.
- Local lead review, notes, and timestamped workflow statuses.
- Up to ten local reviewable drafts per run.
- Optional local Ollama generation using user-installed lightweight models.
- Deterministic draft fallback whenever Ollama is absent or unsafe.
- Stage-level errors, partial-result preservation, restart recovery, and
  bounded retries.

### 4.2 Explicitly excluded

- Google Maps, Google Places, Yelp, OpenTable, TripAdvisor, social platforms,
  paid databases, general search, or directory discovery.
- Automatic website lookup when OSM has no official website tag.
- Non-restaurant OSM amenities such as cafés, bars, fast food, food courts,
  or takeaway-only businesses.
- Guessed email patterns, private contact data, SMTP mailbox probing, or
  personal-email enrichment.
- Crawling external booking providers, social networks, or pages outside the
  official registrable domain.
- Gmail API, SMTP, browser automation, sending, scheduling, sequences,
  follow-up automation, or automatic reply tracking.
- Cloud hosting, remote access, user accounts, permissions, or collaboration.
- A full CRM, analytics warehouse, map interface, or model-based score tuning.
- Automatic Ollama installation, model downloading, training, or GPU
  management.
- Parallel distributed crawling, Redis, Celery, Docker, or multiple services.

## 5. Architecture Decision

### 5.1 Options considered

| Option | Benefits | Costs |
|---|---|---|
| FastAPI modular monolith with a persistent in-process worker | One local command, durable progress, restart recovery, strong module boundaries, and straightforward testing. | Web and worker share one process; not intended for horizontal scaling. |
| Streamlit with a synchronous pipeline | Fastest initial interface implementation. | Long-running work, progress recovery, lifecycle state, and browser testing are awkward. |
| FastAPI with a separate worker process and SQLite queue | Better process isolation and an easy path to independent worker restarts. | Requires two processes and adds SQLite coordination without a version 1 user benefit. |

### 5.2 Decision

Use a single-process modular monolith:

- Python 3.12.
- FastAPI and Uvicorn bound to `127.0.0.1`.
- Server-rendered Jinja templates.
- Lightweight vendored HTMX for two-second progress polling.
- SQLite with WAL mode, foreign keys, and a busy timeout.
- A persistent SQLite-backed job table processed by one in-process worker.
- HTTPX for Overpass, website, and Ollama requests.
- Selectolax or Beautiful Soup for HTML parsing.
- `urllib.robotparser` for `robots.txt`.
- `email-validator`, dnspython, offline-configured `tldextract`, and
  `phonenumbers`.
- Standard-library CSV generation.

The architecture is intentionally local and simple. It must preserve clean
dependency direction so the worker could move to another process later without
rewriting domain rules or external adapters.

### 5.3 Dependency direction

```text
web and adapters -> application services -> domain rules
```

The domain layer must not import FastAPI, HTTPX, SQLite/SQLAlchemy, Ollama, or
template code.

### 5.4 Suggested module boundaries

```text
app/
  domain/          # Entities, evidence, scoring, status, eligibility policies
  application/     # Run, research, review, drafting, and export use cases
  worker/          # Durable job claiming, workflow stages, retry, recovery
  adapters/
    sqlite/        # Migrations, repositories, job persistence
    overpass/      # Query construction, HTTP client, response parsing
    crawler/       # URL policy, robots, fetching, link ranking
    extraction/    # Facts, contacts, decision makers, pain signals
    validation/    # Email syntax, DNS, MX
    ollama/        # Local model readiness and structured generation
    csv_export/    # Qualified and rejected projections
  web/             # FastAPI routes, Jinja templates, static assets
  config.py
```

## 6. User Experience

### 6.1 Start a run

The user enters:

- City.
- Two-letter U.S. state.
- Candidate limit, default 30 and constrained to 1–100.

The interface validates the fields, confirms that discovery uses public OSM
infrastructure, and prevents more than one active run.

### 6.2 Monitor a run

The run page polls persisted SQLite progress and shows:

- Discovered.
- Pending research.
- Crawling.
- Validating.
- Scored.
- Qualified.
- Rejected.
- Drafted.
- Failed.

Refreshing or closing the browser does not lose progress. Errors are shown as
safe typed messages without stack traces.

### 6.3 Review a lead

A lead-detail page presents:

- Restaurant identity and OSM source.
- Official website and crawl manifest.
- Extracted business facts.
- Reservation method and booking provider.
- Public contact channels and validation states.
- Public decision-maker name and role evidence, when available.
- Complete score arithmetic.
- Evidence excerpts and source URLs.
- Unknown signals and crawl limitations.
- Run history.
- Manual notes and status history.

Extracted evidence and computed score components are immutable. Notes and
workflow status are editable.

### 6.4 Review drafts

Drafts show:

- Subject and body.
- Whether Ollama or the deterministic fallback generated the draft.
- Evidence supporting each personalized claim.
- Validation outcome.
- A local copy action.

There is no send action and no connection to Gmail.

### 6.5 Export

The user can download:

- `qualified_leads.csv`.
- `rejected_leads.csv`.

SQLite retains complete run history; the CSV files represent the latest
projection for the selected run.

## 7. Discovery and Deduplication

### 7.1 City resolution

The state is resolved through a local two-letter state table and an Overpass
administrative boundary carrying the matching `ISO3166-2` value. The city
boundary must be nested within the selected state.

If the boundary is ambiguous or unavailable, the run fails visibly instead of
widening silently to the entire state.

### 7.2 Overpass behavior

- One discovery request per run under normal operation.
- Query nodes, ways, and relations tagged `amenity=restaurant`.
- Request tags, node coordinates, and centers for ways and relations.
- Use a meaningful User-Agent and show OSM attribution in the interface and
  exports.
- Honor `Retry-After`.
- Cache identical City + State discovery results for 24 hours.
- Do not spray requests across fallback public endpoints.

### 7.3 Canonical identity

Deduplication follows a conservative order:

1. Exact OSM type and element ID.
2. Exact normalized official registrable domain.
3. Normalized phone number.
4. Normalized full address fingerprint.

Name-only similarity never merges restaurants. Ambiguous secondary matches are
placed in `Needs Review`.

A new run creates a new immutable run snapshot even when it reuses an existing
canonical business.

## 8. Safe Website Crawling

### 8.1 Website eligibility

Only HTTP and HTTPS URLs supplied by OSM `website` or `contact:website` fields
are eligible. Missing website tags are recorded as an expected limitation.

Every initial URL, DNS result, and redirect is checked to reject:

- Loopback, private, link-local, multicast, or otherwise non-public targets.
- Non-HTTP schemes.
- Embedded credentials.
- Malformed URLs.
- Redirects outside the official registrable domain.

Ordinary subdomains and `www` variants of the same registrable domain are
allowed.

### 8.2 Crawl budget

The crawler fetches:

1. The homepage.
2. Up to five ranked relevant same-domain pages.

Relevant page signals include:

- Contact.
- Reservations.
- Private dining or events.
- Catering.
- Locations.
- About or team.
- Menu or FAQ.

The total fetched-page budget never exceeds six. The crawl manifest records
considered, selected, skipped, blocked, fetched, and failed URLs.

### 8.3 Responsible fetching

- Respect `robots.txt` using the declared crawler User-Agent.
- Make one request at a time per host.
- Wait at least one second between host requests by default.
- Enforce connect/read timeouts, redirect limits, response-size limits, and
  HTML content types.
- Apply bounded retries only to transient responses.
- Store sanitized, bounded evidence excerpts and content hashes rather than
  unlimited raw HTML.

Robots denial, unsafe targets, unsupported content, and permanent HTTP errors
are recorded and not retried.

## 9. Evidence and Extraction

### 9.1 Evidence contract

Every extracted fact contains:

- Stable evidence ID.
- Fact type.
- Normalized value.
- Source URL or OSM source identifier.
- Bounded exact excerpt or structured source value.
- Extraction method and version.
- Capture timestamp.
- Validation state.

Unknown, absent, false, and true are distinct states. A failure to inspect is
never treated as proof of absence.

### 9.2 Extracted business facts

- Restaurant name.
- Address.
- Phone.
- Official website.
- Cuisine.
- Opening hours.
- Coordinates.
- Reservation method and provider.
- Public email and its page.
- Official contact form.
- Number of locations.
- Private dining or events.
- Catering.
- Public decision-maker name and role.
- Pain-signal inputs.

Conflicting OSM and website values are retained with separate provenance rather
than silently overwritten.

### 9.3 Contact restrictions

A retained email must:

- Appear publicly on a fetched official-site page.
- Represent a business or role mailbox rather than a named personal mailbox.
- Pass syntax validation.
- Have a resolvable domain.
- Have valid MX records.

Explicitly obfuscated but publicly displayed business addresses may be decoded.
Addresses are never constructed from a person, role, pattern, or domain.

DNS timeouts and temporary failures produce an unknown validation state rather
than an invalid conclusion. The system never performs SMTP probing.

### 9.4 Decision makers

Supported public roles include:

- Owner or founder.
- Operator.
- General manager.
- Restaurant manager.
- Operations manager.
- Events manager.
- Catering manager.
- Marketing manager.

A decision-maker record requires nearby official-site name-and-role evidence.
No personal email or phone is attached, inferred, or searched elsewhere.

## 10. Scoring Policy

The `scoring-v1` function is pure and deterministic.

| Signal | Points |
|---|---:|
| Reservations explicitly require calling | +3 |
| No online booking path or provider found | +2 |
| Private dining or events offered | +2 |
| Catering offered | +2 |
| Two or more locations | +2 |
| Phone heavily promoted | +1 |
| Complicated or split hours | +1 |
| Large FAQ or menu | +1 |
| High-ticket menu | +1 |
| No public contact route | -3 |
| Permanently closed | -3 |
| Fast-food or low-ticket positioning | -2 |

A total score of 6 or greater is qualified. A total below 6 is rejected. No
hidden override changes this arithmetic.

Each signal is `awarded`, `denied`, or `unknown`. Unknown contributes zero.
Every awarded or denied component stores its outcome, point delta, explanation,
and evidence IDs.

### 10.1 Version 1 signal interpretations

- **Phone heavily promoted:** shown in a header, hero, sticky action, or on at
  least two crawled pages.
- **Complicated hours:** split service periods, service-specific schedules, or
  materially different daily schedules.
- **Large FAQ:** at least 10 identifiable question-and-answer pairs.
- **Large menu:** at least 40 identifiable menu items.
- **High-ticket:** the median of at least five clearly parsed entrée prices is
  at least $30.
- **Low-ticket:** the median of at least five clearly parsed entrée prices is
  below $15, or explicit fast-food/quick-service positioning exists.
- **Multiple locations:** at least two distinct official-site addresses.
- **No public contact:** no public phone, validated business email, or official
  contact form was found after a complete allowed-page crawl.
- **No online booking:** awarded only after a complete crawl finds no booking
  link, provider, form, or reservation instruction.

Absence-based signals are unknown when crawling is incomplete, blocked, or
unsafe.

These interpretations are versioned policy. Future changes create a new policy
version and do not rewrite historical assessments.

## 11. Qualification and Draft Eligibility

Qualification and draft eligibility are separate.

A restaurant is qualified when its `scoring-v1` total is at least 6, even if
another fact makes it unsuitable for outreach. This preserves the exact scoring
requirement.

A qualified restaurant is draft-eligible only when:

- It is not supported as permanently closed.
- A public business email appears on the official website.
- Syntax, DNS, and MX validation pass.
- At least one restaurant-specific verified fact supports personalization.

Draft candidates are sorted by score descending, evidence completeness,
normalized restaurant name, and stable business ID. A run creates no more than
ten drafts.

## 12. Ollama and Draft Safety

### 12.1 Runtime expectations

Ollama is optional and manually installed by the user. The default configured
model must be a lightweight 3B-class model appropriate for an 8 GB Apple
Silicon Mac. The model name and local endpoint are configuration values.

The application:

- Checks local endpoint and model readiness.
- Never installs Ollama or pulls a model.
- Sends one request at a time.
- Uses temperature zero and structured JSON output.
- Uses a bounded context.
- Gives the model no tools and no network access.

Missing Ollama is an expected operating condition, not a failed product setup.

### 12.2 Grounding

Ollama receives a structured fact packet containing only verified facts and
evidence IDs. Raw website text is untrusted data and is never treated as model
instructions.

Generated personalized claims must cite valid evidence IDs. Validation rejects:

- Unknown evidence IDs.
- New unsupported names or proper nouns.
- Unsupported numbers.
- Fabricated services, features, compliments, or pain claims.
- Malformed structured output.

Rejected output is never promoted as an accepted draft.

### 12.3 Fallback

Ollama absence, timeout, invalid output, or unsupported claims automatically
produce a deterministic fallback draft. The fallback uses:

- Restaurant name.
- Permitted contact context.
- One verified restaurant-specific fact.
- A factual AI-receptionist value statement.
- One permission-based call to action.

Every saved draft records its generation method, evidence IDs, validation
result, and timestamp.

## 13. Workflow Status

The stable business lifecycle is:

```text
New -> Needs Review -> Draft Ready -> Contacted -> Replied
```

`Rejected` may be applied from any pre-contact state.

`Contacted` and `Replied` are always manual because the application cannot send
or read email. Every status change is timestamped. Research reruns never
overwrite a manual status or note.

## 14. Persistence Model

The SQLite schema contains:

- `runs`: immutable location/configuration snapshots and run state.
- `jobs`: durable stage work, leases, attempts, retry time, error code, and
  idempotency key.
- `businesses`: canonical restaurant identity and current manual lifecycle.
- `business_aliases`: OSM IDs, domains, phones, addresses, and merge history.
- `run_candidates`: immutable run-to-business discovery snapshots.
- `source_records`: OSM tags and source identifiers.
- `crawl_pages`: URL, robots decision, response metadata, sanitized content
  hash, and fetch outcome.
- `facts`: typed values, provenance, excerpts, extractor versions, and
  validation state.
- `contacts`: email/phone/form and separate validation/classification results.
- `people`: official-site public name/title evidence.
- `assessments`: run-specific total, qualification, and scoring version.
- `score_signals`: rule, delta, state, explanation, and linked evidence.
- `drafts`: versioned subject/body, grounding evidence, generator, and
  validation.
- `notes`: manual notes.
- `status_history`: manual lifecycle changes.
- `errors`: typed stage failures.
- `exports`: file paths, row counts, and generation timestamps.

Foreign keys and uniqueness constraints are enabled. Repository operations use
transactional checkpoints. Run snapshots and historical evidence are immutable.

## 15. Worker and Recovery

### 15.1 Run states

- `queued`.
- `running`.
- `completed`.
- `completed_with_errors`.
- `failed`.
- `cancelled`.
- `interrupted`.

### 15.2 Durable jobs

Each job stores:

- Stage.
- Status.
- Attempt count.
- Next-attempt timestamp.
- Lease expiration.
- Typed error.
- Idempotency key such as `run_id/business_id/stage/version`.

Each successful stage commits before the next stage is scheduled. Expired
running jobs return to pending after restart. Previously persisted stages are
not duplicated.

### 15.3 Retry policy

- Overpass rate-limit, server, or timeout failures: up to three bounded retries
  with jitter, honoring `Retry-After`.
- Website rate-limit, server, or timeout failures: up to two bounded retries.
- DNS timeout: one retry.
- Ollama timeout or schema failure: one repair/retry, then fallback.
- SQLite busy: short bounded retry.
- Integrity violations, robots denial, unsafe URLs, permanent HTTP errors, and
  unsupported content are not retried.

The user can retry one recoverable business or all recoverable failures in an
incomplete run.

## 16. CSV Exports

CSV files are generated only from authoritative SQLite records.

Both exports include:

- Run and stable business IDs.
- Restaurant name, city, state, website, address, and phone.
- Recipient email and email-confidence/validation state.
- Contact name and role when officially evidenced.
- Reservation method.
- Pain signals and evidence summary.
- Personalization fact.
- Score, qualification, and score breakdown.
- Source URLs.
- Outreach status.
- Date found, last seen, date contacted, follow-up date, reply status, and
  notes where present.

Rows are deterministic and RFC 4180-safe. Empty exports contain headers.
Generation writes a temporary file and atomically replaces the target.

## 17. Security and Ethics

- Bind only to `127.0.0.1`.
- Validate Host and Origin and protect state-changing requests against CSRF.
- Use template autoescaping and a restrictive Content Security Policy.
- Use no CDN runtime dependency.
- Revalidate every DNS resolution and redirect to prevent SSRF.
- Treat all crawled text as hostile data.
- Honor `robots.txt` and conservative pacing.
- Never crawl private systems, personal-data sources, or non-official domains.
- Never guess an email or test mailbox existence through SMTP.
- Never claim that a restaurant is losing calls or revenue; describe verified
  workflows as an opportunity.
- Show OSM attribution.
- Never infer that outreach occurred merely because a draft exists.

## 18. Testing Strategy

### 18.1 Unit tests

- Every score component, unknown behavior, and threshold boundary.
- Draft cap and eligibility.
- Status transitions.
- URL normalization and domain policy.
- Link ranking and page budget.
- Email classification and validation states.
- Evidence and excerpt stability.
- Draft grounding validation.

### 18.2 Fixture-based adapter tests

- Overpass queries, ambiguous locations, malformed responses, and duplicate
  elements.
- JSON-LD and ordinary HTML extraction.
- Robots allow/deny/missing/timeout.
- Off-domain redirects, private-IP targets, oversized and non-HTML responses.
- DNS success, missing MX, null MX, and timeout.
- Ollama unavailable, malformed, and adversarial hallucinated responses.

Normal tests make no live Overpass, website, DNS, or Ollama calls.

### 18.3 Repository and workflow tests

- Repeatable migrations.
- Canonical deduplication and immutable run history.
- Notes and status survival across reruns.
- Transaction rollback.
- Job leasing, interruption, and restart recovery.
- Partial crawl and per-restaurant failures.
- Deterministic CSVs and draft snapshots.

### 18.4 Browser tests

The browser suite covers:

- Starting a run.
- Polling progress.
- Reviewing qualified and rejected evidence.
- Editing notes and statuses.
- Reviewing drafts.
- Downloading both CSVs.
- Refreshing during a run.
- Reviewing interrupted partial results.
- Confirming that no sending action exists.

### 18.5 Live smoke test

Live verification is opt-in and excluded from the normal suite. It is bounded to
one city, one Overpass discovery request, the configured candidate limit, and
zero outreach actions.

## 19. Success Metrics After Initial Use

After the first 100–150 manually reviewed prospects, evaluate:

- Percentage of OSM restaurants with usable official websites.
- Percentage with valid public business emails.
- Qualification rate.
- Draft-eligibility rate.
- Evidence corrections made during manual review.
- Ollama rejection/fallback rate.
- Response and meeting rates recorded manually.
- Most common objections and inaccurate scoring heuristics.

These results determine what should be automated or adjusted next. They do not
justify automatic sending in version 1.

## 20. Implementation Sequencing

Implementation will be divided into small sequential tasks across:

1. Project foundation and database.
2. OSM discovery and deduplication.
3. Safe official-site crawling.
4. Evidence extraction and deterministic scoring.
5. Pipeline recovery and CSV exports.
6. Ollama drafting and hallucination safeguards.
7. Local review interface.
8. Integration, browser, security, and release verification.

Each task must:

- Have one independently reviewable deliverable.
- Use test-driven development.
- Name exact files and interfaces.
- Preserve all prior passing tests.
- Include fresh verification evidence before completion.
- Avoid implementing later-task features early.
