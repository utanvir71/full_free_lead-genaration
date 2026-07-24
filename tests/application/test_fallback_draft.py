from datetime import UTC, datetime

from app.application.fact_packets import FactPacket
from app.application.fallback_draft import build_fallback_draft
from app.domain.enums import FactState, ValidationState
from app.domain.models import Fact


def test_fallback_draft_uses_one_verified_fact_and_permission_cta() -> None:
    fact = Fact(
        fact_id="fact-1",
        fact_type="private_events",
        state=FactState.PRESENT,
        value=True,
        source="https://example.test/events",
        excerpt="Private events are available.",
        captured_at=datetime(2026, 7, 25, tzinfo=UTC),
        extractor_version="fixture-v1",
        validation_state=ValidationState.VALID,
    )

    packet = FactPacket("business-1", "assessment-1", (fact,), ("fact-1",))
    draft = build_fallback_draft(packet)

    assert "Private events are available." in draft.body
    assert "Would you be open" in draft.body
    assert draft.evidence_ids == ("fact-1",)
