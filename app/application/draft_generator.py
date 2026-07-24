from __future__ import annotations

from typing import Protocol

from app.application.draft_guard import DraftValidation, validate_generated_draft
from app.application.fact_packets import FactPacket


class GeneratedResult(Protocol):
    content: str | None


class DraftModel(Protocol):
    def generate(self, packet: object, schema: object) -> GeneratedResult: ...


class DraftGenerator:
    def __init__(self, *, client: DraftModel) -> None:
        self._client = client

    def generate(self, packet: FactPacket) -> DraftValidation:
        schema = {
            "type": "object",
            "required": ["subject", "body", "evidence_ids"],
        }
        for _ in range(2):
            result = self._client.generate(packet, schema)
            validation = validate_generated_draft(result.content, packet)
            if validation.approved:
                return validation
        return validation
