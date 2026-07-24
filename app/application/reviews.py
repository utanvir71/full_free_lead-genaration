from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Engine, select

from app.db import schema
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import LeadStatus


class InvalidStatusTransition(ValueError):
    pass


class ReviewService:
    def __init__(self, engine: Engine, *, clock: Callable[[], datetime]) -> None:
        self._engine = engine
        self._clock = clock

    def add_note(self, business_id: str, body: str) -> None:
        clean_body = body.strip()
        if not clean_body:
            raise ValueError("Note is required")
        with SqlAlchemyUnitOfWork(self._engine) as unit_of_work:
            unit_of_work.reviews.add_note(
                note_id=str(uuid4()),
                business_id=business_id,
                body=clean_body,
                created_at=self._clock(),
            )

    def change_status(self, business_id: str, target: LeadStatus) -> None:
        with self._engine.connect() as connection:
            current_value = connection.scalar(
                select(schema.businesses.c.lead_status).where(
                    schema.businesses.c.id == business_id
                )
            )
        if current_value is None:
            raise LookupError(business_id)
        current = LeadStatus(current_value)
        if target is LeadStatus.REJECTED and current in {
            LeadStatus.CONTACTED,
            LeadStatus.REPLIED,
        }:
            raise InvalidStatusTransition("Rejected is only available before contact")
        with SqlAlchemyUnitOfWork(self._engine) as unit_of_work:
            unit_of_work.reviews.change_status(
                history_id=str(uuid4()),
                business_id=business_id,
                target=target,
                changed_at=self._clock(),
            )
