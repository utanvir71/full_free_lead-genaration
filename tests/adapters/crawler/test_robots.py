import httpx

from app.adapters.crawler.robots import RobotsDecision, RobotsPolicy


def test_robots_policy_caches_allow_and_deny_decisions_for_active_run() -> None:
    requests: list[str] = []

    def get(url: str) -> httpx.Response:
        requests.append(url)
        return httpx.Response(200, text="User-agent: TestBot\nDisallow: /private\n")

    policy = RobotsPolicy(user_agent="TestBot", get=get)

    allowed = policy.allowed("https://restaurant.example.com/menu")
    denied = policy.allowed("https://restaurant.example.com/private/events")

    assert allowed == RobotsDecision(
        True, "https://restaurant.example.com/robots.txt", None
    )
    assert denied.allowed is False
    assert requests == ["https://restaurant.example.com/robots.txt"]


def test_missing_and_timeout_robots_outcomes_remain_visible_and_conservative() -> None:
    missing = RobotsPolicy(
        user_agent="TestBot", get=lambda _: httpx.Response(404)
    ).allowed("https://restaurant.example.com/menu")
    timeout = RobotsPolicy(
        user_agent="TestBot",
        get=lambda _: (_ for _ in ()).throw(httpx.TimeoutException("slow")),
    ).allowed("https://restaurant.example.com/menu")

    assert missing.allowed is True
    assert missing.error == "missing"
    assert timeout.allowed is False
    assert timeout.error == "timeout"
