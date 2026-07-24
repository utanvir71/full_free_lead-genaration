from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.enums import JobStatus, LeadStatus, RunStatus
from app.domain.models import Assessment, Draft, Fact, StageError


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    city: str
    state: str
    candidate_limit: int
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    run_id: str
    stage: str
    status: JobStatus
    attempt_count: int
    max_attempts: int
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    business_id: str | None = None
    next_attempt_at: datetime | None = None
    lease_expires_at: datetime | None = None
    error_code: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class RestaurantCheckpoint:
    run_id: str
    business_id: str
    canonical_name: str
    snapshot_id: str
    snapshot_name: str
    captured_at: datetime
    facts: tuple[Fact, ...]
    assessment: Assessment


class RunRepository(Protocol):
    def add(self, record: RunRecord) -> None: ...

    def get(self, run_id: str) -> RunRecord | None: ...

    def active(self) -> RunRecord | None: ...

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None: ...


class JobRepository(Protocol):
    def add(self, record: JobRecord) -> None: ...

    def for_run(self, run_id: str) -> tuple[JobRecord, ...]: ...


class BusinessRepository(Protocol):
    def upsert_canonical(
        self,
        business_id: str,
        name: str,
        captured_at: datetime,
    ) -> None: ...


class EvidenceRepository(Protocol):
    def add_fact(self, run_id: str, business_id: str, fact: Fact) -> None: ...


class AssessmentRepository(Protocol):
    def add(self, assessment: Assessment) -> None: ...


class DraftRepository(Protocol):
    def add(self, draft: Draft) -> None: ...


class ReviewRepository(Protocol):
    def add_note(
        self,
        *,
        note_id: str,
        business_id: str,
        body: str,
        created_at: datetime,
    ) -> None: ...

    def change_status(
        self,
        *,
        history_id: str,
        business_id: str,
        target: LeadStatus,
        changed_at: datetime,
    ) -> None: ...


class ErrorRepository(Protocol):
    def add(
        self,
        error: StageError,
        *,
        run_id: str,
        business_id: str | None = None,
        job_id: str | None = None,
    ) -> None: ...


class ExportRepository(Protocol):
    def add(
        self,
        *,
        export_id: str,
        run_id: str,
        kind: str,
        file_path: str,
        row_count: int,
        generated_at: datetime,
    ) -> None: ...
