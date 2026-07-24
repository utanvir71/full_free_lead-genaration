from pathlib import Path

from starlette.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    settings = Settings.load(
        {"LEADGEN_DATABASE_PATH": str(tmp_path / "leadgen.sqlite3")}
    )
    return TestClient(create_app(settings))


def test_runs_dashboard_renders_local_form_and_security_headers(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/runs")

    assert response.status_code == 200
    assert 'action="/runs"' in response.text
    assert 'name="candidate_limit"' in response.text
    assert 'value="30"' in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert f'value="{response.cookies["csrf_token"]}"' in response.text


def test_runs_reject_invalid_input_without_creating_a_run(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    form = client.get("/runs")

    response = client.post(
        "/runs",
        data={
            "city": "",
            "state": "California",
            "candidate_limit": "101",
            "csrf_token": form.cookies.get("csrf_token", ""),
        },
        headers={"Origin": "http://testserver"},
    )

    assert response.status_code == 422
    assert "City is required" in response.text
    assert "State must be a two-letter code" in response.text
    assert "Limit must be between 1 and 100" in response.text
    assert "No runs yet" in response.text


def test_runs_creates_a_persisted_run_with_valid_csrf_and_origin(
    tmp_path: Path,
) -> None:
    client = make_client(tmp_path)
    form = client.get("/runs")

    response = client.post(
        "/runs",
        data={
            "city": "Austin",
            "state": "tx",
            "candidate_limit": "30",
            "csrf_token": form.cookies["csrf_token"],
        },
        headers={"Origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/runs/")
    assert "Austin, TX" in client.get("/runs").text


def test_runs_rejects_cross_origin_or_missing_csrf(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/runs",
        data={"city": "Austin", "state": "TX", "candidate_limit": "30"},
        headers={"Origin": "https://example.invalid"},
    )

    assert response.status_code == 403


def test_runs_rejects_an_untrusted_host_even_when_origin_matches(
    tmp_path: Path,
) -> None:
    client = make_client(tmp_path)
    response = client.get("/runs", headers={"Host": "evil.invalid"})
    token = response.cookies.get("csrf_token", "")

    rejected = client.post(
        "/runs",
        data={
            "city": "Austin",
            "state": "TX",
            "candidate_limit": "30",
            "csrf_token": token,
        },
        headers={"Host": "evil.invalid", "Origin": "http://evil.invalid"},
    )

    assert rejected.status_code == 400


def test_runs_serves_local_styles_without_a_cdn(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/static/app.css")

    assert response.status_code == 200
    assert "system-ui" in response.text
