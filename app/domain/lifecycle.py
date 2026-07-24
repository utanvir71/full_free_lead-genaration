from app.domain.enums import RunStatus


class InvalidRunTransition(ValueError):
    pass


_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.COMPLETED,
            RunStatus.COMPLETED_WITH_ERRORS,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.INTERRUPTED,
        }
    ),
    RunStatus.INTERRUPTED: frozenset({RunStatus.QUEUED, RunStatus.CANCELLED}),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.COMPLETED_WITH_ERRORS: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


def transition_run(current: RunStatus, target: RunStatus) -> RunStatus:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidRunTransition(f"Cannot transition run from {current} to {target}")
    return target
