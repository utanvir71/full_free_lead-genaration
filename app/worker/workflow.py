from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import JobStatus


class OneJobRunner(Protocol):
    def run_once(self) -> JobStatus | None: ...


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    jobs_processed: int


class RunWorkflow:
    def __init__(self, *, runner: OneJobRunner) -> None:
        self._runner = runner

    def execute(self, run_id: str) -> WorkflowResult:
        del run_id
        jobs_processed = 0
        while self._runner.run_once() is not None:
            jobs_processed += 1
        return WorkflowResult(jobs_processed=jobs_processed)
