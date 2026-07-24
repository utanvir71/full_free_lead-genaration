from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.db.session import create_engine_for, migrate_database

EXPECTED_TABLES = {
    "runs",
    "jobs",
    "businesses",
    "business_aliases",
    "run_candidates",
    "source_records",
    "crawl_pages",
    "facts",
    "contacts",
    "people",
    "assessments",
    "score_signals",
    "drafts",
    "notes",
    "status_history",
    "errors",
    "exports",
}


def make_settings(database_path: Path) -> Settings:
    return Settings.load({"LEADGEN_DATABASE_PATH": str(database_path)})


def test_migration_creates_authoritative_schema_and_is_repeatable(
    tmp_path: Path,
) -> None:
    engine = create_engine_for(make_settings(tmp_path / "leadgen.sqlite3"))

    migrate_database(engine)
    migrate_database(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= EXPECTED_TABLES
    with engine.connect() as connection:
        version = connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert version == "0001"


def test_sqlite_safety_pragmas_are_enabled(tmp_path: Path) -> None:
    engine = create_engine_for(make_settings(tmp_path / "leadgen.sqlite3"))

    with engine.connect() as connection:
        foreign_keys = connection.scalar(text("PRAGMA foreign_keys"))
        journal_mode = connection.scalar(text("PRAGMA journal_mode"))
        busy_timeout = connection.scalar(text("PRAGMA busy_timeout"))

    assert foreign_keys == 1
    assert journal_mode == "wal"
    assert busy_timeout == 5000


def test_foreign_keys_and_idempotency_constraints_are_enforced(
    tmp_path: Path,
) -> None:
    engine = create_engine_for(make_settings(tmp_path / "leadgen.sqlite3"))
    migrate_database(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO runs (id, city, state, candidate_limit, status, created_at)
                VALUES ('run-1', 'Austin', 'TX', 30, 'queued', CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO jobs (
                    id, run_id, stage, status, attempt_count, max_attempts,
                    idempotency_key, created_at, updated_at
                )
                VALUES (
                    'job-1', 'run-1', 'discover', 'pending', 0, 3,
                    'run-1/discover/v1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO jobs (
                    id, run_id, stage, status, attempt_count, max_attempts,
                    idempotency_key, created_at, updated_at
                )
                VALUES (
                    'job-2', 'run-1', 'discover', 'pending', 0, 3,
                    'run-1/discover/v1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO run_candidates (
                    id, run_id, business_id, name_snapshot, created_at
                )
                VALUES (
                    'candidate-1', 'missing-run', 'missing-business',
                    'Missing', CURRENT_TIMESTAMP
                )
                """
            )
        )
