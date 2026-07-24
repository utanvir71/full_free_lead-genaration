from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from app.application.fact_packets import FactPacket
from app.domain.enums import DraftMethod, ValidationState
from app.domain.models import Draft


def build_fallback_draft(packet: FactPacket) -> Draft:
    fact = packet.facts[0] if packet.facts else None
    fact_text = fact.excerpt if fact is not None else "your restaurant's operations"
    evidence_ids = (fact.fact_id,) if fact is not None else ()
    return Draft(
        draft_id=str(uuid5(NAMESPACE_URL, _draft_identity(packet))),
        run_id="unpersisted",
        business_id=packet.business_id,
        subject=f"A question for {packet.business_id}",
        body=(
            f"I noticed {fact_text} An AI receptionist can answer routine calls "
            "and capture reservation requests. Would you be open to a short "
            "conversation?"
        ),
        method=DraftMethod.FALLBACK,
        evidence_ids=evidence_ids,
        validation_state=ValidationState.VALID,
        version="draft-v1",
        created_at=datetime.now(UTC),
    )


def _draft_identity(packet: FactPacket) -> str:
    return f"fallback:{packet.business_id}:{packet.assessment_id}"
