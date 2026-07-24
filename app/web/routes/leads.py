from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.db import schema
from app.web.security import csrf_token_for

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/runs/{run_id}/leads", response_class=HTMLResponse)
def index(request: Request, run_id: str) -> HTMLResponse:
    with request.app.state.engine.connect() as connection:
        rows = (
            connection.execute(
                select(schema.businesses, schema.assessments)
                .join(
                    schema.assessments,
                    schema.assessments.c.business_id == schema.businesses.c.id,
                )
                .where(schema.assessments.c.run_id == run_id)
                .order_by(
                    schema.assessments.c.qualified.desc(),
                    schema.assessments.c.total.desc(),
                )
            )
            .mappings()
            .all()
        )
    return templates.TemplateResponse(
        request, "leads/index.html", {"leads": rows, "run_id": run_id}
    )


@router.get("/leads/{business_id}", response_class=HTMLResponse)
def detail(request: Request, business_id: str) -> HTMLResponse:
    with request.app.state.engine.connect() as connection:
        business = (
            connection.execute(
                select(schema.businesses).where(schema.businesses.c.id == business_id)
            )
            .mappings()
            .one_or_none()
        )
        if business is None:
            raise HTTPException(status_code=404, detail="Lead not found")
        assessment = (
            connection.execute(
                select(schema.assessments)
                .where(schema.assessments.c.business_id == business_id)
                .order_by(schema.assessments.c.created_at.desc())
            )
            .mappings()
            .first()
        )
        facts = (
            connection.execute(
                select(schema.facts).where(schema.facts.c.business_id == business_id)
            )
            .mappings()
            .all()
        )
        contacts = (
            connection.execute(
                select(schema.contacts).where(
                    schema.contacts.c.business_id == business_id
                )
            )
            .mappings()
            .all()
        )
        people = (
            connection.execute(
                select(schema.people).where(schema.people.c.business_id == business_id)
            )
            .mappings()
            .all()
        )
        signals = (
            []
            if assessment is None
            else connection.execute(
                select(schema.score_signals).where(
                    schema.score_signals.c.assessment_id == assessment["id"]
                )
            )
            .mappings()
            .all()
        )
        pages = (
            connection.execute(
                select(schema.crawl_pages).where(
                    schema.crawl_pages.c.business_id == business_id
                )
            )
            .mappings()
            .all()
        )
        errors = (
            connection.execute(
                select(schema.errors).where(schema.errors.c.business_id == business_id)
            )
            .mappings()
            .all()
        )
        notes = (
            connection.execute(
                select(schema.notes).where(schema.notes.c.business_id == business_id)
            )
            .mappings()
            .all()
        )
    return templates.TemplateResponse(
        request,
        "leads/detail.html",
        {
            "business": business,
            "assessment": assessment,
            "facts": facts,
            "contacts": contacts,
            "people": people,
            "signals": signals,
            "pages": pages,
            "errors": errors,
            "notes": notes,
            "csrf_token": csrf_token_for(request),
        },
    )
