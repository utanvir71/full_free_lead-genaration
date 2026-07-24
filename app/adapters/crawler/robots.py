from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class RobotsDecision:
    allowed: bool
    robots_url: str
    error: str | None


class RobotsPolicy:
    def __init__(
        self, *, user_agent: str, get: Callable[[str], httpx.Response]
    ) -> None:
        self._user_agent = user_agent
        self._get = get
        self._cache: dict[
            str, tuple[RobotsDecision, robotparser.RobotFileParser | None]
        ] = {}

    def allowed(self, url: str) -> RobotsDecision:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        cached = self._cache.get(robots_url)
        if cached is None:
            cached = self._load(robots_url)
            self._cache[robots_url] = cached
        decision, parser = cached
        if parser is None:
            return decision
        return RobotsDecision(
            allowed=parser.can_fetch(self._user_agent, url),
            robots_url=robots_url,
            error=None,
        )

    def _load(
        self, robots_url: str
    ) -> tuple[RobotsDecision, robotparser.RobotFileParser | None]:
        try:
            response = self._get(robots_url)
        except httpx.TimeoutException:
            return RobotsDecision(False, robots_url, "timeout"), None
        except httpx.HTTPError:
            return RobotsDecision(False, robots_url, "request_error"), None
        if response.status_code == 404:
            return RobotsDecision(True, robots_url, "missing"), None
        if response.is_error:
            return RobotsDecision(
                False, robots_url, f"http_{response.status_code}"
            ), None
        parser = robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return RobotsDecision(True, robots_url, None), parser
