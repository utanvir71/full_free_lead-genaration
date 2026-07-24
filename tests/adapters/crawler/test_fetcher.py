from datetime import UTC, datetime

import httpx
import pytest

from app.adapters.crawler.errors import FetchError
from app.adapters.crawler.fetcher import PageFetcher, RequestBudget
from app.adapters.crawler.robots import RobotsPolicy
from app.adapters.crawler.url_policy import UrlPolicy


def resolver(_: str) -> tuple[str, ...]:
    return ("93.184.216.34",)


def test_fetcher_returns_bounded_html_after_url_and_robots_checks() -> None:
    requests: list[str] = []
    policy = UrlPolicy(resolve=resolver)
    robots = RobotsPolicy(user_agent="TestBot", get=lambda _: httpx.Response(404))
    fetcher = PageFetcher(
        policy,
        robots,
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: (
                    requests.append(str(request.url))
                    or httpx.Response(
                        200, text="<h1>Menu</h1>", headers={"content-type": "text/html"}
                    )
                )
            )
        ),
        sleep=lambda _: None,
        clock=lambda: datetime(2026, 7, 25, tzinfo=UTC),
    )

    page = fetcher.fetch(
        "https://restaurant.example.com/menu",
        RequestBudget(official_url="https://restaurant.example.com/", max_bytes=100),
    )

    assert page.url == "https://restaurant.example.com/menu"
    assert page.html == "<h1>Menu</h1>"
    assert requests == ["https://restaurant.example.com/menu"]


def test_fetcher_does_not_retry_denied_or_non_html_content() -> None:
    policy = UrlPolicy(resolve=resolver)
    denied = RobotsPolicy(
        user_agent="TestBot",
        get=lambda _: httpx.Response(200, text="User-agent: *\nDisallow: /\n"),
    )
    fetcher = PageFetcher(
        policy,
        denied,
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: pytest.fail("must not fetch"))
        ),
        sleep=lambda _: None,
    )

    with pytest.raises(FetchError, match="robots_denied"):
        fetcher.fetch(
            "https://restaurant.example.com/menu",
            RequestBudget("https://restaurant.example.com/", 100),
        )
