from __future__ import annotations

import json

from app.application.fact_packets import FactPacket


def build_draft_prompt(packet: FactPacket) -> str:
    return json.dumps(
        {
            "business_id": packet.business_id,
            "assessment_id": packet.assessment_id,
            "facts": [fact.model_dump(mode="json") for fact in packet.facts],
            "evidence_ids": packet.evidence_ids,
        },
        sort_keys=True,
    )
