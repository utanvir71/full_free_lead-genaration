from datetime import UTC, datetime

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.crawler.link_ranker import rank_relevant_links


def test_ranker_prioritizes_relevant_unique_internal_links() -> None:
    homepage = FetchedPage(
        url="https://restaurant.example.com/",
        html="""
        <a href="/menu#dinner">Menu</a><a href="/menu#lunch">Menu</a>
        <a href="/private-dining">Private Dining</a><a href="/contact">Contact</a>
        <a href="https://booking.example/reserve">Reserve</a>
        """,
        http_status=200,
        fetched_at=datetime(2026, 7, 25, tzinfo=UTC),
    )

    links = rank_relevant_links(homepage)

    assert [link.url for link in links] == [
        "https://restaurant.example.com/private-dining",
        "https://restaurant.example.com/contact",
        "https://restaurant.example.com/menu",
    ]
