from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.application.reviews import InvalidStatusTransition, ReviewService
from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import LeadStatus


def test_review_service_records_notes_and_manual_status_history(tmp_path: Path) -> None:
    engine = create_engine_for(
        Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "db.sqlite3")})
    )
    migrate_database(engine)
    now = datetime(2026, 7, 25, tzinfo=UTC)
    with SqlAlchemyUnitOfWork(engine) as uow:
        uow.businesses.upsert_canonical("b1", "Elm House", now)
    service = ReviewService(engine, clock=lambda: now)
    service.add_note("b1", "Call after lunch")
    service.change_status("b1", LeadStatus.CONTACTED)
    with engine.connect() as connection:
        assert connection.scalar(select(schema.notes.c.body)) == "Call after lunch"


def test_rejected_cannot_follow_contacted(tmp_path: Path) -> None:
    engine = create_engine_for(
        Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "db.sqlite3")})
    )
    migrate_database(engine)
    now = datetime(2026, 7, 25, tzinfo=UTC)
    with SqlAlchemyUnitOfWork(engine) as uow:
        uow.businesses.upsert_canonical("b1", "Elm House", now)
    service = ReviewService(engine, clock=lambda: now)
    service.change_status("b1", LeadStatus.CONTACTED)
    with pytest.raises(InvalidStatusTransition):
        service.change_status("b1", LeadStatus.REJECTED)
