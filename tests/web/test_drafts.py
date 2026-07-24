from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert
from starlette.testclient import TestClient

from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.main import create_app


def test_draft_review_is_local_and_has_no_send_surface(tmp_path: Path) -> None:
    settings = Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "db.sqlite3")})
    engine = create_engine_for(settings)
    migrate_database(engine)
    now = datetime(2026, 7, 25, tzinfo=UTC)
    with engine.begin() as c:
        c.execute(
            insert(schema.runs).values(
                id="r1",
                city="Austin",
                state="TX",
                candidate_limit=30,
                status="completed",
                created_at=now,
            )
        )
        c.execute(
            insert(schema.businesses).values(
                id="b1",
                name="Elm House",
                lead_status="draft_ready",
                created_at=now,
                updated_at=now,
            )
        )
        c.execute(
            insert(schema.drafts).values(
                id="d1",
                run_id="r1",
                business_id="b1",
                subject="Hello",
                body="A grounded draft",
                method="fallback",
                evidence_ids_json='["f1"]',
                validation_state="valid",
                version="v1",
                created_at=now,
            )
        )
    client = TestClient(create_app(settings))
    assert "Elm House" in client.get("/runs/r1/drafts").text
    detail = client.get("/drafts/d1")
    assert "A grounded draft" in detail.text
    assert "send" not in detail.text.lower()
