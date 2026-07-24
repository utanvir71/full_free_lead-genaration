from datetime import UTC, datetime

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.crawler.site_crawler import SiteCrawler


class FakeFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch(self, url: str, budget):  # type: ignore[no-untyped-def]
        self.urls.append(url)
        return FetchedPage(
            url=url,
            html="".join(f'<a href="/menu/{index}">Menu</a>' for index in range(10)),
            http_status=200,
            fetched_at=datetime(2026, 7, 25, tzinfo=UTC),
        )


def test_site_crawler_never_fetches_more_than_homepage_plus_five_pages() -> None:
    fetcher = FakeFetcher()
    result = SiteCrawler(fetcher).crawl("https://restaurant.example.com/")

    assert len(fetcher.urls) == 6
    assert len(result.pages) == 6
    assert len(result.manifest.selected) == 5
    assert result.complete is True
