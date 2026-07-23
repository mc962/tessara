"""Self-service API token management — any logged-in user manages only their own tokens.

Superuser management of *other* users' tokens lives in web/html/admin.py.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from tessara_server.configuration.settings import application_settings
from tessara_server.data.database.dependencies import DatabaseSessionDependency
from tessara_server.data.repository import api_token_repository
from tessara_server.web.csrf import verify_csrf
from tessara_server.web.dependencies.auth import SessionDependency
from tessara_server.web.templates import templates

CsrfDependency = Annotated[None, Depends(verify_csrf)]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["account"])

_CTX = {"settings": application_settings}


async def _owned_token(session, user_id: int, token_id: int):
    token = await api_token_repository.get_by_id(session, token_id)
    if not token or token.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your token")
    return token


@router.get("/tokens", response_class=HTMLResponse)
async def get_tokens(
    request: Request,
    session: DatabaseSessionDependency,
    user: SessionDependency,
) -> HTMLResponse:
    tokens = await api_token_repository.list_for_user(session, user.id)
    return templates.TemplateResponse(
        request,
        "account/tokens.html",
        {**_CTX, "tokens": tokens, "max_tokens": application_settings.max_api_tokens_per_user},
    )


@router.post("/tokens", response_class=HTMLResponse)
async def create_token(
    request: Request,
    session: DatabaseSessionDependency,
    user: SessionDependency,
    _csrf: CsrfDependency,
    name: str = Form(...),
) -> HTMLResponse:
    count = await api_token_repository.count_for_user(session, user.id)
    if count >= application_settings.max_api_tokens_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"You've reached the limit of {application_settings.max_api_tokens_per_user} API tokens.",
        )
    token, plaintext = await api_token_repository.create(session, user.id, name)
    return templates.TemplateResponse(
        request, "account/_token_created.html", {**_CTX, "token": token, "plaintext": plaintext}
    )


@router.post("/tokens/{token_id}/toggle", response_class=HTMLResponse)
async def toggle_token(
    request: Request,
    token_id: int,
    session: DatabaseSessionDependency,
    user: SessionDependency,
    _csrf: CsrfDependency,
) -> HTMLResponse:
    await _owned_token(session, user.id, token_id)
    await api_token_repository.toggle_active(session, token_id)
    token = await api_token_repository.get_by_id(session, token_id)
    return templates.TemplateResponse(request, "account/_token_row.html", {**_CTX, "token": token})


@router.post("/tokens/{token_id}/delete", response_class=HTMLResponse)
async def delete_token(
    token_id: int,
    session: DatabaseSessionDependency,
    user: SessionDependency,
    _csrf: CsrfDependency,
) -> HTMLResponse:
    await _owned_token(session, user.id, token_id)
    await api_token_repository.delete(session, token_id)
    return HTMLResponse("")
