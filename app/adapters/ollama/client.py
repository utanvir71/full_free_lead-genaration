from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

import httpx


class OllamaReadiness(StrEnum):
    READY = "ready"
    SERVICE_UNAVAILABLE = "service_unavailable"
    MODEL_UNAVAILABLE = "model_unavailable"


@dataclass(frozen=True, slots=True)
class OllamaResult:
    kind: str
    content: str | None = None


class OllamaClient:
    def __init__(
        self,
        *,
        endpoint: str,
        model: str = "gemma4:e2b-it-qat",
        timeout_seconds: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def readiness(self) -> OllamaReadiness:
        try:
            with self._client() as client:
                response = client.get("/api/tags")
                response.raise_for_status()
        except (httpx.HTTPError, ValueError):
            return OllamaReadiness.SERVICE_UNAVAILABLE
        try:
            models = response.json().get("models", [])
        except ValueError:
            return OllamaReadiness.SERVICE_UNAVAILABLE
        return (
            OllamaReadiness.READY
            if any(model.get("name") == self._model for model in models)
            else OllamaReadiness.MODEL_UNAVAILABLE
        )

    def generate(
        self, packet: Mapping[str, object], schema: Mapping[str, object]
    ) -> OllamaResult:
        payload = {
            "model": self._model,
            "prompt": (
                "Generate a grounded restaurant outreach draft from this JSON packet. "
                "Return only a JSON object with exactly these fields: "
                '{"subject":"...","body":"...","evidence_ids":["..."]}. '
                "Use only evidence_ids present in the packet. Do not invent facts, "
                "names, contact details, or links.\n\nPacket:\n"
                f"{json.dumps(packet, separators=(',', ':'))}"
            ),
            "format": schema,
            "stream": False,
            "options": {"num_ctx": 8192, "temperature": 0.4, "num_predict": 220},
        }
        try:
            with self._client() as client:
                response = client.post("/api/generate", json=payload)
                response.raise_for_status()
                content = response.json().get("response")
        except (httpx.HTTPError, ValueError):
            return OllamaResult(kind="unavailable")
        if isinstance(content, str):
            return OllamaResult(kind="generated", content=content)
        return OllamaResult(kind="malformed")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._endpoint,
            timeout=self._timeout_seconds,
            transport=self._transport,
        )
