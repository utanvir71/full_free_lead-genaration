from datetime import UTC, datetime

from app.application.fact_packets import FactPacketService
from app.domain.enums import FactState, ValidationState
from app.domain.models import Fact


def test_fact_packets_include_only_verified_facts_and_evidence_ids() -> None:
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

    packet = FactPacketService(lambda _business_id, _assessment_id: (fact,)).build(
        "business-1", "assessment-1"
    )

    assert packet.business_id == "business-1"
    assert packet.evidence_ids == ("fact-1",)
    assert packet.facts == (fact,)
