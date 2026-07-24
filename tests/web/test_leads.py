from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert
from starlette.testclient import TestClient

from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.main import create_app

NOW = datetime(2026, 7, 25, tzinfo=UTC)


def test_lead_pages_show_evidence_score_and_osm_attribution(tmp_path: Path) -> None:
    settings = Settings.load(
        {"LEADGEN_DATABASE_PATH": str(tmp_path / "leadgen.sqlite3")}
    )
    engine = create_engine_for(settings)
    migrate_database(engine)
    with engine.begin() as c:
        c.execute(
            insert(schema.runs).values(
                id="r1",
                city="Austin",
                state="TX",
                candidate_limit=30,
                status="completed",
                created_at=NOW,
            )
        )
        c.execute(
            insert(schema.businesses).values(
                id="b1",
                name="Elm House",
                lead_status="new",
                website="https://elm.example",
                phone="555",
                address="1 Elm",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        c.execute(
            insert(schema.run_candidates).values(
                id="c1",
                run_id="r1",
                business_id="b1",
                osm_type="node",
                osm_id="1",
                name_snapshot="Elm House",
                created_at=NOW,
            )
        )
        c.execute(
            insert(schema.assessments).values(
                id="a1",
                run_id="r1",
                business_id="b1",
                total=6,
                qualified=True,
                scoring_version="scoring-v1",
                created_at=NOW,
            )
        )
        c.execute(
            insert(schema.score_signals).values(
                id="s1",
                assessment_id="a1",
                signal="call_reservations",
                state="true",
                delta=3,
                explanation="Call us",
                evidence_ids_json='["f1"]',
            )
        )
        c.execute(
            insert(schema.facts).values(
                id="f1",
                run_id="r1",
                business_id="b1",
                fact_type="reservations",
                state="true",
                value_json='"Call us"',
                source="https://elm.example",
                excerpt="Call us to reserve",
                captured_at=NOW,
                extractor_version="v1",
                validation_state="valid",
                idempotency_key="f1",
            )
        )

    client = TestClient(create_app(settings))
    assert "Elm House" in client.get("/runs/r1/leads").text
    page = client.get("/leads/b1")
    assert page.status_code == 200
    assert "Call us to reserve" in page.text
    assert "6" in page.text
    assert "OpenStreetMap" in page.text
