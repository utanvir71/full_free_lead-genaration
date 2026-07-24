from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.adapters.crawler.errors import FetchError
from app.adapters.crawler.robots import RobotsPolicy
from app.adapters.crawler.url_policy import UrlPolicy


@dataclass(frozen=True, slots=True)
class RequestBudget:
    official_url: str
    max_bytes: int
    crawl_delay_seconds: float = 1.0
    max_redirects: int = 3


@dataclass(frozen=True, slots=True)
class FetchedPage:
    url: str
    html: str
    http_status: int
    fetched_at: datetime


class PageFetcher:
    def __init__(
        self,
        policy: UrlPolicy,
        robots: RobotsPolicy,
        *,
        http_client: httpx.Client,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._policy = policy
        self._robots = robots
        self._http_client = http_client
        self._sleep = sleep
        self._clock = clock or (lambda: datetime.now(UTC))
        self._last_request_at: dict[str, datetime] = {}

    def fetch(self, url: str, budget: RequestBudget) -> FetchedPage:
        try:
            validated = self._policy.validate_initial(url)
        except ValueError as error:
            raise FetchError("unsafe_url") from error
        if not self._policy.same_official_domain(budget.official_url, validated.url):
            raise FetchError("off_domain")
        robots = self._robots.allowed(validated.url)
        if not robots.allowed:
            raise FetchError("robots_denied")
        self._pace(validated.hostname, budget.crawl_delay_seconds)
        for attempt in range(2):
            try:
                response = self._http_client.get(validated.url, follow_redirects=False)
            except httpx.TimeoutException as error:
                if attempt == 1:
                    raise FetchError("timeout") from error
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                continue
            if response.is_error:
                raise FetchError(f"http_{response.status_code}")
            if (
                not response.headers.get("content-type", "")
                .lower()
                .startswith("text/html")
            ):
                raise FetchError("invalid_content")
            if len(response.content) > budget.max_bytes:
                raise FetchError("response_too_large")
            return FetchedPage(
                url=validated.url,
                html=response.text,
                http_status=response.status_code,
                fetched_at=self._clock(),
            )
        raise FetchError("retry_exhausted")

    def _pace(self, hostname: str, delay: float) -> None:
        now = self._clock()
        previous = self._last_request_at.get(hostname)
        if previous is not None:
            remaining = delay - (now - previous).total_seconds()
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at[hostname] = self._clock()
