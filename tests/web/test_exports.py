from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert
from starlette.testclient import TestClient

from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.main import create_app


def test_export_download_reads_authoritative_registered_csv(tmp_path: Path) -> None:
    settings = Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "db.sqlite3")})
    engine = create_engine_for(settings)
    migrate_database(engine)
    export = tmp_path / "qualified_leads.csv"
    export.write_text("name\nElm House\n")
    with engine.begin() as connection:
        connection.execute(
            insert(schema.runs).values(
                id="r1",
                city="Austin",
                state="TX",
                candidate_limit=30,
                status="completed",
                created_at=datetime(2026, 7, 25, tzinfo=UTC),
            )
        )
        connection.execute(
            insert(schema.exports).values(
                id="e1",
                run_id="r1",
                kind="qualified",
                file_path=str(export),
                row_count=1,
                generated_at=datetime(2026, 7, 25, tzinfo=UTC),
            )
        )
    client = TestClient(create_app(settings))

    response = client.get("/runs/r1/exports/qualified")

    assert response.status_code == 200
    assert response.text == "name\nElm House\n"
