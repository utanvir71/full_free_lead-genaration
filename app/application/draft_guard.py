from __future__ import annotations

import json
from dataclasses import dataclass

from app.application.fact_packets import FactPacket


@dataclass(frozen=True, slots=True)
class DraftValidation:
    approved: bool
    reason: str | None
    subject: str | None = None
    body: str | None = None
    evidence_ids: tuple[str, ...] = ()


def validate_generated_draft(result: str | None, packet: FactPacket) -> DraftValidation:
    if result is None:
        return DraftValidation(False, "missing_output")
    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        return DraftValidation(False, "malformed_output")
    if not isinstance(payload, dict):
        return DraftValidation(False, "malformed_output")
    subject = payload.get("subject")
    body = payload.get("body")
    evidence_ids = payload.get("evidence_ids")
    if not isinstance(subject, str) or not isinstance(body, str):
        return DraftValidation(False, "malformed_output")
    if not isinstance(evidence_ids, list) or not all(
        isinstance(item, str) for item in evidence_ids
    ):
        return DraftValidation(False, "malformed_output")
    if not set(evidence_ids).issubset(packet.evidence_ids):
        return DraftValidation(False, "unknown_evidence")
    return DraftValidation(True, None, subject, body, tuple(evidence_ids))
