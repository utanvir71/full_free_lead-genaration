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

## Configuration

All settings are optional and use the safe defaults documented in
[`.env.example`](.env.example). Configuration names use the `LEADGEN_` prefix.
The application accepts no API key or other secret because version 1 uses only
public OpenStreetMap infrastructure and optional local Ollama.
