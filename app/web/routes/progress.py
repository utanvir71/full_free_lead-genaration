from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.sql import ColumnElement, FromClause

from app.application.runs import RunNotFoundError, RunService
from app.db import schema
from app.domain.enums import JobStatus, RunStatus
from app.domain.lifecycle import InvalidRunTransition
from app.web.security import csrf_token_for, verify_csrf

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
_TERMINAL_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.COMPLETED_WITH_ERRORS,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
    RunStatus.INTERRUPTED,
}


def _progress(request: Request, run_id: str) -> dict[str, object]:
    with request.app.state.engine.connect() as connection:
        run = connection.execute(
            select(schema.runs).where(schema.runs.c.id == run_id)
        ).mappings().one_or_none()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        def count(table: FromClause, *where: ColumnElement[bool]) -> int:
            statement = select(func.count()).select_from(table)
            for clause in where:
                statement = statement.where(clause)
            return int(connection.scalar(statement) or 0)

        status = RunStatus(run["status"])
        return {
            "run_id": run_id,
            "status": status.value,
            "discovered": count(
                schema.run_candidates, schema.run_candidates.c.run_id == run_id
            ),
            "pending": count(
                schema.jobs,
                schema.jobs.c.run_id == run_id,
                schema.jobs.c.status == JobStatus.PENDING.value,
            ),
            "processing": count(
                schema.jobs,
                schema.jobs.c.run_id == run_id,
                schema.jobs.c.status == JobStatus.RUNNING.value,
            ),
            "qualified": count(
                schema.assessments,
                schema.assessments.c.run_id == run_id,
                schema.assessments.c.qualified.is_(True),
            ),
            "rejected": count(
                schema.assessments,
                schema.assessments.c.run_id == run_id,
                schema.assessments.c.qualified.is_(False),
            ),
            "drafted": count(schema.drafts, schema.drafts.c.run_id == run_id),
            "failed": count(
                schema.jobs,
                schema.jobs.c.run_id == run_id,
                schema.jobs.c.status == JobStatus.FAILED.value,
            ),
            "terminal": status in _TERMINAL_STATUSES,
        }


@router.get("/runs/{run_id}/progress")
def progress(request: Request, run_id: str) -> dict[str, object]:
    return _progress(request, run_id)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def detail(request: Request, run_id: str) -> HTMLResponse:
    progress_data = _progress(request, run_id)
    with request.app.state.engine.connect() as connection:
        run = connection.execute(
            select(schema.runs).where(schema.runs.c.id == run_id)
        ).mappings().one()
        errors = connection.execute(
            select(schema.errors)
            .where(schema.errors.c.run_id == run_id)
            .order_by(schema.errors.c.occurred_at.desc())
        ).mappings().all()
    return templates.TemplateResponse(
        request,
        "runs/detail.html",
        {
            "run": run,
            "progress": progress_data,
            "errors": errors,
            "csrf_token": csrf_token_for(request),
        },
    )


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    request: Request,
    run_id: str,
    csrf_token: str = Form(default=""),
) -> RedirectResponse:
    verify_csrf(request, csrf_token)
    service = RunService(
        request.app.state.engine,
        clock=lambda: datetime.now().astimezone(),
    )
    try:
        service.cancel(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail="Run not found") from error
    except InvalidRunTransition as error:
        raise HTTPException(
            status_code=409,
            detail="Only an active run can be cancelled",
        ) from error

    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)
