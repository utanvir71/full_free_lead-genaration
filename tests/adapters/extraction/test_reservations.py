from datetime import UTC, datetime

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.extraction.reservations import ReservationExtractor
from app.domain.enums import FactState

CAPTURED_AT = datetime(2026, 7, 25, 12, 5, tzinfo=UTC)


def test_reservation_extractor_records_call_provider_and_form_evidence() -> None:
    page = FetchedPage(
        url="https://rosa.example/reservations",
        html="""
        <main>
          <p>For parties of six or more, please call us to reserve.</p>
          <a href="https://www.opentable.com/r/rosas-kitchen">Book a table</a>
          <form action="/reserve"><input name="date"></form>
        </main>
        """,
        http_status=200,
        fetched_at=CAPTURED_AT,
    )

    facts = ReservationExtractor().extract((page,))

    assert {(fact.fact_type, fact.value) for fact in facts} == {
        ("reservation_method", "call"),
        ("reservation_method", "online"),
        ("reservation_provider", "opentable"),
        ("reservation_form", "https://rosa.example/reserve"),
        ("call_to_reserve", "please call us to reserve"),
    }
    assert all(fact.state is FactState.PRESENT for fact in facts)
    assert {fact.source for fact in facts} == {"https://rosa.example/reservations"}
    assert all(fact.excerpt for fact in facts)


def test_reservation_extractor_represents_unobserved_methods_as_unknown() -> None:
    page = FetchedPage(
        url="https://rosa.example/about",
        html="<main>Welcome to Rosa's Kitchen.</main>",
        http_status=200,
        fetched_at=CAPTURED_AT,
    )

    facts = ReservationExtractor().extract((page,))

    assert {fact.fact_type for fact in facts} == {
        "reservation_method",
        "reservation_provider",
        "reservation_form",
        "call_to_reserve",
    }
    assert all(fact.state is FactState.UNKNOWN for fact in facts)
    assert all(fact.value is None for fact in facts)
