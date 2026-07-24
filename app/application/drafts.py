from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from app.application.draft_generator import DraftGenerator
from app.application.draft_guard import DraftValidation
from app.application.fact_packets import FactPacket
from app.application.fallback_draft import build_fallback_draft
from app.domain.enums import DraftMethod, ValidationState
from app.domain.models import Draft


class StoredDrafts(Protocol):
    def add(self, draft: Draft) -> None: ...


@dataclass(frozen=True, slots=True)
class DraftService:
    packets_for_run: Callable[[str], Iterable[FactPacket]]
    generator: DraftGenerator
    repository: StoredDrafts

    def generate_for_run(self, run_id: str) -> int:
        saved = 0
        for packet in self.packets_for_run(run_id):
            if saved == 10:
                break
            validation = self.generator.generate(packet)
            draft = _from_validation(packet, run_id, validation)
            self.repository.add(draft)
            saved += 1
        return saved


def _from_validation(
    packet: FactPacket, run_id: str, validation: DraftValidation
) -> Draft:
    if not validation.approved:
        return build_fallback_draft(packet).model_copy(update={"run_id": run_id})
    assert validation.subject is not None
    assert validation.body is not None
    return Draft(
        draft_id=str(uuid5(NAMESPACE_URL, f"ollama:{run_id}:{packet.business_id}")),
        run_id=run_id,
        business_id=packet.business_id,
        subject=validation.subject,
        body=validation.body,
        method=DraftMethod.OLLAMA,
        evidence_ids=validation.evidence_ids,
        validation_state=ValidationState.VALID,
        version="draft-v1",
        created_at=build_fallback_draft(packet).created_at,
    )
