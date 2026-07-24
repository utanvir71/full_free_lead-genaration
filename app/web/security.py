from __future__ import annotations

import secrets
from hmac import compare_digest

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            host = request.headers.get("host")
            if origin != f"http://{host}":
                return PlainTextResponse("Forbidden", status_code=403)

        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.method == "GET" and "csrf_token" not in request.cookies:
            response.set_cookie(
                "csrf_token",
                secrets.token_urlsafe(32),
                httponly=True,
                samesite="strict",
            )
        return response


def verify_csrf(request: Request, submitted_token: str) -> None:
    cookie_token = request.cookies.get("csrf_token", "")
    if not cookie_token or not compare_digest(submitted_token, cookie_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
