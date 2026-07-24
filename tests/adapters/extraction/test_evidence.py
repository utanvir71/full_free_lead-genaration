from datetime import UTC, datetime

from app.adapters.extraction.evidence import EvidenceFactory
from app.adapters.extraction.page_text import extract_visible_text
from app.domain.enums import ValidationState

CAPTURED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def test_extract_visible_text_excludes_non_primary_and_hidden_content() -> None:
    page = extract_visible_text(
        """
        <html><head><style>.hidden { display: none; }</style>
        <script>ignore()</script></head>
        <body><nav>Home Menu Contact</nav><main><h1>Rosa's Kitchen</h1>
        <p>For reservations, call us at 555-0100.</p><p hidden>Hidden promotion</p>
        <p style="display: none">Invisible promotion</p></main>
        <footer>Privacy</footer></body></html>
        """
    )

    assert page.text == "Rosa's Kitchen For reservations, call us at 555-0100."
    assert "Home" not in page.text
    assert "ignore" not in page.text
    assert "Hidden" not in page.text


def test_evidence_factory_bounds_excerpt_around_matched_phrase() -> None:
    html = f"<main>{'before ' * 80}Call to reserve.{' after' * 80}</main>"
    page = extract_visible_text(html)

    evidence = EvidenceFactory(excerpt_length=80).from_match(
        source_url="https://rosa.example/reservations",
        page=page,
        matched_phrase="Call to reserve.",
        locator="main",
        captured_at=CAPTURED_AT,
    )

    assert evidence.source == "https://rosa.example/reservations"
    assert evidence.locator == "main"
    assert evidence.captured_at == CAPTURED_AT
    assert evidence.extractor_version == "website-evidence-v1"
    assert evidence.validation_state is ValidationState.NOT_APPLICABLE
    assert "Call to reserve." in evidence.excerpt
    assert len(evidence.excerpt) <= 80


def test_evidence_factory_uses_stable_identity_for_identical_html() -> None:
    factory = EvidenceFactory()

    first = factory.from_match(
        source_url="https://rosa.example/reservations",
        page=extract_visible_text("<main>Call to reserve.</main>"),
        matched_phrase="Call to reserve.",
        locator="main",
        captured_at=CAPTURED_AT,
    )
    second = factory.from_match(
        source_url="https://rosa.example/reservations",
        page=extract_visible_text("<main>Call to reserve.</main>"),
        matched_phrase="Call to reserve.",
        locator="main",
        captured_at=CAPTURED_AT,
    )

    assert first.evidence_id == second.evidence_id
