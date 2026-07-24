from dataclasses import replace

from app.application.qualification import QualificationService
from app.domain.enums import SignalState
from app.domain.signal_policy import SignalInput, SignalInputs


def test_qualification_service_rejects_score_five_without_hard_overrides() -> None:
    unknown = SignalInput(SignalState.UNKNOWN)
    inputs = SignalInputs(*([unknown] * 12))
    inputs = replace(
        inputs,
        call_required=SignalInput(SignalState.AWARDED),
        no_online_booking=SignalInput(SignalState.AWARDED),
        permanently_closed=SignalInput(SignalState.DENIED),
    )

    assessment = QualificationService().assess("run-1", "business-1", inputs)

    assert assessment.total == 5
    assert assessment.qualified is False
