from datetime import UTC, datetime

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.extraction.decision_makers import DecisionMakerExtractor


def test_decision_maker_extractor_requires_nearby_supported_name_and_role() -> None:
    page = FetchedPage(
        url="https://rosa.example/about",
        html="""
        <main>
          <p>Rosa Martinez, Founder and Owner</p>
          <p>Marcus Lee — Events Manager</p>
          <p>Our staff: Alice, Ben, Carmen</p>
        </main>
        """,
        http_status=200,
        fetched_at=datetime(2026, 7, 25, tzinfo=UTC),
    )

    people = DecisionMakerExtractor().extract((page,))

    assert {(person.name, person.role) for person in people} == {
        ("Rosa Martinez", "Founder and Owner"),
        ("Marcus Lee", "Events Manager"),
    }
    assert all(person.evidence_ids for person in people)
