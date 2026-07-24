from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError

from app.application.ports import RestaurantCheckpoint, RunRecord
from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import (
    FactState,
    LeadStatus,
    RunStatus,
    SignalState,
    ValidationState,
)
from app.domain.models import Assessment, Fact, ScoreComponent

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def make_engine(tmp_path: Path) -> Engine:
    settings = Settings.load(
        {"LEADGEN_DATABASE_PATH": str(tmp_path / "leadgen.sqlite3")}
    )
    engine = create_engine_for(settings)
    migrate_database(engine)
    return engine


def add_run(engine: Engine, run_id: str) -> None:
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.runs.add(
            RunRecord(
                run_id=run_id,
                city="Austin",
                state="TX",
                candidate_limit=30,
                status=RunStatus.QUEUED,
                created_at=NOW,
            )
        )


def make_fact(fact_id: str = "fact-1") -> Fact:
    return Fact(
        fact_id=fact_id,
        fact_type="reservation_method",
        state=FactState.PRESENT,
        value="Call the restaurant",
        source="https://example.com/reservations",
        excerpt="For reservations, call us.",
        captured_at=NOW,
        extractor_version="reservations-v1",
        validation_state=ValidationState.VALID,
    )


def make_assessment(run_id: str, business_id: str) -> Assessment:
    return Assessment(
        assessment_id=f"assessment-{run_id}",
        run_id=run_id,
        business_id=business_id,
        scoring_version="scoring-v1",
        components=(
            ScoreComponent(
                signal="calling_required",
                state=SignalState.AWARDED,
                delta=3,
                explanation="The official page requires calling.",
                evidence_ids=("fact-1",),
            ),
        ),
        total=3,
        qualified=False,
    )


def make_checkpoint(
    run_id: str,
    business_id: str = "business-1",
    *,
    canonical_name: str = "Original Restaurant",
    snapshot_name: str = "Original Restaurant",
    facts: tuple[Fact, ...] | None = None,
) -> RestaurantCheckpoint:
    return RestaurantCheckpoint(
        run_id=run_id,
        business_id=business_id,
        canonical_name=canonical_name,
        snapshot_id=f"snapshot-{run_id}",
        snapshot_name=snapshot_name,
        captured_at=NOW,
        facts=facts if facts is not None else (make_fact(),),
        assessment=make_assessment(run_id, business_id),
    )


def test_checkpoint_saves_related_stage_records_atomically(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    add_run(engine, "run-1")

    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.checkpoint_restaurant(make_checkpoint("run-1"))

    with engine.connect() as connection:
        business_count = connection.scalar(
            select(func.count()).select_from(schema.businesses)
        )
        assert (
            connection.scalar(select(func.count()).select_from(schema.run_candidates))
            == 1
        )
        assert connection.scalar(select(func.count()).select_from(schema.facts)) == 1
        assert (
            connection.scalar(select(func.count()).select_from(schema.assessments)) == 1
        )
        assert (
            connection.scalar(select(func.count()).select_from(schema.score_signals))
            == 1
        )
    assert business_count == 1


def test_failed_checkpoint_rolls_back_without_orphans(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    add_run(engine, "run-1")
    duplicate_facts = (make_fact(), make_fact())

    with (
        pytest.raises(IntegrityError),
        SqlAlchemyUnitOfWork(engine) as unit_of_work,
    ):
        unit_of_work.checkpoint_restaurant(
            make_checkpoint("run-1", facts=duplicate_facts)
        )

    with engine.connect() as connection:
        business_count = connection.scalar(
            select(func.count()).select_from(schema.businesses)
        )
        assert (
            connection.scalar(select(func.count()).select_from(schema.run_candidates))
            == 0
        )
        assert connection.scalar(select(func.count()).select_from(schema.facts)) == 0
        assert (
            connection.scalar(select(func.count()).select_from(schema.assessments)) == 0
        )
    assert business_count == 0


def test_canonical_updates_preserve_snapshots_notes_and_manual_status(
    tmp_path: Path,
) -> None:
    engine = make_engine(tmp_path)
    add_run(engine, "run-1")
    add_run(engine, "run-2")

    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.checkpoint_restaurant(
            make_checkpoint(
                "run-1",
                canonical_name="Original Restaurant",
                snapshot_name="Original Restaurant",
            )
        )
        unit_of_work.reviews.add_note(
            note_id="note-1",
            business_id="business-1",
            body="Call after 3 PM.",
            created_at=NOW,
        )
        unit_of_work.reviews.change_status(
            history_id="history-1",
            business_id="business-1",
            target=LeadStatus.NEEDS_REVIEW,
            changed_at=NOW,
        )

    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.checkpoint_restaurant(
            make_checkpoint(
                "run-2",
                canonical_name="Renamed Restaurant",
                snapshot_name="Renamed Restaurant",
                facts=(make_fact("fact-2"),),
            )
        )

    with engine.connect() as connection:
        snapshots = connection.execute(
            select(
                schema.run_candidates.c.run_id,
                schema.run_candidates.c.name_snapshot,
            )
            .order_by(schema.run_candidates.c.run_id)
        ).all()
        business = connection.execute(select(schema.businesses)).mappings().one()
        notes = connection.scalar(select(func.count()).select_from(schema.notes))
        history = connection.scalar(
            select(func.count()).select_from(schema.status_history)
        )

    assert snapshots == [
        ("run-1", "Original Restaurant"),
        ("run-2", "Renamed Restaurant"),
    ]
    assert business["name"] == "Renamed Restaurant"
    assert business["lead_status"] == LeadStatus.NEEDS_REVIEW.value
    assert notes == 1
    assert history == 1
