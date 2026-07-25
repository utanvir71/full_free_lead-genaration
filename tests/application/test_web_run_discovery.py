from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.adapters.overpass.client import DiscoveryRequest
from app.adapters.overpass.errors import OverpassRetryExhausted
from app.adapters.overpass.parser import Candidate
from app.application.runs import RunService
from app.application.web_run_discovery import WebRunDiscovery
from app.config import Settings
from app.db import schema
from app.db.session import create_engine_for, migrate_database
from app.domain.enums import RunStatus

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


class FakeProvider:
    def __init__(self, candidates: list[Candidate]) -> None:
        self._candidates = candidates
        self.requests: list[DiscoveryRequest] = []

    def discover(self, request: DiscoveryRequest) -> list[Candidate]:
        self.requests.append(request)
        return self._candidates


class FailingProvider:
    def discover(self, request: DiscoveryRequest) -> list[Candidate]:
        del request
        raise RuntimeError("provider unavailable")


class BusyProvider:
    def discover(self, request: DiscoveryRequest) -> list[Candidate]:
        del request
        raise OverpassRetryExhausted("Overpass returned retryable status 504")


def make_running_engine(tmp_path: Path):
    settings = Settings.load(
        {"LEADGEN_DATABASE_PATH": str(tmp_path / "leadgen.sqlite3")}
    )
    engine = create_engine_for(settings)
    migrate_database(engine)
    RunService(engine, clock=lambda: NOW).start(
        run_id="run-1", city="Austin", state="TX", candidate_limit=3
    )
    return engine


def candidate() -> Candidate:
    return Candidate(
        osm_type="node",
        osm_id=101,
        latitude=30.2672,
        longitude=-97.7431,
        tags={"name": "Northstar Grill", "amenity": "restaurant"},
    )


def run_status(engine) -> str:
    with engine.connect() as connection:
        return str(
            connection.scalar(
                select(schema.runs.c.status).where(schema.runs.c.id == "run-1")
            )
        )


def candidate_count(engine) -> int:
    with engine.connect() as connection:
        return len(
            connection.execute(
                select(schema.run_candidates.c.id).where(
                    schema.run_candidates.c.run_id == "run-1"
                )
            ).all()
        )


def test_execute_reconciles_candidates_and_completes_a_running_run(
    tmp_path: Path,
) -> None:
    engine = make_running_engine(tmp_path)
    provider = FakeProvider([candidate()])

    WebRunDiscovery(engine, provider=provider, clock=lambda: NOW).execute("run-1")

    assert provider.requests == [
        DiscoveryRequest(run_id="run-1", city="Austin", state="TX", limit=3)
    ]
    assert run_status(engine) == RunStatus.COMPLETED.value
    assert candidate_count(engine) == 1


def test_execute_records_failure_and_marks_run_failed(tmp_path: Path) -> None:
    engine = make_running_engine(tmp_path)

    WebRunDiscovery(engine, provider=FailingProvider(), clock=lambda: NOW).execute(
        "run-1"
    )

    assert run_status(engine) == RunStatus.FAILED.value
    with engine.connect() as connection:
        error_codes = connection.scalars(
            select(schema.errors.c.code).where(schema.errors.c.run_id == "run-1")
        ).all()
    assert error_codes == ["discovery_failed"]


def test_execute_explains_when_the_public_overpass_server_is_busy(
    tmp_path: Path,
) -> None:
    engine = make_running_engine(tmp_path)

    WebRunDiscovery(engine, provider=BusyProvider(), clock=lambda: NOW).execute(
        "run-1"
    )

    with engine.connect() as connection:
        message = connection.scalar(
            select(schema.errors.c.message).where(schema.errors.c.run_id == "run-1")
        )
    assert message == "OpenStreetMap is busy or timed out. Please try again later."
