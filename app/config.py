from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bind_host: Literal["127.0.0.1"] = "127.0.0.1"
    database_path: Path = Path("data/leadgen.sqlite3")
    overpass_url: HttpUrl = HttpUrl("https://overpass-api.de/api/interpreter")
    user_agent: str = "ZeroMoneyRestaurantLeadGenerator/0.1 (local operator)"
    candidate_limit: int = Field(default=30, ge=1, le=100)
    http_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    http_read_timeout_seconds: float = Field(default=15.0, gt=0)
    crawl_delay_seconds: float = Field(default=1.0, ge=1.0)
    max_response_bytes: int = Field(default=2_000_000, gt=0)
    ollama_endpoint: HttpUrl = HttpUrl("http://127.0.0.1:11434")
    ollama_model: str = "gemma4:e2b-it-qat"
    ollama_context: int = Field(default=8192, gt=0)
    ollama_temperature: float = Field(default=0.4, ge=0, le=1)
    ollama_max_output_tokens: int = Field(default=220, gt=0)
    ollama_timeout_seconds: float = Field(default=45.0, gt=0)
    export_directory: Path = Path("exports")

    _ENV_FIELDS: ClassVar[dict[str, str]] = {
        f"LEADGEN_{field_name.upper()}": field_name
        for field_name in (
            "bind_host",
            "database_path",
            "overpass_url",
            "user_agent",
            "candidate_limit",
            "http_connect_timeout_seconds",
            "http_read_timeout_seconds",
            "crawl_delay_seconds",
            "max_response_bytes",
            "ollama_endpoint",
            "ollama_model",
            "ollama_context",
            "ollama_temperature",
            "ollama_max_output_tokens",
            "ollama_timeout_seconds",
            "export_directory",
        )
    }

    @classmethod
    def load(cls, environ: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if environ is None else environ
        unsupported = sorted(
            name
            for name in source
            if name.startswith("LEADGEN_") and name not in cls._ENV_FIELDS
        )
        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(f"Unsupported LEADGEN setting: {names}")
        values: dict[str, Any] = {
            field_name: source[environment_name]
            for environment_name, field_name in cls._ENV_FIELDS.items()
            if environment_name in source
        }
        return cls.model_validate(values)
