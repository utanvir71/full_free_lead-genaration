from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.application.runs import ActiveRunError, RunService
from app.db import schema
from app.web.security import csrf_token_for, verify_csrf

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


def _run_history(request: Request) -> list[dict[str, object]]:
    with request.app.state.engine.connect() as connection:
        rows = connection.execute(
            select(schema.runs).order_by(schema.runs.c.created_at.desc())
        ).mappings()
        return [dict(row) for row in rows]


def _render_index(
    request: Request,
    *,
    errors: list[str] | None = None,
    values: dict[str, str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "runs/index.html",
        {
            "runs": _run_history(request),
            "errors": errors or [],
            "values": values or {"city": "", "state": "", "candidate_limit": "30"},
            "csrf_token": csrf_token_for(request),
        },
        status_code=status_code,
    )


@router.get("/runs", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return _render_index(request)


@router.post("/runs", response_class=HTMLResponse, response_model=None)
def create_run(
    request: Request,
    city: str = Form(default=""),
    state: str = Form(default=""),
    candidate_limit: str = Form(default="30"),
    csrf_token: str = Form(default=""),
) -> object:
    verify_csrf(request, csrf_token)
    clean_city = city.strip()
    clean_state = state.strip().upper()
    errors: list[str] = []
    if not clean_city:
        errors.append("City is required")
    if len(clean_state) != 2 or not clean_state.isalpha():
        errors.append("State must be a two-letter code")
    try:
        limit = int(candidate_limit)
    except ValueError:
        limit = 0
    if not 1 <= limit <= 100:
        errors.append("Limit must be between 1 and 100")
    values = {
        "city": clean_city,
        "state": clean_state,
        "candidate_limit": candidate_limit,
    }
    if errors:
        return _render_index(request, errors=errors, values=values, status_code=422)

    service = RunService(
        request.app.state.engine,
        clock=lambda: datetime.now().astimezone(),
    )
    run_id = str(uuid4())
    try:
        service.start(
            run_id=run_id,
            city=clean_city,
            state=clean_state,
            candidate_limit=limit,
        )
    except ActiveRunError as error:
        return _render_index(
            request,
            errors=[str(error)],
            values=values,
            status_code=409,
        )
    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)
