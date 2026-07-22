"""Admin UI — API key management."""

import logging
from typing import Union

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from tessara_server.configuration.settings import application_settings
from tessara_server.data.database.dependencies import DatabaseSessionDependency
from tessara_server.data.repository import api_key_repository
from tessara_server.web.dependencies.auth import (
    SuperuserSessionDependency,
    _SESSION_COOKIE,
    make_session_cookie,
)
from tessara_server.web.rate_limit import limiter
from tessara_server.web.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

_CTX = {"settings": application_settings}


def _safe_next(next_path: str | None) -> str:
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    # Not /admin/api-keys — that's superuser-only and a non-superuser key
    # would just bounce straight back to the login page.
    return "/generate"


@router.get("/admin/login", response_class=HTMLResponse)
async def get_login(
    request: Request, error: str | None = None, next: str | None = None
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "admin/login.html", {**_CTX, "error": error, "next": next}
    )


@router.post("/admin/login", response_model=None)
@limiter.limit(application_settings.rate_limit_login)
async def post_login(
    request: Request,
    session: DatabaseSessionDependency,
    api_key: str = Form(...),
    next: str = Form(""),
) -> Union[HTMLResponse, RedirectResponse]:
    key = await api_key_repository.verify_key(session, api_key)
    if not key:
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {**_CTX, "error": "Invalid or inactive API key", "next": next},
            status_code=401,
        )
    token = make_session_cookie(key.id)
    response = RedirectResponse(_safe_next(next), status_code=303)
    response.set_cookie(
        _SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=application_settings.session_max_age,
    )
    return response


@router.post("/admin/logout")
async def post_logout() -> RedirectResponse:
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(_SESSION_COOKIE)
    return response


@router.get("/admin/api-keys", response_class=HTMLResponse)
async def get_api_keys(
    request: Request,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
) -> HTMLResponse:
    keys = await api_key_repository.list_all(session)
    return templates.TemplateResponse(
        request,
        "admin/api_keys.html",
        {
            **_CTX,
            "keys": keys,
        },
    )


@router.post("/admin/api-keys", response_class=HTMLResponse)
async def create_api_key(
    request: Request,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    name: str = Form(...),
    is_superuser: bool = Form(False),
) -> HTMLResponse:
    key, plaintext = await api_key_repository.create(session, name, is_superuser=is_superuser)
    return templates.TemplateResponse(
        request,
        "admin/_key_created.html",
        {**_CTX, "key": key, "plaintext": plaintext},
    )


@router.post("/admin/api-keys/{key_id}/toggle", response_class=HTMLResponse)
async def toggle_api_key(
    request: Request,
    key_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
) -> HTMLResponse:
    await api_key_repository.toggle_active(session, key_id)
    key = await api_key_repository.get_by_id(session, key_id)
    return templates.TemplateResponse(request, "admin/_key_row.html", {**_CTX, "key": key})


@router.post("/admin/api-keys/{key_id}/delete", response_class=HTMLResponse)
async def delete_api_key(
    key_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
) -> HTMLResponse:
    await api_key_repository.delete(session, key_id)
    return HTMLResponse("")
