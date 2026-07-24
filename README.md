# Zero-Money Restaurant Lead Generator

A local-only application for evidence-backed restaurant research and manual
outreach-draft review. It does not send email and does not use paid lead
providers.

## Development setup

Python 3.12 is required.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Run the quality checks:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app
```

Start the local server:

```bash
.venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

The service is intentionally bound only to `127.0.0.1`.

Startup applies the local SQLite migration automatically. Open
`http://127.0.0.1:8000/runs` to create and revisit runs, review evidence and
manual workflow status, inspect local drafts, and download the registered
qualified or rejected CSV projections. A draft is never a sent message.

## Configuration

All settings are optional and use the safe defaults documented in
[`.env.example`](.env.example). Configuration names use the `LEADGEN_` prefix.
The application accepts no API key or other secret because version 1 uses only
public OpenStreetMap infrastructure and optional local Ollama.

Ollama is optional. If you choose to use it, install and manage it yourself;
the application neither installs Ollama nor downloads models. The default local
model is `gemma4:e2b-it-qat`; missing or rejected model output uses a grounded
deterministic fallback.

See [architecture](docs/architecture.md), [scoring policy](docs/scoring-policy.md),
[testing](docs/testing.md), and the [release checklist](docs/release-checklist.md)
for the operating and recovery procedures.
