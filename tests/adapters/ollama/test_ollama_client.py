import json

import httpx

from app.adapters.ollama.client import OllamaClient, OllamaReadiness


def test_ollama_generation_uses_approved_local_defaults() -> None:
    request: httpx.Request | None = None

    def handler(candidate: httpx.Request) -> httpx.Response:
        nonlocal request
        request = candidate
        return httpx.Response(200, json={"response": '{"subject":"Hi","body":"Body"}'})

    client = OllamaClient(
        endpoint="http://127.0.0.1:11434",
        transport=httpx.MockTransport(handler),
    )

    result = client.generate({"facts": []}, {"type": "object"})

    assert result.kind == "generated"
    assert request is not None
    payload = json.loads(request.content)
    assert payload["model"] == "gemma4:e2b-it-qat"
    assert payload["options"] == {
        "num_ctx": 8192,
        "temperature": 0.4,
        "num_predict": 220,
    }
    assert "context" not in payload
    assert '"facts":[]' in payload["prompt"]
    assert '"subject"' in payload["prompt"]
    assert '"body"' in payload["prompt"]
    assert '"evidence_ids"' in payload["prompt"]


def test_ollama_readiness_reports_missing_service_without_raising() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("not running")

    client = OllamaClient(
        endpoint="http://127.0.0.1:11434",
        transport=httpx.MockTransport(handler),
    )

    assert client.readiness() is OllamaReadiness.SERVICE_UNAVAILABLE
