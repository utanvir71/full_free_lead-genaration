from dataclasses import replace

from app.domain.enums import SignalState
from app.domain.scoring import score_v1
from app.domain.signal_policy import SignalInput, SignalInputs


def _inputs(state: SignalState = SignalState.DENIED) -> SignalInputs:
    signal = SignalInput(state, ("website:1",))
    return SignalInputs(*([signal] * 12))


def test_score_v1_uses_exact_ordered_deltas_and_evidence() -> None:
    assessment = score_v1(_inputs(SignalState.AWARDED))

    assert [component.delta for component in assessment.components] == [
        3,
        2,
        2,
        2,
        2,
        1,
        1,
        1,
        1,
        -3,
        -3,
        -2,
    ]
    assert assessment.total == 7
    assert all(
        component.evidence_ids == ("website:1",) for component in assessment.components
    )


def test_score_v1_unknown_is_zero_and_boundary_six_qualifies() -> None:
    inputs = replace(
        _inputs(SignalState.UNKNOWN),
        call_required=SignalInput(SignalState.AWARDED, ("website:call",)),
        no_online_booking=SignalInput(SignalState.AWARDED, ("website:booking",)),
        phone_prominent=SignalInput(SignalState.AWARDED, ("website:phone",)),
    )

    assessment = score_v1(inputs)

    assert assessment.total == 6
    assert assessment.qualified is True
    assert [component.delta for component in assessment.components] == [
        3,
        2,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
