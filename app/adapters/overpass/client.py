from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

import httpx

from app.adapters.overpass.errors import OverpassResponseError, OverpassRetryExhausted
from app.adapters.overpass.parser import Candidate, parse_elements
from app.adapters.overpass.query import build_restaurant_query
from app.config import Settings

MAX_ATTEMPTS: Final = 3
CACHE_DURATION: Final = timedelta(hours=24)
RETRYABLE_STATUSES: Final = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class DiscoveryRequest:
    run_id: str
    city: str
    state: str
    limit: int


@dataclass(frozen=True, slots=True)
class _CachedDiscovery:
    expires_at: datetime
    candidates: tuple[Candidate, ...]


class OverpassClient:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        random_delay: Callable[[], float] = random.random,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client(
            timeout=httpx.Timeout(
                connect=settings.http_connect_timeout_seconds,
                read=settings.http_read_timeout_seconds,
                write=settings.http_read_timeout_seconds,
                pool=settings.http_connect_timeout_seconds,
            )
        )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleep = sleep
        self._random_delay = random_delay
        self._cache: dict[tuple[str, str], _CachedDiscovery] = {}
        self._queried_run_ids: set[str] = set()

    def discover(self, request: DiscoveryRequest) -> list[Candidate]:
        if request.run_id in self._queried_run_ids:
            raise ValueError("Overpass discovery may run only once per run")
        self._queried_run_ids.add(request.run_id)

        cache_key = (request.city.strip().casefold(), request.state.upper())
        cached = self._cache.get(cache_key)
        if cached is not None and cached.expires_at > self._clock():
            return list(cached.candidates[: request.limit])

        query = build_restaurant_query(request.city, request.state, limit=100)
        candidates = self._request_candidates(query)
        cached_candidates = tuple(candidates)
        self._cache[cache_key] = _CachedDiscovery(
            expires_at=self._clock() + CACHE_DURATION,
            candidates=cached_candidates,
        )
        return list(cached_candidates[: request.limit])

    def _request_candidates(self, query: str) -> list[Candidate]:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._http_client.post(
                    str(self._settings.overpass_url),
                    content=query,
                    headers={"User-Agent": self._settings.user_agent},
                )
            except httpx.TimeoutException as error:
                if attempt == MAX_ATTEMPTS:
                    raise OverpassRetryExhausted("Overpass timed out") from error
                self._sleep(self._retry_delay(None, attempt))
                continue
            except httpx.HTTPError as error:
                raise OverpassResponseError("Overpass request failed") from error

            if response.status_code in RETRYABLE_STATUSES:
                if attempt == MAX_ATTEMPTS:
                    raise OverpassRetryExhausted(
                        f"Overpass returned retryable status {response.status_code}"
                    )
                self._sleep(self._retry_delay(response, attempt))
                continue
            if response.is_error:
                raise OverpassResponseError(
                    f"Overpass returned HTTP status {response.status_code}"
                )
            return self._parse_response(response)

        raise AssertionError("Overpass retry loop unexpectedly completed")

    def _parse_response(self, response: httpx.Response) -> list[Candidate]:
        try:
            payload = response.json()
        except ValueError as error:
            raise OverpassResponseError("Overpass returned invalid JSON") from error
        if not isinstance(payload, dict) or "elements" not in payload:
            raise OverpassResponseError("Overpass returned an error payload")
        return parse_elements(payload)

    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass
        return float(attempt) + self._random_delay()
