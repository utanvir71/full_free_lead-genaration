from __future__ import annotations

from typing import Protocol

from app.application.ports import JobRecord
from app.domain.enums import JobStatus
from app.worker.restaurant_pipeline import PipelineResult


class RunnableJobs(Protocol):
    def claim_next(self) -> JobRecord | None: ...

    def complete(self, job: JobRecord) -> None: ...

    def fail(self, job: JobRecord) -> None: ...


class RestaurantProcessor(Protocol):
    def process(self, run_id: str, business_id: str) -> PipelineResult: ...


class JobRunner:
    def __init__(self, *, jobs: RunnableJobs, pipeline: RestaurantProcessor) -> None:
        self._jobs = jobs
        self._pipeline = pipeline

    def claim_next(self) -> JobRecord | None:
        return self._jobs.claim_next()

    def run_once(self) -> JobStatus | None:
        job = self.claim_next()
        if job is None:
            return None
        if job.business_id is None:
            self._jobs.fail(job)
            return JobStatus.FAILED

        result = self._pipeline.process(job.run_id, job.business_id)
        if result.error is not None or not result.checkpointed:
            self._jobs.fail(job)
            return JobStatus.FAILED
        self._jobs.complete(job)
        return JobStatus.COMPLETED
