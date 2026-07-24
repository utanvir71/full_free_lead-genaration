from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, insert, update
from starlette.testclient import TestClient

from app.config import Settings
from app.db import schema
from app.main import create_app


def seed_completed_run(engine: Engine, run_id: str, tmp_path: Path) -> None:
    now = datetime(2026, 7, 25, tzinfo=UTC)
    qualified = tmp_path / "qualified_leads.csv"
    rejected = tmp_path / "rejected_leads.csv"
    qualified.write_text("restaurant_name\nElm House\n")
    rejected.write_text("restaurant_name\nBudget Bites\n")
    with engine.begin() as connection:
        connection.execute(
            update(schema.runs)
            .where(schema.runs.c.id == run_id)
            .values(status="completed", finished_at=now)
        )
        connection.execute(
            insert(schema.businesses),
            [
                {
                    "id": "elm-house",
                    "name": "Elm House",
                    "lead_status": "new",
                    "website": "https://elm.example",
                    "phone": "+1 555 0100",
                    "address": "1 Elm Street, Austin, TX",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "budget-bites",
                    "name": "Budget Bites",
                    "lead_status": "new",
                    "website": None,
                    "phone": None,
                    "address": None,
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )
        connection.execute(
            insert(schema.run_candidates),
            [
                {
                    "id": "candidate-elm",
                    "run_id": run_id,
                    "business_id": "elm-house",
                    "osm_type": "node",
                    "osm_id": "1",
                    "name_snapshot": "Elm House",
                    "created_at": now,
                },
                {
                    "id": "candidate-budget",
                    "run_id": run_id,
                    "business_id": "budget-bites",
                    "osm_type": "node",
                    "osm_id": "2",
                    "name_snapshot": "Budget Bites",
                    "created_at": now,
                },
            ],
        )
        connection.execute(
            insert(schema.assessments),
            [
                {
                    "id": "assessment-elm",
                    "run_id": run_id,
                    "business_id": "elm-house",
                    "total": 6,
                    "qualified": True,
                    "scoring_version": "scoring-v1",
                    "created_at": now,
                },
                {
                    "id": "assessment-budget",
                    "run_id": run_id,
                    "business_id": "budget-bites",
                    "total": 5,
                    "qualified": False,
                    "scoring_version": "scoring-v1",
                    "created_at": now,
                },
            ],
        )
        connection.execute(
            insert(schema.facts).values(
                id="fact-events",
                run_id=run_id,
                business_id="elm-house",
                fact_type="private_dining",
                state="present",
                value_json='"Private dining"',
                source="https://elm.example/events",
                excerpt="Private dining is available for groups.",
                captured_at=now,
                extractor_version="test-v1",
                validation_state="valid",
                idempotency_key="fact-events",
            )
        )
        connection.execute(
            insert(schema.contacts).values(
                id="contact-elm",
                run_id=run_id,
                business_id="elm-house",
                kind="email",
                value="events@elm.example",
                evidence_ids_json='["fact-events"]',
                classification="business",
                syntax_state="valid",
                dns_state="valid",
                mx_state="valid",
                idempotency_key="contact-elm",
            )
        )
        connection.execute(
            insert(schema.people).values(
                id="person-elm",
                run_id=run_id,
                business_id="elm-house",
                name="Taylor Rivera",
                role="Events Manager",
                evidence_ids_json='["fact-events"]',
                idempotency_key="person-elm",
            )
        )
        connection.execute(
            insert(schema.score_signals).values(
                id="signal-elm",
                assessment_id="assessment-elm",
                signal="private_dining",
                state="awarded",
                delta=2,
                explanation="Private dining is available.",
                evidence_ids_json='["fact-events"]',
            )
        )
        connection.execute(
            insert(schema.crawl_pages).values(
                id="page-elm",
                run_id=run_id,
                business_id="elm-house",
                url="https://elm.example/events",
                robots_decision="allowed",
                status="fetched",
                http_status=200,
                content_hash="test-hash",
                fetched_at=now,
            )
        )
        connection.execute(
            insert(schema.errors).values(
                id="error-elm",
                run_id=run_id,
                business_id="elm-house",
                stage="crawl",
                code="partial_crawl",
                message="One optional page timed out.",
                retryable=False,
                occurred_at=now,
                idempotency_key="error-elm",
            )
        )
        connection.execute(
            insert(schema.drafts).values(
                id="draft-elm",
                run_id=run_id,
                business_id="elm-house",
                subject="Elm House private dining",
                body="A local-only evidence-backed draft.",
                method="fallback",
                evidence_ids_json='["fact-events"]',
                validation_state="valid",
                version="v1",
                created_at=now,
            )
        )
        connection.execute(
            insert(schema.exports),
            [
                {
                    "id": "export-qualified",
                    "run_id": run_id,
                    "kind": "qualified",
                    "file_path": str(qualified),
                    "row_count": 1,
                    "generated_at": now,
                },
                {
                    "id": "export-rejected",
                    "run_id": run_id,
                    "kind": "rejected",
                    "file_path": str(rejected),
                    "row_count": 1,
                    "generated_at": now,
                },
            ],
        )


def test_operator_can_review_a_completed_fixture_run(tmp_path: Path) -> None:
    settings = Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "db.sqlite3")})
    client = TestClient(create_app(settings))
    form = client.get("/runs")
    response = client.post(
        "/runs",
        data={
            "city": "Austin",
            "state": "TX",
            "candidate_limit": "2",
            "csrf_token": form.cookies["csrf_token"],
        },
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    run_id = response.headers["location"].rsplit("/", maxsplit=1)[-1]
    seed_completed_run(client.app.state.engine, run_id, tmp_path)

    progress = client.get(f"/runs/{run_id}")
    assert "Qualified</dt><dd>1" in progress.text
    assert "Rejected</dt><dd>1" in progress.text

    detail = client.get("/leads/elm-house")
    assert "events@elm.example" in detail.text
    assert "Taylor Rivera" in detail.text
    assert "Crawl manifest" in detail.text
    assert "One optional page timed out." in detail.text

    token = client.cookies["csrf_token"]
    note = client.post(
        "/leads/elm-house/notes",
        data={"body": "Review before outreach", "csrf_token": token},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    status = client.post(
        "/leads/elm-house/status",
        data={"status": "draft_ready", "csrf_token": token},
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )
    assert note.status_code == 303
    assert status.status_code == 303
    assert "Review before outreach" in client.get("/leads/elm-house").text

    draft = client.get(f"/runs/{run_id}/drafts")
    assert "Elm House" in draft.text
    assert "send" not in client.get("/drafts/draft-elm").text.lower()
    assert client.get(f"/runs/{run_id}/exports/qualified").text.endswith("Elm House\n")
    assert client.get(f"/runs/{run_id}/exports/rejected").text.endswith(
        "Budget Bites\n"
    )
