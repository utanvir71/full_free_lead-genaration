# Architecture

The application is a local FastAPI modular monolith. Uvicorn must bind to
`127.0.0.1`; the process owns one SQLite database, one durable job queue, and
one in-process worker.

```
web routes and adapters -> application services -> domain rules
```

SQLite is the source of truth. It stores canonical businesses, immutable run
snapshots, evidence, assessments, drafts, notes, statuses, errors, and export
records. Startup applies the numbered Alembic migration, enables foreign keys,
WAL mode, and a five-second busy timeout.

The web interface reads only persisted state. The run page polls persisted
progress; lead review renders evidence, contacts, score signals, crawl records,
typed limitations, and manual review history. It does not alter extracted facts
or score arithmetic.

OpenStreetMap Overpass is the sole discovery provider. Official-site crawling
is bounded, robots-aware, same-domain, and revalidates DNS and redirects.
Ollama is optional and local. Its output is accepted only after grounding
validation; otherwise a deterministic local draft is saved. No component sends
email or connects to Gmail or SMTP.

Security controls include localhost bind configuration, Host and Origin checks,
CSRF tokens, template autoescaping, a self-only CSP, local static assets, and
SSRF checks in the crawler.
