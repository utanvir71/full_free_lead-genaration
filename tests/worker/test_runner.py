from dataclasses import replace
from datetime import UTC, datetime

from app.application.ports import JobRecord
from app.domain.enums import JobStatus
from app.worker.restaurant_pipeline import PipelineResult
from app.worker.runner import JobRunner

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


class FakeJobs:
    def __init__(self, jobs: list[JobRecord]) -> None:
        self.jobs = jobs
        self.completed: list[str] = []
        self.failed: list[str] = []

    def claim_next(self) -> JobRecord | None:
        for job in self.jobs:
            if job.status is JobStatus.PENDING:
                return job
        return None

    def complete(self, job: JobRecord) -> None:
        self.completed.append(job.job_id)
        self._replace(job, JobStatus.COMPLETED)

    def fail(self, job: JobRecord) -> None:
        self.failed.append(job.job_id)
        self._replace(job, JobStatus.FAILED)

    def _replace(self, job: JobRecord, status: JobStatus) -> None:
        self.jobs[self.jobs.index(job)] = replace(job, status=status)


class FakePipeline:
    def process(self, run_id: str, business_id: str) -> PipelineResult:
        return PipelineResult(checkpointed=business_id == "business-good")


def _job(job_id: str, business_id: str) -> JobRecord:
    return JobRecord(
        job_id=job_id,
        run_id="run-1",
        business_id=business_id,
        stage="research",
        status=JobStatus.PENDING,
        attempt_count=0,
        max_attempts=1,
        idempotency_key=job_id,
        created_at=NOW,
        updated_at=NOW,
    )


def test_runner_continues_after_one_restaurant_fails() -> None:
    jobs = FakeJobs(
        [_job("job-bad", "business-bad"), _job("job-good", "business-good")]
    )
    runner = JobRunner(jobs=jobs, pipeline=FakePipeline())

    first = runner.run_once()
    second = runner.run_once()

    assert first is JobStatus.FAILED
    assert second is JobStatus.COMPLETED
    assert jobs.failed == ["job-bad"]
    assert jobs.completed == ["job-good"]
