from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert, update
from starlette.testclient import TestClient

from app.application.ports import JobRecord
from app.application.runs import RunService
from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.enums import JobStatus, RunStatus
from app.main import create_app

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def make_client(tmp_path: Path) -> tuple[TestClient, object]:
    settings = Settings.load(
        {"LEADGEN_DATABASE_PATH": str(tmp_path / "leadgen.sqlite3")}
    )
    engine = create_engine_for(settings)
    migrate_database(engine)
    RunService(engine, clock=lambda: NOW).start(
        run_id="run-1", city="Austin", state="TX", candidate_limit=30
    )
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        for job_id, status in (
            ("pending", JobStatus.PENDING),
            ("running", JobStatus.RUNNING),
            ("failed", JobStatus.FAILED),
        ):
            unit_of_work.jobs.add(
                JobRecord(
                    job_id=job_id,
                    run_id="run-1",
                    stage="research",
                    status=status,
                    attempt_count=0,
                    max_attempts=2,
                    idempotency_key=f"run-1/{job_id}",
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
    with engine.begin() as connection:
        connection.execute(
            insert(schema.errors).values(
                id="error-1",
                run_id="run-1",
                business_id=None,
                job_id="failed",
                stage="crawl",
                code="timeout",
                message="Website timed out",
                retryable=True,
                occurred_at=NOW,
                idempotency_key="error-1",
            )
        )
    return TestClient(create_app(settings)), engine


def test_progress_page_and_endpoint_read_persisted_counts_and_safe_errors(
    tmp_path: Path,
) -> None:
    client, _ = make_client(tmp_path)

    page = client.get("/runs/run-1")
    progress = client.get("/runs/run-1/progress")

    assert page.status_code == 200
    assert "Austin, TX" in page.text
    assert "Website timed out" in page.text
    assert "Traceback" not in page.text
    assert progress.json() == {
        "run_id": "run-1",
        "status": "running",
        "discovered": 0,
        "pending": 1,
        "processing": 1,
        "qualified": 0,
        "rejected": 0,
        "drafted": 0,
        "failed": 1,
        "terminal": False,
    }


def test_progress_page_marks_terminal_run_for_polling_stop(tmp_path: Path) -> None:
    client, engine = make_client(tmp_path)
    with engine.begin() as connection:
        connection.execute(
            update(schema.runs)
            .where(schema.runs.c.id == "run-1")
            .values(status=RunStatus.INTERRUPTED.value)
        )

    response = client.get("/runs/run-1")

    assert response.status_code == 200
    assert 'data-terminal="true"' in response.text
    assert client.get("/runs/run-1/progress").json()["terminal"] is True
