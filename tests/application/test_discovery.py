from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, insert, select

from app.adapters.overpass.parser import Candidate
from app.application.discovery import DiscoveryService
from app.application.ports import RunRecord
from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import LeadStatus, RunStatus

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def make_engine(tmp_path: Path) -> Engine:
    engine = create_engine_for(
        Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "leadgen.sqlite3")})
    )
    migrate_database(engine)
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.runs.add(
            RunRecord(
                run_id="run-1",
                city="Austin",
                state="TX",
                candidate_limit=30,
                status=RunStatus.QUEUED,
                created_at=NOW,
            )
        )
    return engine


def candidate(*, osm_id: int = 101, phone: str = "(512) 555-0199") -> Candidate:
    return Candidate(
        osm_type="node",
        osm_id=osm_id,
        latitude=30.2672,
        longitude=-97.7431,
        tags={
            "name": "Northstar Grill",
            "website": "https://www.northstar.example.com/menu",
            "phone": phone,
            "addr:housenumber": "123",
            "addr:street": "Main St",
            "addr:city": "Austin",
            "addr:state": "TX",
            "addr:postcode": "78701",
        },
    )


def test_reconcile_reuses_exact_osm_identity_and_keeps_new_run_snapshot(
    tmp_path: Path,
) -> None:
    engine = make_engine(tmp_path)
    service = DiscoveryService(engine, clock=lambda: NOW)

    first = service.reconcile("run-1", [candidate()])

    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.runs.add(
            RunRecord(
                run_id="run-2",
                city="Austin",
                state="TX",
                candidate_limit=30,
                status=RunStatus.QUEUED,
                created_at=NOW,
            )
        )
    second = service.reconcile("run-2", [candidate()])

    assert first[0].business_id == second[0].business_id
    with engine.connect() as connection:
        snapshots = connection.execute(
            select(
                schema.run_candidates.c.run_id, schema.run_candidates.c.business_id
            ).order_by(schema.run_candidates.c.run_id)
        ).all()
    assert snapshots == [
        ("run-1", first[0].business_id),
        ("run-2", first[0].business_id),
    ]


def test_reconcile_marks_conflicting_secondary_identity_matches_for_review(
    tmp_path: Path,
) -> None:
    engine = make_engine(tmp_path)
    with engine.begin() as connection:
        connection.execute(
            insert(schema.businesses),
            [
                {
                    "id": "business-domain",
                    "name": "Domain Match",
                    "lead_status": LeadStatus.NEW.value,
                    "created_at": NOW,
                    "updated_at": NOW,
                },
                {
                    "id": "business-phone",
                    "name": "Phone Match",
                    "lead_status": LeadStatus.NEW.value,
                    "created_at": NOW,
                    "updated_at": NOW,
                },
            ],
        )
        connection.execute(
            insert(schema.business_aliases),
            [
                {
                    "id": "domain-alias",
                    "business_id": "business-domain",
                    "alias_type": "domain",
                    "normalized_value": "example.com",
                    "created_at": NOW,
                },
                {
                    "id": "phone-alias",
                    "business_id": "business-phone",
                    "alias_type": "phone",
                    "normalized_value": "+15125550199",
                    "created_at": NOW,
                },
            ],
        )

    result = DiscoveryService(engine, clock=lambda: NOW).reconcile(
        "run-1", [candidate()]
    )

    assert result[0].needs_review is True
    with engine.connect() as connection:
        status = connection.scalar(
            select(schema.businesses.c.lead_status).where(
                schema.businesses.c.id == result[0].business_id
            )
        )
    assert status == LeadStatus.NEEDS_REVIEW.value
