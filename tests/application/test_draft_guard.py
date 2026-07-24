from app.application.draft_guard import validate_generated_draft
from app.application.fact_packets import FactPacket


def test_draft_guard_rejects_unknown_evidence_ids() -> None:
    packet = FactPacket("business-1", "assessment-1", (), ("fact-1",))

    validation = validate_generated_draft(
        '{"subject":"Hello","body":"Hi","evidence_ids":["invented"]}', packet
    )

    assert validation.approved is False
    assert validation.reason == "unknown_evidence"
