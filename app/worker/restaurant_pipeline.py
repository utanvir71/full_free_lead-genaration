from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.application.ports import RestaurantCheckpoint
from app.domain.models import Assessment, Fact, StageError


@dataclass(frozen=True, slots=True)
class RestaurantResearch:
    canonical_name: str
    snapshot_id: str
    snapshot_name: str
    captured_at: datetime
    facts: tuple[Fact, ...]
    assessment: Assessment


@dataclass(frozen=True, slots=True)
class PipelineResult:
    checkpointed: bool
    error: StageError | None = None


class RestaurantCheckpointRepository(Protocol):
    def checkpoint(self, checkpoint: RestaurantCheckpoint) -> None: ...


class RestaurantErrorRepository(Protocol):
    def add(self, error: StageError, *, run_id: str, business_id: str) -> None: ...


class PipelineStageFailure(Exception):
    def __init__(self, error: StageError) -> None:
        super().__init__(error.message)
        self.error = error


class RestaurantPipeline:
    def __init__(
        self,
        *,
        repository: RestaurantCheckpointRepository,
        research: Callable[[str, str], RestaurantResearch],
        errors: RestaurantErrorRepository | None = None,
    ) -> None:
        self._repository = repository
        self._research = research
        self._errors = errors
        self._processed: set[tuple[str, str]] = set()

    def process(self, run_id: str, business_id: str) -> PipelineResult:
        key = (run_id, business_id)
        if key in self._processed:
            return PipelineResult(checkpointed=False)

        try:
            research = self._research(run_id, business_id)
        except PipelineStageFailure as failure:
            if self._errors is not None:
                self._errors.add(failure.error, run_id=run_id, business_id=business_id)
            return PipelineResult(checkpointed=False, error=failure.error)
        self._repository.checkpoint(
            RestaurantCheckpoint(
                run_id=run_id,
                business_id=business_id,
                canonical_name=research.canonical_name,
                snapshot_id=research.snapshot_id,
                snapshot_name=research.snapshot_name,
                captured_at=research.captured_at,
                facts=research.facts,
                assessment=research.assessment,
            )
        )
        self._processed.add(key)
        return PipelineResult(checkpointed=True)
