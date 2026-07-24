from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.domain.enums import ValidationState
from app.domain.models import Fact


@dataclass(frozen=True, slots=True)
class FactPacket:
    business_id: str
    assessment_id: str
    facts: tuple[Fact, ...]
    evidence_ids: tuple[str, ...]


class FactPacketService:
    def __init__(
        self,
        facts_for_assessment: Callable[[str, str], Iterable[Fact]],
    ) -> None:
        self._facts_for_assessment = facts_for_assessment

    def build(self, business_id: str, assessment_id: str) -> FactPacket:
        facts = tuple(
            fact
            for fact in self._facts_for_assessment(business_id, assessment_id)
            if fact.validation_state is ValidationState.VALID
        )
        return FactPacket(
            business_id=business_id,
            assessment_id=assessment_id,
            facts=facts,
            evidence_ids=tuple(fact.fact_id for fact in facts),
        )
