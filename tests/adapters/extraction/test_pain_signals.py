from app.adapters.extraction.pain_signals import PainSignalExtractor
from app.domain.enums import SignalState


def test_pain_signal_extractor_applies_versioned_thresholds_and_evidence() -> None:
    inputs = PainSignalExtractor().extract(
        {
            "complete_crawl": True,
            "call_to_reserve": True,
            "online_booking": False,
            "private_events": True,
            "catering": True,
            "location_count": 2,
            "phone_prominent": True,
            "complex_hours": True,
            "faq_pairs": 10,
            "menu_items": 40,
            "entree_prices": [28, 30, 31, 35, 40],
            "contact_route": True,
            "closed": False,
            "quick_service": False,
            "evidence_ids": {"call_required": ("website:call",)},
        }
    )

    assert inputs.call_required.state is SignalState.AWARDED
    assert inputs.no_online_booking.state is SignalState.AWARDED
    assert inputs.large_faq_or_menu.state is SignalState.AWARDED
    assert inputs.high_ticket.state is SignalState.AWARDED
    assert inputs.low_ticket.state is SignalState.DENIED
    assert inputs.call_required.evidence_ids == ("website:call",)


def test_incomplete_crawl_leaves_absence_signals_unknown() -> None:
    inputs = PainSignalExtractor().extract(
        {"complete_crawl": False, "online_booking": False, "contact_route": False}
    )

    assert inputs.no_online_booking.state is SignalState.UNKNOWN
    assert inputs.no_contact_route.state is SignalState.UNKNOWN
