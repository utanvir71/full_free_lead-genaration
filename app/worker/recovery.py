from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine

from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import JobStatus


@dataclass(frozen=True)
class RecoveryResult:
    requeued_job_ids: tuple[str, ...]
    interrupted_job_ids: tuple[str, ...]


def recover_expired_jobs(engine: Engine, *, now: datetime) -> RecoveryResult:
    requeued: list[str] = []
    interrupted: list[str] = []
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        for job in unit_of_work.jobs.expired_running(now):
            if job.attempt_count < job.max_attempts:
                target = JobStatus.PENDING
                requeued.append(job.job_id)
            else:
                target = JobStatus.INTERRUPTED
                interrupted.append(job.job_id)
            unit_of_work.jobs.recover(job, target, now)
    return RecoveryResult(tuple(requeued), tuple(interrupted))
