"""CSRF protection for cookie-authenticated HTML routes — double-submit cookie pattern.

A random token lives in a cookie (HttpOnly, so cross-site JS can't read it)
and is echoed into every rendered page via `request.state.csrf_token`
(exposed to Jinja automatically, since fastapi's `TemplateResponse` already
puts `request` in template context). Forms embed it as a hidden field;
htmx requests get it via a global `X-CSRF-Token` header (see base.html) since
its buttons post no form body. A POST is only accepted if the submitted
value matches the cookie — a cross-site forger can trigger the cookie to be
attached automatically but has no way to read its value to also submit it.

Only applies to form-encoded/multipart POSTs (i.e. real HTML forms) — Bearer
requests carry no ambient credential and are exempt by definition, and JSON
bodies can't be sent cross-origin without a CORS preflight this app doesn't
allow.
"""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

CSRF_COOKIE_NAME = "tessara_csrf"
CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

_FORM_CONTENT_TYPES = ("application/x-www-form-urlencoded", "multipart/form-data")


def _generate_token() -> str:
    return secrets.token_hex(32)


class CsrfCookieMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a CSRF cookie and exposes its value as
    `request.state.csrf_token` for templates to embed — runs for all
    requests so any page can render a protected form without a route
    remembering to depend on anything."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = request.cookies.get(CSRF_COOKIE_NAME) or _generate_token()
        request.state.csrf_token = token

        response = await call_next(request)

        if request.cookies.get(CSRF_COOKIE_NAME) != token:
            response.set_cookie(
                CSRF_COOKIE_NAME,
                token,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
            )
        return response


async def verify_csrf(
    request: Request,
    csrf_header: Annotated[str | None, Header(alias=CSRF_HEADER_NAME)] = None,
) -> None:
    """Dependency for cookie-session-authenticated POST routes."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)

    form_token = None
    content_type = request.headers.get("content-type", "")
    if content_type.startswith(_FORM_CONTENT_TYPES):
        form = await request.form()
        value = form.get(CSRF_FIELD_NAME)
        form_token = value if isinstance(value, str) else None

    submitted = csrf_header or form_token
    if not cookie_token or not submitted or not secrets.compare_digest(cookie_token, submitted):
        raise HTTPException(status_code=403, detail="Your session expired — please retry.")
