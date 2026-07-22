"""FastAPI dependencies for API key and session authentication."""

import logging
from typing import Annotated

from fastapi import BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_server.configuration.settings import application_settings
from tessera_server.data.database.dependencies import DatabaseSessionDependency
from tessera_server.data.model.api_key import ApiKey
from tessera_server.data.repository import api_key_repository

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


class AdminLoginRequired(Exception):
    """Raised by session dependencies on admin routes — triggers a login redirect."""


_SESSION_COOKIE = "tessera_session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        application_settings.session_secret.get_secret_value()
    )


async def _update_last_used_bg(session: AsyncSession, key_id: int) -> None:
    try:
        await api_key_repository.update_last_used(session, key_id)
    except Exception:
        pass


async def require_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DatabaseSessionDependency,
    background_tasks: BackgroundTasks,
) -> ApiKey:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing API key")
    key = await api_key_repository.verify_key(session, credentials.credentials)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    background_tasks.add_task(_update_last_used_bg, session, key.id)
    return key


async def require_superuser_api_key(
    key: Annotated[ApiKey, Depends(require_api_key)],
) -> ApiKey:
    if not key.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser key required")
    return key


async def require_session(
    request: Request,
    session: DatabaseSessionDependency,
) -> ApiKey:
    """Any active key's session — used by browser-facing pages that aren't admin-only, like /generate."""
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        raise AdminLoginRequired()
    try:
        data = _serializer().loads(token, max_age=application_settings.session_max_age)
        key_id = data["id"]
    except (BadSignature, SignatureExpired, KeyError):
        raise AdminLoginRequired()
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or not key.is_active:
        raise AdminLoginRequired()
    return key


async def require_superuser_session(
    key: Annotated[ApiKey, Depends(require_session)],
) -> ApiKey:
    if not key.is_superuser:
        raise AdminLoginRequired()
    return key


async def get_optional_session(
    request: Request,
    session: DatabaseSessionDependency,
) -> "ApiKey | None":
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=application_settings.session_max_age)
        key_id = data["id"]
    except (BadSignature, SignatureExpired, KeyError):
        return None
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or not key.is_active:
        return None
    return key


def make_session_cookie(key_id: int) -> str:
    return _serializer().dumps({"id": key_id})


async def require_superuser_any(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DatabaseSessionDependency,
    background_tasks: BackgroundTasks,
) -> ApiKey:
    """Accept either a session cookie (admin UI) or a superuser Bearer token (API)."""
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        try:
            data = _serializer().loads(
                token, max_age=application_settings.session_max_age
            )
            key_id = data["id"]
        except (BadSignature, SignatureExpired, KeyError):
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        key = await api_key_repository.get_by_id(session, key_id)
        if not key or not key.is_active or not key.is_superuser:
            raise HTTPException(status_code=403, detail="Superuser access required")
        return key

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing API key")
    key = await api_key_repository.verify_key(session, credentials.credentials)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    if not key.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser key required")
    background_tasks.add_task(_update_last_used_bg, session, key.id)
    return key


ApiKeyDependency = Annotated[ApiKey, Depends(require_api_key)]
SuperuserApiKeyDependency = Annotated[ApiKey, Depends(require_superuser_api_key)]
SessionDependency = Annotated[ApiKey, Depends(require_session)]
SuperuserSessionDependency = Annotated[ApiKey, Depends(require_superuser_session)]
SuperuserAnyDependency = Annotated[ApiKey, Depends(require_superuser_any)]
OptionalSessionDependency = Annotated["ApiKey | None", Depends(get_optional_session)]
