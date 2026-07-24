from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.application.ports import JobRecord, RunRecord
from app.db import schema
from app.domain.enums import JobStatus, LeadStatus, RunStatus
from app.domain.models import Assessment, Draft, Fact, StageError


class SqlRunRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, record: RunRecord) -> None:
        self._connection.execute(
            insert(schema.runs).values(
                id=record.run_id,
                city=record.city,
                state=record.state,
                candidate_limit=record.candidate_limit,
                status=record.status.value,
                created_at=record.created_at,
                started_at=record.started_at,
                finished_at=record.finished_at,
            )
        )

    def get(self, run_id: str) -> RunRecord | None:
        row = self._connection.execute(
            select(schema.runs).where(schema.runs.c.id == run_id)
        ).mappings().one_or_none()
        return None if row is None else _run_record(row)

    def active(self) -> RunRecord | None:
        row = self._connection.execute(
            select(schema.runs)
            .where(
                schema.runs.c.status.in_(
                    (RunStatus.QUEUED.value, RunStatus.RUNNING.value)
                )
            )
            .order_by(schema.runs.c.created_at)
        ).mappings().first()
        return None if row is None else _run_record(row)

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": status.value}
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        self._connection.execute(
            update(schema.runs).where(schema.runs.c.id == run_id).values(**values)
        )


class SqlJobRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, record: JobRecord) -> None:
        self._connection.execute(
            insert(schema.jobs).values(
                id=record.job_id,
                run_id=record.run_id,
                business_id=record.business_id,
                stage=record.stage,
                status=record.status.value,
                attempt_count=record.attempt_count,
                max_attempts=record.max_attempts,
                next_attempt_at=record.next_attempt_at,
                lease_expires_at=record.lease_expires_at,
                error_code=record.error_code,
                idempotency_key=record.idempotency_key,
                created_at=record.created_at,
                updated_at=record.updated_at,
                completed_at=record.completed_at,
            )
        )

    def for_run(self, run_id: str) -> tuple[JobRecord, ...]:
        rows = self._connection.execute(
            select(schema.jobs)
            .where(schema.jobs.c.run_id == run_id)
            .order_by(schema.jobs.c.created_at, schema.jobs.c.id)
        ).mappings()
        return tuple(_job_record(row) for row in rows)

    def expired_running(self, now: datetime) -> tuple[JobRecord, ...]:
        rows = self._connection.execute(
            select(schema.jobs)
            .where(schema.jobs.c.status == JobStatus.RUNNING.value)
            .where(schema.jobs.c.lease_expires_at.is_not(None))
            .where(schema.jobs.c.lease_expires_at < now)
            .order_by(schema.jobs.c.created_at, schema.jobs.c.id)
        ).mappings()
        return tuple(_job_record(row) for row in rows)

    def recover(self, record: JobRecord, target: JobStatus, now: datetime) -> None:
        self._connection.execute(
            update(schema.jobs)
            .where(schema.jobs.c.id == record.job_id)
            .values(
                status=target.value,
                lease_expires_at=None,
                updated_at=now,
                error_code=(
                    "interrupted_after_retries"
                    if target is JobStatus.INTERRUPTED
                    else None
                ),
            )
        )


class SqlBusinessRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert_canonical(
        self,
        business_id: str,
        name: str,
        captured_at: datetime,
    ) -> None:
        statement = sqlite_insert(schema.businesses).values(
            id=business_id,
            name=name,
            lead_status=LeadStatus.NEW.value,
            created_at=captured_at,
            updated_at=captured_at,
        )
        self._connection.execute(
            statement.on_conflict_do_update(
                index_elements=[schema.businesses.c.id],
                set_={"name": name, "updated_at": captured_at},
            )
        )


class SqlEvidenceRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add_fact(self, run_id: str, business_id: str, fact: Fact) -> None:
        self._connection.execute(
            insert(schema.facts).values(
                id=fact.fact_id,
                run_id=run_id,
                business_id=business_id,
                fact_type=fact.fact_type,
                state=fact.state.value,
                value_json=json.dumps(fact.value),
                source=fact.source,
                excerpt=fact.excerpt,
                captured_at=fact.captured_at,
                extractor_version=fact.extractor_version,
                validation_state=fact.validation_state.value,
                idempotency_key=fact.fact_id,
            )
        )


class SqlAssessmentRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, assessment: Assessment) -> None:
        self._connection.execute(
            insert(schema.assessments).values(
                id=assessment.assessment_id,
                run_id=assessment.run_id,
                business_id=assessment.business_id,
                total=assessment.total,
                qualified=assessment.qualified,
                scoring_version=assessment.scoring_version,
                created_at=datetime.now().astimezone(),
            )
        )
        for component in assessment.components:
            self._connection.execute(
                insert(schema.score_signals).values(
                    id=f"{assessment.assessment_id}:{component.signal}",
                    assessment_id=assessment.assessment_id,
                    signal=component.signal,
                    state=component.state.value,
                    delta=component.delta,
                    explanation=component.explanation,
                    evidence_ids_json=json.dumps(component.evidence_ids),
                )
            )


class SqlDraftRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, draft: Draft) -> None:
        self._connection.execute(
            insert(schema.drafts).values(
                id=draft.draft_id,
                run_id=draft.run_id,
                business_id=draft.business_id,
                subject=draft.subject,
                body=draft.body,
                method=draft.method.value,
                evidence_ids_json=json.dumps(draft.evidence_ids),
                validation_state=draft.validation_state.value,
                version=draft.version,
                created_at=draft.created_at,
            )
        )


class SqlReviewRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add_note(
        self,
        *,
        note_id: str,
        business_id: str,
        body: str,
        created_at: datetime,
    ) -> None:
        self._connection.execute(
            insert(schema.notes).values(
                id=note_id,
                business_id=business_id,
                body=body,
                created_at=created_at,
            )
        )

    def change_status(
        self,
        *,
        history_id: str,
        business_id: str,
        target: LeadStatus,
        changed_at: datetime,
    ) -> None:
        current = self._connection.scalar(
            select(schema.businesses.c.lead_status).where(
                schema.businesses.c.id == business_id
            )
        )
        self._connection.execute(
            update(schema.businesses)
            .where(schema.businesses.c.id == business_id)
            .values(lead_status=target.value, updated_at=changed_at)
        )
        self._connection.execute(
            insert(schema.status_history).values(
                id=history_id,
                business_id=business_id,
                from_status=current,
                to_status=target.value,
                changed_at=changed_at,
            )
        )


class SqlErrorRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(
        self,
        error: StageError,
        *,
        run_id: str,
        business_id: str | None = None,
        job_id: str | None = None,
    ) -> None:
        self._connection.execute(
            insert(schema.errors).values(
                id=error.error_id,
                run_id=run_id,
                business_id=business_id,
                job_id=job_id,
                stage=error.stage,
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                occurred_at=error.occurred_at,
                idempotency_key=error.error_id,
            )
        )


class SqlExportRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(
        self,
        *,
        export_id: str,
        run_id: str,
        kind: str,
        file_path: str,
        row_count: int,
        generated_at: datetime,
    ) -> None:
        self._connection.execute(
            insert(schema.exports).values(
                id=export_id,
                run_id=run_id,
                kind=kind,
                file_path=file_path,
                row_count=row_count,
                generated_at=generated_at,
            )
        )


def _run_record(row: Any) -> RunRecord:
    return RunRecord(
        run_id=row["id"],
        city=row["city"],
        state=row["state"],
        candidate_limit=row["candidate_limit"],
        status=RunStatus(row["status"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def _job_record(row: Any) -> JobRecord:
    return JobRecord(
        job_id=row["id"],
        run_id=row["run_id"],
        business_id=row["business_id"],
        stage=row["stage"],
        status=JobStatus(row["status"]),
        attempt_count=row["attempt_count"],
        max_attempts=row["max_attempts"],
        next_attempt_at=row["next_attempt_at"],
        lease_expires_at=row["lease_expires_at"],
        error_code=row["error_code"],
        idempotency_key=row["idempotency_key"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )
