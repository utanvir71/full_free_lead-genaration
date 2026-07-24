from __future__ import annotations

import secrets
from hmac import compare_digest

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

_ALLOWED_HOSTS = {"127.0.0.1", "testserver"}


def _is_allowed_host(host: str | None) -> bool:
    if host is None:
        return False
    hostname = host.rsplit(":", maxsplit=1)[0]
    return hostname in _ALLOWED_HOSTS


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not _is_allowed_host(request.headers.get("host")):
            return PlainTextResponse("Invalid Host", status_code=400)
        new_csrf_token: str | None = None
        if request.method == "GET" and "csrf_token" not in request.cookies:
            new_csrf_token = secrets.token_urlsafe(32)
            request.state.csrf_token = new_csrf_token
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
        if new_csrf_token is not None:
            response.set_cookie(
                "csrf_token",
                new_csrf_token,
                httponly=True,
                samesite="strict",
            )
        return response


def verify_csrf(request: Request, submitted_token: str) -> None:
    cookie_token = request.cookies.get("csrf_token", "")
    if not cookie_token or not compare_digest(submitted_token, cookie_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def csrf_token_for(request: Request) -> str:
    return getattr(request.state, "csrf_token", request.cookies.get("csrf_token", ""))
