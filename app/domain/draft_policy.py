from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DraftCandidate:
    business_id: str
    normalized_name: str
    score: int
    evidence_completeness: int
    qualified: bool
    permanently_closed: bool
    validated_business_email: bool
    has_verified_fact: bool


def select_draft_candidates(
    leads: Iterable[DraftCandidate], *, limit: int = 10
) -> tuple[DraftCandidate, ...]:
    eligible = (
        lead
        for lead in leads
        if lead.qualified
        and not lead.permanently_closed
        and lead.validated_business_email
        and lead.has_verified_fact
    )
    return tuple(
        sorted(
            eligible,
            key=lambda lead: (
                -lead.score,
                -lead.evidence_completeness,
                lead.normalized_name.casefold(),
                lead.business_id,
            ),
        )[:limit]
    )
