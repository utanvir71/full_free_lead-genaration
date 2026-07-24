from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert
from starlette.testclient import TestClient

from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.main import create_app


def test_lead_review_routes_add_note_and_manual_status(tmp_path: Path) -> None:
    settings = Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "db.sqlite3")})
    engine = create_engine_for(settings)
    migrate_database(engine)
    now = datetime(2026, 7, 25, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            insert(schema.businesses).values(
                id="b1",
                name="Elm House",
                lead_status="new",
                created_at=now,
                updated_at=now,
            )
        )
    client = TestClient(create_app(settings))
    token = client.get("/runs").cookies["csrf_token"]

    note = client.post(
        "/leads/b1/notes",
        data={"body": "Call after lunch", "csrf_token": token},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    status = client.post(
        "/leads/b1/status",
        data={"status": "contacted", "csrf_token": token},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )

    assert note.status_code == 303
    assert status.status_code == 303
    detail = client.get("/leads/b1")
    assert "Call after lunch" in detail.text
    assert "contacted" in detail.text
