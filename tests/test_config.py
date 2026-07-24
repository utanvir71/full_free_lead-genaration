from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


def test_load_uses_exact_safe_defaults() -> None:
    settings = Settings.load({})

    assert settings.bind_host == "127.0.0.1"
    assert settings.database_path == Path("data/leadgen.sqlite3")
    assert str(settings.overpass_url) == "https://overpass-api.de/api/interpreter"
    assert settings.candidate_limit == 30
    assert settings.crawl_delay_seconds == 1.0
    assert settings.ollama_model == "gemma4:e2b-it-qat"
    assert settings.ollama_context == 8192
    assert settings.ollama_temperature == 0.4
    assert settings.ollama_max_output_tokens == 220
    assert settings.ollama_timeout_seconds == 45.0
    assert settings.export_directory == Path("exports")


def test_load_uses_only_injected_values() -> None:
    settings = Settings.load(
        {
            "LEADGEN_CANDIDATE_LIMIT": "12",
            "LEADGEN_DATABASE_PATH": "tmp/test.sqlite3",
        }
    )

    assert settings.candidate_limit == 12
    assert settings.database_path == Path("tmp/test.sqlite3")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("LEADGEN_BIND_HOST", "0.0.0.0"),
        ("LEADGEN_OVERPASS_URL", "ftp://example.com"),
        ("LEADGEN_OLLAMA_ENDPOINT", "not-a-url"),
        ("LEADGEN_CANDIDATE_LIMIT", "0"),
        ("LEADGEN_CANDIDATE_LIMIT", "101"),
        ("LEADGEN_HTTP_CONNECT_TIMEOUT_SECONDS", "0"),
        ("LEADGEN_HTTP_READ_TIMEOUT_SECONDS", "-1"),
        ("LEADGEN_CRAWL_DELAY_SECONDS", "0.5"),
        ("LEADGEN_MAX_RESPONSE_BYTES", "0"),
        ("LEADGEN_OLLAMA_CONTEXT", "0"),
        ("LEADGEN_OLLAMA_TEMPERATURE", "1.1"),
        ("LEADGEN_OLLAMA_MAX_OUTPUT_TOKENS", "0"),
        ("LEADGEN_OLLAMA_TIMEOUT_SECONDS", "0"),
    ],
)
def test_load_rejects_unsafe_or_invalid_values(name: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Settings.load({name: value})


def test_load_rejects_secret_configuration() -> None:
    with pytest.raises(ValueError, match="Unsupported LEADGEN setting"):
        Settings.load({"LEADGEN_API_KEY": "not-used"})


def test_create_app_uses_injected_settings() -> None:
    settings = Settings.load({"LEADGEN_CANDIDATE_LIMIT": "7"})

    app = create_app(settings)

    assert app.state.settings is settings
