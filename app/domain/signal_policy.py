from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import SignalState

SCORING_V1_SIGNAL_POLICY = "scoring-v1"


@dataclass(frozen=True, slots=True)
class SignalInput:
    state: SignalState
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SignalInputs:
    call_required: SignalInput
    no_online_booking: SignalInput
    private_events: SignalInput
    catering: SignalInput
    multiple_locations: SignalInput
    phone_prominent: SignalInput
    complex_hours: SignalInput
    large_faq_or_menu: SignalInput
    high_ticket: SignalInput
    no_contact_route: SignalInput
    permanently_closed: SignalInput
    low_ticket: SignalInput
