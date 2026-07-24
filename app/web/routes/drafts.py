from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.db import schema

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/runs/{run_id}/drafts", response_class=HTMLResponse)
def index(request: Request, run_id: str) -> HTMLResponse:
    with request.app.state.engine.connect() as connection:
        drafts = (
            connection.execute(
                select(schema.drafts, schema.businesses.c.name)
                .join(
                    schema.businesses,
                    schema.businesses.c.id == schema.drafts.c.business_id,
                )
                .where(schema.drafts.c.run_id == run_id)
                .limit(10)
            )
            .mappings()
            .all()
        )
    return templates.TemplateResponse(request, "drafts/index.html", {"drafts": drafts})


@router.get("/drafts/{draft_id}", response_class=HTMLResponse)
def detail(request: Request, draft_id: str) -> HTMLResponse:
    with request.app.state.engine.connect() as connection:
        draft = (
            connection.execute(
                select(schema.drafts).where(schema.drafts.c.id == draft_id)
            )
            .mappings()
            .one_or_none()
        )
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return templates.TemplateResponse(request, "drafts/detail.html", {"draft": draft})
