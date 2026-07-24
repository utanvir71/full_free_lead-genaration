import pytest

from app.domain.enums import RunStatus
from app.domain.lifecycle import InvalidRunTransition, transition_run


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RunStatus.QUEUED, RunStatus.RUNNING),
        (RunStatus.QUEUED, RunStatus.CANCELLED),
        (RunStatus.RUNNING, RunStatus.COMPLETED),
        (RunStatus.RUNNING, RunStatus.COMPLETED_WITH_ERRORS),
        (RunStatus.RUNNING, RunStatus.FAILED),
        (RunStatus.RUNNING, RunStatus.CANCELLED),
        (RunStatus.RUNNING, RunStatus.INTERRUPTED),
        (RunStatus.INTERRUPTED, RunStatus.QUEUED),
        (RunStatus.INTERRUPTED, RunStatus.CANCELLED),
    ],
)
def test_transition_run_accepts_only_documented_edges(
    current: RunStatus,
    target: RunStatus,
) -> None:
    assert transition_run(current, target) is target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RunStatus.QUEUED, RunStatus.COMPLETED),
        (RunStatus.RUNNING, RunStatus.QUEUED),
        (RunStatus.COMPLETED, RunStatus.RUNNING),
        (RunStatus.FAILED, RunStatus.RUNNING),
        (RunStatus.CANCELLED, RunStatus.QUEUED),
        (RunStatus.INTERRUPTED, RunStatus.COMPLETED),
        (RunStatus.RUNNING, RunStatus.RUNNING),
    ],
)
def test_transition_run_rejects_invalid_edges(
    current: RunStatus,
    target: RunStatus,
) -> None:
    with pytest.raises(InvalidRunTransition):
        transition_run(current, target)
