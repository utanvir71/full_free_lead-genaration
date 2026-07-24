# Testing

Normal tests are offline: they use fixtures, fakes, mock transports, and
temporary SQLite databases. They must not contact Overpass, websites, DNS, or
Ollama.

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest tests/e2e -q
```

The Playwright suite launches the local application on `127.0.0.1`, starts a
fixture run, refreshes persisted progress, reviews evidence, changes a manual
status, inspects a local draft, and downloads both CSV projections. If Chromium
is not present, install it manually for the virtual environment:

```bash
.venv/bin/playwright install chromium
```

Fixture inputs include high-score, low-ticket, closed, robots-denied,
partial-crawl, invalid-email, no-MX, DNS-timeout, duplicate, and hallucinated
model cases. The focused tests for their adapters and policies remain the
primary behavioral checks.
