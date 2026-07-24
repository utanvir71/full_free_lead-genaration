from datetime import UTC, datetime

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.extraction.contacts import ContactExtractor
from app.domain.enums import ValidationState

CAPTURED_AT = datetime(2026, 7, 25, 12, 5, tzinfo=UTC)


def test_contact_extractor_keeps_visible_business_contacts_with_evidence() -> None:
    page = FetchedPage(
        url="https://rosa.example/contact",
        html="""
        <main>
          <p>Email events@rosa.example or info [at] rosa [dot] example.</p>
          <p>Call (512) 555-0100 for reservations.</p>
          <form action="/contact"><label>Message</label></form>
        </main>
        """,
        http_status=200,
        fetched_at=CAPTURED_AT,
    )

    contacts = ContactExtractor().extract((page,))

    assert {(contact.kind, contact.value) for contact in contacts} == {
        ("email", "events@rosa.example"),
        ("email", "info@rosa.example"),
        ("phone", "(512) 555-0100"),
        ("form", "https://rosa.example/contact"),
    }
    assert all(contact.evidence_ids for contact in contacts)
    assert all(
        contact.validation_state is ValidationState.UNKNOWN for contact in contacts
    )


def test_contact_extractor_excludes_named_and_personal_mailboxes() -> None:
    page = FetchedPage(
        url="https://rosa.example/team",
        html="<main>jane.doe@rosa.example jane@gmail.com info@rosa.example</main>",
        http_status=200,
        fetched_at=CAPTURED_AT,
    )

    contacts = ContactExtractor().extract((page,))

    assert [(contact.kind, contact.value) for contact in contacts] == [
        ("email", "info@rosa.example")
    ]
