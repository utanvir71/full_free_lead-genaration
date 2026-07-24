from __future__ import annotations

from types import TracebackType
from typing import Literal

from sqlalchemy import Connection, Engine, insert
from sqlalchemy.engine import RootTransaction

from app.application.ports import RestaurantCheckpoint
from app.db import schema
from app.db.repositories import (
    SqlAssessmentRepository,
    SqlBusinessRepository,
    SqlDraftRepository,
    SqlErrorRepository,
    SqlEvidenceRepository,
    SqlExportRepository,
    SqlJobRepository,
    SqlReviewRepository,
    SqlRunRepository,
)


class SqlAlchemyUnitOfWork:
    runs: SqlRunRepository
    jobs: SqlJobRepository
    businesses: SqlBusinessRepository
    evidence: SqlEvidenceRepository
    assessments: SqlAssessmentRepository
    drafts: SqlDraftRepository
    reviews: SqlReviewRepository
    errors: SqlErrorRepository
    exports: SqlExportRepository

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None
        self._transaction: RootTransaction | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        connection = self._engine.connect()
        self._connection = connection
        self._transaction = connection.begin()
        self.runs = SqlRunRepository(connection)
        self.jobs = SqlJobRepository(connection)
        self.businesses = SqlBusinessRepository(connection)
        self.evidence = SqlEvidenceRepository(connection)
        self.assessments = SqlAssessmentRepository(connection)
        self.drafts = SqlDraftRepository(connection)
        self.reviews = SqlReviewRepository(connection)
        self.errors = SqlErrorRepository(connection)
        self.exports = SqlExportRepository(connection)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if self._transaction is None or self._connection is None:
            raise RuntimeError("Unit of work was not entered")
        try:
            if exc_type is None:
                self._transaction.commit()
            else:
                self._transaction.rollback()
        finally:
            self._connection.close()
            self._connection = None
            self._transaction = None
        return False

    def checkpoint_restaurant(self, checkpoint: RestaurantCheckpoint) -> None:
        connection = self._require_connection()
        if checkpoint.assessment.run_id != checkpoint.run_id:
            raise ValueError("Assessment run does not match checkpoint run")
        if checkpoint.assessment.business_id != checkpoint.business_id:
            raise ValueError("Assessment business does not match checkpoint business")

        self.businesses.upsert_canonical(
            checkpoint.business_id,
            checkpoint.canonical_name,
            checkpoint.captured_at,
        )
        connection.execute(
            insert(schema.run_candidates).values(
                id=checkpoint.snapshot_id,
                run_id=checkpoint.run_id,
                business_id=checkpoint.business_id,
                name_snapshot=checkpoint.snapshot_name,
                created_at=checkpoint.captured_at,
            )
        )
        for fact in checkpoint.facts:
            self.evidence.add_fact(
                checkpoint.run_id,
                checkpoint.business_id,
                fact,
            )
        self.assessments.add(checkpoint.assessment)

    def _require_connection(self) -> Connection:
        if self._connection is None:
            raise RuntimeError("Unit of work must be entered before use")
        return self._connection
