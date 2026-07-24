from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select

from app.application.ports import JobRecord
from app.application.runs import ActiveRunError, RunService
from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import JobStatus, RunStatus
from app.worker.recovery import recover_expired_jobs

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def make_engine(tmp_path: Path) -> Engine:
    settings = Settings.load(
        {"LEADGEN_DATABASE_PATH": str(tmp_path / "leadgen.sqlite3")}
    )
    engine = create_engine_for(settings)
    migrate_database(engine)
    return engine


def make_job(
    job_id: str,
    *,
    status: JobStatus,
    attempt_count: int = 0,
    max_attempts: int = 3,
    lease_expires_at: datetime | None = None,
) -> JobRecord:
    return JobRecord(
        job_id=job_id,
        run_id="run-1",
        stage="research",
        status=status,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        lease_expires_at=lease_expires_at,
        idempotency_key=f"run-1/{job_id}/research-v1",
        created_at=NOW,
        updated_at=NOW,
    )


def test_start_enforces_one_active_run(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    service = RunService(engine, clock=lambda: NOW)

    started = service.start(
        run_id="run-1",
        city="Austin",
        state="TX",
        candidate_limit=30,
    )

    assert started.status is RunStatus.RUNNING
    with pytest.raises(ActiveRunError):
        service.start(
            run_id="run-2",
            city="Dallas",
            state="TX",
            candidate_limit=30,
        )


def test_progress_is_rebuilt_from_persisted_jobs(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    RunService(engine, clock=lambda: NOW).start(
        run_id="run-1",
        city="Austin",
        state="TX",
        candidate_limit=30,
    )
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.jobs.add(make_job("pending", status=JobStatus.PENDING))
        unit_of_work.jobs.add(make_job("running", status=JobStatus.RUNNING))
        unit_of_work.jobs.add(make_job("complete", status=JobStatus.COMPLETED))
        unit_of_work.jobs.add(make_job("failed", status=JobStatus.FAILED))

    fresh_service = RunService(engine, clock=lambda: NOW + timedelta(hours=1))
    progress = fresh_service.progress("run-1")

    assert progress.total_jobs == 4
    assert progress.pending == 1
    assert progress.running == 1
    assert progress.completed == 1
    assert progress.failed == 1
    assert progress.interrupted == 0


def test_recovery_requeues_retryable_jobs_and_interrupts_exhausted_jobs(
    tmp_path: Path,
) -> None:
    engine = make_engine(tmp_path)
    RunService(engine, clock=lambda: NOW).start(
        run_id="run-1",
        city="Austin",
        state="TX",
        candidate_limit=30,
    )
    expired = NOW - timedelta(seconds=1)
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.jobs.add(
            make_job(
                "retryable",
                status=JobStatus.RUNNING,
                attempt_count=1,
                max_attempts=3,
                lease_expires_at=expired,
            )
        )
        unit_of_work.jobs.add(
            make_job(
                "exhausted",
                status=JobStatus.RUNNING,
                attempt_count=3,
                max_attempts=3,
                lease_expires_at=expired,
            )
        )
        unit_of_work.jobs.add(
            make_job(
                "completed",
                status=JobStatus.COMPLETED,
                attempt_count=1,
                lease_expires_at=expired,
            )
        )

    result = recover_expired_jobs(engine, now=NOW)

    assert result.requeued_job_ids == ("retryable",)
    assert result.interrupted_job_ids == ("exhausted",)
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        jobs = {job.job_id: job for job in unit_of_work.jobs.for_run("run-1")}
    assert jobs["retryable"].status is JobStatus.PENDING
    assert jobs["retryable"].lease_expires_at is None
    assert jobs["exhausted"].status is JobStatus.INTERRUPTED
    assert jobs["completed"].status is JobStatus.COMPLETED

    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(schema.jobs)) == 3
