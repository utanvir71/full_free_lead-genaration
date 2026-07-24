from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.application.reviews import ReviewService
from app.domain.enums import LeadStatus
from app.web.security import verify_csrf

router = APIRouter()


def _service(request: Request) -> ReviewService:
    return ReviewService(
        request.app.state.engine, clock=lambda: datetime.now().astimezone()
    )


@router.post("/leads/{business_id}/notes")
def add_note(
    request: Request,
    business_id: str,
    body: str = Form(default=""),
    csrf_token: str = Form(default=""),
) -> RedirectResponse:
    verify_csrf(request, csrf_token)
    _service(request).add_note(business_id, body)
    return RedirectResponse(f"/leads/{business_id}", status_code=303)


@router.post("/leads/{business_id}/status")
def change_status(
    request: Request,
    business_id: str,
    status: Annotated[LeadStatus, Form()] = LeadStatus.NEW,
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse:
    verify_csrf(request, csrf_token)
    _service(request).change_status(business_id, status)
    return RedirectResponse(f"/leads/{business_id}", status_code=303)
