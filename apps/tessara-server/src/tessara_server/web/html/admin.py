"""Admin UI — user management, and per-user API token management (superuser-only).

Self-service token management for a user's *own* tokens lives in
web/html/account.py instead — this file is for a superuser managing anyone.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from tessara_server.configuration.settings import application_settings
from tessara_server.data.database.dependencies import DatabaseSessionDependency
from tessara_server.data.repository import api_token_repository, user_repository
from tessara_server.web.csrf import verify_csrf
from tessara_server.web.dependencies.auth import SuperuserSessionDependency
from tessara_server.web.templates import templates

CsrfDependency = Annotated[None, Depends(verify_csrf)]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_CTX = {"settings": application_settings}


@router.get("/users", response_class=HTMLResponse)
async def get_users(
    request: Request,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
) -> HTMLResponse:
    users = await user_repository.list_all(session)
    return templates.TemplateResponse(request, "admin/users.html", {**_CTX, "users": users})


@router.post("/users", response_class=HTMLResponse)
async def create_user(
    request: Request,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    _csrf: CsrfDependency,
    email: str = Form(...),
    password: str = Form(...),
    is_superuser: bool = Form(False),
) -> HTMLResponse:
    if await user_repository.get_by_email(session, email):
        raise HTTPException(status_code=400, detail="A user with that email already exists")
    user = await user_repository.create(
        session, email, password, is_superuser=is_superuser, is_verified=True
    )
    return templates.TemplateResponse(
        request, "admin/_user_created.html", {**_CTX, "user": user}
    )


@router.post("/users/{user_id}/toggle-active", response_class=HTMLResponse)
async def toggle_user_active(
    request: Request,
    user_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    _csrf: CsrfDependency,
) -> HTMLResponse:
    await user_repository.toggle_active(session, user_id)
    user = await user_repository.get_by_id(session, user_id)
    return templates.TemplateResponse(request, "admin/_user_row.html", {**_CTX, "user": user})


@router.post("/users/{user_id}/toggle-superuser", response_class=HTMLResponse)
async def toggle_user_superuser(
    request: Request,
    user_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    _csrf: CsrfDependency,
) -> HTMLResponse:
    await user_repository.toggle_superuser(session, user_id)
    user = await user_repository.get_by_id(session, user_id)
    return templates.TemplateResponse(request, "admin/_user_row.html", {**_CTX, "user": user})


@router.post("/users/{user_id}/delete", response_class=HTMLResponse)
async def delete_user(
    user_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    _csrf: CsrfDependency,
) -> HTMLResponse:
    await user_repository.delete(session, user_id)
    return HTMLResponse("")


@router.get("/users/{user_id}/tokens", response_class=HTMLResponse)
async def get_user_tokens(
    request: Request,
    user_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
) -> HTMLResponse:
    user = await user_repository.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tokens = await api_token_repository.list_for_user(session, user_id)
    return templates.TemplateResponse(
        request, "admin/tokens.html", {**_CTX, "target_user": user, "tokens": tokens}
    )


@router.post("/users/{user_id}/tokens", response_class=HTMLResponse)
async def create_user_token(
    request: Request,
    user_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    _csrf: CsrfDependency,
    name: str = Form(...),
) -> HTMLResponse:
    user = await user_repository.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if await api_token_repository.count_for_user(session, user_id) >= application_settings.max_api_tokens_per_user:
        raise HTTPException(status_code=400, detail="This user has reached the API token limit")
    token, plaintext = await api_token_repository.create(session, user_id, name)
    return templates.TemplateResponse(
        request, "admin/_token_created.html", {**_CTX, "token": token, "plaintext": plaintext}
    )


@router.post("/users/{user_id}/tokens/{token_id}/toggle", response_class=HTMLResponse)
async def toggle_user_token(
    request: Request,
    user_id: int,
    token_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    _csrf: CsrfDependency,
) -> HTMLResponse:
    await api_token_repository.toggle_active(session, token_id)
    token = await api_token_repository.get_by_id(session, token_id)
    return templates.TemplateResponse(request, "admin/_token_row.html", {**_CTX, "token": token})


@router.post("/users/{user_id}/tokens/{token_id}/delete", response_class=HTMLResponse)
async def delete_user_token(
    user_id: int,
    token_id: int,
    session: DatabaseSessionDependency,
    _: SuperuserSessionDependency,
    _csrf: CsrfDependency,
) -> HTMLResponse:
    await api_token_repository.delete(session, token_id)
    return HTMLResponse("")
