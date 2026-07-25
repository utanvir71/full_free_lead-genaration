from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import Engine

from app.application.ports import RunRecord
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import JobStatus, RunStatus
from app.domain.lifecycle import transition_run


class ActiveRunError(RuntimeError):
    pass


class RunNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class RunProgress:
    run_id: str
    status: RunStatus
    total_jobs: int
    pending: int
    running: int
    completed: int
    failed: int
    interrupted: int


class RunService:
    def __init__(self, engine: Engine, *, clock: Callable[[], datetime]) -> None:
        self._engine = engine
        self._clock = clock

    def start(
        self,
        *,
        run_id: str,
        city: str,
        state: str,
        candidate_limit: int,
    ) -> RunRecord:
        now = self._clock()
        queued = RunRecord(
            run_id=run_id,
            city=city,
            state=state,
            candidate_limit=candidate_limit,
            status=RunStatus.QUEUED,
            created_at=now,
        )
        with SqlAlchemyUnitOfWork(self._engine) as unit_of_work:
            active = unit_of_work.runs.active()
            if active is not None:
                raise ActiveRunError(f"Run {active.run_id} is already active")
            unit_of_work.runs.add(queued)
            running_status = transition_run(queued.status, RunStatus.RUNNING)
            unit_of_work.runs.update_status(
                run_id,
                running_status,
                started_at=now,
            )
        return RunRecord(
            run_id=queued.run_id,
            city=queued.city,
            state=queued.state,
            candidate_limit=queued.candidate_limit,
            status=running_status,
            created_at=queued.created_at,
            started_at=now,
        )
    def cancel(self, run_id: str) -> RunRecord:
        now = self._clock()
        with SqlAlchemyUnitOfWork(self._engine) as unit_of_work:
            run = unit_of_work.runs.get(run_id)
            if run is None:
                raise RunNotFoundError(run_id)
            cancelled_status = transition_run(run.status, RunStatus.CANCELLED)
            unit_of_work.runs.update_status(
                run_id,
                cancelled_status,
                finished_at=now,
            )
        return replace(
            run,
            status=cancelled_status,
            finished_at=now,
        )

    def progress(self, run_id: str) -> RunProgress:
        with SqlAlchemyUnitOfWork(self._engine) as unit_of_work:
            run = unit_of_work.runs.get(run_id)
            if run is None:
                raise RunNotFoundError(run_id)
            jobs = unit_of_work.jobs.for_run(run_id)

        counts = Counter(job.status for job in jobs)
        return RunProgress(
            run_id=run_id,
            status=run.status,
            total_jobs=len(jobs),
            pending=counts[JobStatus.PENDING],
            running=counts[JobStatus.RUNNING],
            completed=counts[JobStatus.COMPLETED],
            failed=counts[JobStatus.FAILED],
            interrupted=counts[JobStatus.INTERRUPTED],
        )
