import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from app.adapters.overpass.client import DiscoveryRequest, OverpassClient
from app.adapters.overpass.errors import OverpassResponseError, OverpassRetryExhausted
from app.config import Settings

FIXTURE_PATH = Path(__file__).parents[2] / "fixtures" / "overpass" / "restaurants.json"


def build_client(handler: Callable[[httpx.Request], httpx.Response]) -> OverpassClient:
    transport = httpx.MockTransport(handler)
    return OverpassClient(
        Settings.load({}),
        http_client=httpx.Client(transport=transport),
        sleep=lambda _: None,
        random_delay=lambda: 0.0,
    )


def test_discover_uses_configured_user_agent_and_caches_city_state_response() -> None:
    requests: list[httpx.Request] = []
    fixture = json.loads(FIXTURE_PATH.read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=fixture)

    client = build_client(handler)
    request = DiscoveryRequest(run_id="run-1", city="Austin", state="TX", limit=3)

    first = client.discover(request)
    second = client.discover(
        DiscoveryRequest(run_id="run-2", city="Austin", state="TX", limit=3)
    )

    assert len(requests) == 1
    assert requests[0].headers["user-agent"] == Settings.load({}).user_agent
    assert requests[0].content.decode().count("amenity") == 3
    assert first == second
    assert len(first) == 3


def test_discover_retries_transient_failures_at_most_three_times() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    client = build_client(handler)

    with pytest.raises(OverpassRetryExhausted):
        client.discover(
            DiscoveryRequest(run_id="run-1", city="Austin", state="TX", limit=3)
        )

    assert attempts == 3


def test_discover_rejects_overpass_error_payloads_and_invalid_json() -> None:
    responses = iter(
        [
            httpx.Response(200, json={"remark": "runtime error: out of memory"}),
            httpx.Response(200, content=b"not-json"),
        ]
    )

    client = build_client(lambda _: next(responses))

    with pytest.raises(OverpassResponseError):
        client.discover(
            DiscoveryRequest(run_id="run-1", city="Austin", state="TX", limit=3)
        )
    with pytest.raises(OverpassResponseError):
        client.discover(
            DiscoveryRequest(run_id="run-2", city="Dallas", state="TX", limit=3)
        )
