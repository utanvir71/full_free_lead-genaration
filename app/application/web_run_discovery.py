from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Engine, insert, select, update

from app.adapters.overpass.client import DiscoveryRequest
from app.adapters.overpass.parser import Candidate
from app.application.discovery import DiscoveryService
from app.db import schema
from app.domain.enums import RunStatus
from app.domain.lifecycle import transition_run


class DiscoveryProvider(Protocol):
    def discover(self, request: DiscoveryRequest) -> list[Candidate]: ...


@dataclass(frozen=True, slots=True)
class _RunningRun:
    city: str
    state: str
    candidate_limit: int


class WebRunDiscovery:
    def __init__(
        self,
        engine: Engine,
        *,
        provider: DiscoveryProvider,
        clock: Callable[[], datetime],
    ) -> None:
        self._engine = engine
        self._provider = provider
        self._clock = clock

    def execute(self, run_id: str) -> None:
        run = self._running_run(run_id)
        if run is None:
            return
        request = DiscoveryRequest(
            run_id=run_id,
            city=run.city,
            state=run.state,
            limit=run.candidate_limit,
        )
        try:
            candidates = self._provider.discover(request)
            if self._running_run(run_id) is None:
                return
            DiscoveryService(self._engine, clock=self._clock).reconcile(
                run_id, candidates
            )
        except Exception:
            self._fail_if_running(run_id)
            return
        self._complete_if_running(run_id)

    def _running_run(self, run_id: str) -> _RunningRun | None:
        with self._engine.connect() as connection:
            row = connection.execute(
                select(
                    schema.runs.c.city,
                    schema.runs.c.state,
                    schema.runs.c.candidate_limit,
                    schema.runs.c.status,
                ).where(schema.runs.c.id == run_id)
            ).mappings().one_or_none()
        if row is None or row["status"] != RunStatus.RUNNING.value:
            return None
        return _RunningRun(
            city=str(row["city"]),
            state=str(row["state"]),
            candidate_limit=int(row["candidate_limit"]),
        )

    def _complete_if_running(self, run_id: str) -> None:
        now = self._clock()
        with self._engine.begin() as connection:
            status = connection.scalar(
                select(schema.runs.c.status).where(schema.runs.c.id == run_id)
            )
            if status != RunStatus.RUNNING.value:
                return
            connection.execute(
                update(schema.runs)
                .where(schema.runs.c.id == run_id)
                .values(
                    status=transition_run(
                        RunStatus.RUNNING, RunStatus.COMPLETED
                    ).value,
                    finished_at=now,
                )
            )

    def _fail_if_running(self, run_id: str) -> None:
        now = self._clock()
        with self._engine.begin() as connection:
            status = connection.scalar(
                select(schema.runs.c.status).where(schema.runs.c.id == run_id)
            )
            if status != RunStatus.RUNNING.value:
                return
            connection.execute(
                update(schema.runs)
                .where(schema.runs.c.id == run_id)
                .values(
                    status=transition_run(
                        RunStatus.RUNNING, RunStatus.FAILED
                    ).value,
                    finished_at=now,
                )
            )
            connection.execute(
                insert(schema.errors).values(
                    id=str(uuid5(NAMESPACE_URL, f"{run_id}:discovery_failed")),
                    run_id=run_id,
                    business_id=None,
                    job_id=None,
                    stage="discovery",
                    code="discovery_failed",
                    message="Restaurant discovery failed. Try again later.",
                    retryable=True,
                    occurred_at=now,
                    idempotency_key=f"{run_id}:discovery_failed",
                )
            )
