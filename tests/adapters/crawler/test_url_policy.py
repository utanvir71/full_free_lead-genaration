import pytest

from app.adapters.crawler.url_policy import UnsafeUrlError, UrlPolicy


def public_resolver(hostname: str) -> tuple[str, ...]:
    addresses = {
        "restaurant.example.com": ("93.184.216.34",),
        "www.restaurant.example.com": ("93.184.216.34",),
    }
    return addresses[hostname]


def test_accepts_public_http_urls_and_same_registrable_domain_redirects() -> None:
    policy = UrlPolicy(resolve=public_resolver)

    initial = policy.validate_initial("https://restaurant.example.com/menu")
    redirected = policy.validate_redirect(
        "https://restaurant.example.com/menu",
        "https://www.restaurant.example.com/contact",
    )

    assert initial.hostname == "restaurant.example.com"
    assert redirected.hostname == "www.restaurant.example.com"
    assert policy.same_official_domain(initial.url, redirected.url) is True


@pytest.mark.parametrize(
    "url",
    [
        "ftp://restaurant.example.com/menu",
        "https://user:pass@restaurant.example.com/menu",
        "https://127.0.0.1/admin",
        "https://[::1]/admin",
    ],
)
def test_rejects_unsafe_initial_urls(url: str) -> None:
    resolver = (
        public_resolver if "restaurant.example" in url else lambda _: ("127.0.0.1",)
    )

    with pytest.raises(UnsafeUrlError):
        UrlPolicy(resolve=resolver).validate_initial(url)


def test_rejects_official_domain_redirects() -> None:
    def resolver(hostname: str) -> tuple[str, ...]:
        return {
            "restaurant.example.com": ("93.184.216.34",),
            "evil.example": ("8.8.8.8",),
        }[hostname]

    with pytest.raises(UnsafeUrlError):
        UrlPolicy(resolve=resolver).validate_redirect(
            "https://restaurant.example.com/",
            "https://evil.example/",
        )
