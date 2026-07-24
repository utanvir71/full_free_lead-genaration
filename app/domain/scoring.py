from __future__ import annotations

from hashlib import sha256

from app.domain.enums import SignalState
from app.domain.models import Assessment, ScoreComponent
from app.domain.signal_policy import SCORING_V1_SIGNAL_POLICY, SignalInputs

_RULES = (
    ("call_required", "Reservations explicitly require calling", 3),
    ("no_online_booking", "No online booking path found", 2),
    ("private_events", "Private dining or events offered", 2),
    ("catering", "Catering offered", 2),
    ("multiple_locations", "Two or more locations", 2),
    ("phone_prominent", "Phone heavily promoted", 1),
    ("complex_hours", "Complicated hours", 1),
    ("large_faq_or_menu", "Large FAQ or menu", 1),
    ("high_ticket", "High-ticket menu", 1),
    ("no_contact_route", "No public contact route", -3),
    ("permanently_closed", "Permanently closed", -3),
    ("low_ticket", "Fast-food or low-ticket positioning", -2),
)


def score_v1(
    inputs: SignalInputs,
    *,
    run_id: str = "unbound-run",
    business_id: str = "unbound-business",
) -> Assessment:
    components: list[ScoreComponent] = []
    for attribute, explanation, delta in _RULES:
        signal = getattr(inputs, attribute)
        applied_delta = delta if signal.state is SignalState.AWARDED else 0
        components.append(
            ScoreComponent(
                signal=attribute,
                state=signal.state,
                delta=applied_delta,
                explanation=explanation,
                evidence_ids=signal.evidence_ids,
            )
        )
    total = sum(component.delta for component in components)
    identity = "\n".join((run_id, business_id, str(total), SCORING_V1_SIGNAL_POLICY))
    return Assessment(
        assessment_id=f"assessment:{sha256(identity.encode()).hexdigest()}",
        run_id=run_id,
        business_id=business_id,
        scoring_version=SCORING_V1_SIGNAL_POLICY,
        components=tuple(components),
        total=total,
        qualified=total >= 6,
    )
