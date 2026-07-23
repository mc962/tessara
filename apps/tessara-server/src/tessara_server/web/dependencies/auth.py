"""FastAPI dependencies for Bearer API-token and session (cookie) authentication."""

import logging
from typing import Annotated

from fastapi import BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from tessara_server.configuration.settings import application_settings
from tessara_server.data.database.dependencies import DatabaseSessionDependency
from tessara_server.data.model.user import User
from tessara_server.data.repository import api_token_repository, user_repository
from tessara_server.web.dependencies.tokens import password_nonce

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


class AdminLoginRequired(Exception):
    """Raised by session dependencies on login-required routes — triggers a login redirect."""


_SESSION_COOKIE = "tessara_session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        application_settings.session_secret.get_secret_value()
    )


async def _update_last_used_bg(session: AsyncSession, token_id: int) -> None:
    try:
        await api_token_repository.update_last_used(session, token_id)
    except Exception:
        pass


async def require_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DatabaseSessionDependency,
    background_tasks: BackgroundTasks,
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing API token")
    token = await api_token_repository.verify_token(session, credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or inactive API token")
    background_tasks.add_task(_update_last_used_bg, session, token.id)
    return token.user


async def require_superuser_bearer_token(
    user: Annotated[User, Depends(require_bearer_token)],
) -> User:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")
    return user


async def require_session(
    request: Request,
    session: DatabaseSessionDependency,
) -> User:
    """Any active, logged-in user's session — used by browser-facing pages that aren't admin-only, like /generate."""
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        raise AdminLoginRequired()
    try:
        data = _serializer().loads(token, max_age=application_settings.session_max_age)
        user_id = data["id"]
        nonce = data["pwn"]
    except (BadSignature, SignatureExpired, KeyError):
        raise AdminLoginRequired()
    user = await user_repository.get_by_id(session, user_id)
    if not user or not user.is_active or password_nonce(user) != nonce:
        raise AdminLoginRequired()
    return user


async def require_superuser_session(
    user: Annotated[User, Depends(require_session)],
) -> User:
    if not user.is_superuser:
        raise AdminLoginRequired()
    return user


async def get_optional_session(
    request: Request,
    session: DatabaseSessionDependency,
) -> "User | None":
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=application_settings.session_max_age)
        user_id = data["id"]
        nonce = data["pwn"]
    except (BadSignature, SignatureExpired, KeyError):
        return None
    user = await user_repository.get_by_id(session, user_id)
    if not user or not user.is_active or password_nonce(user) != nonce:
        return None
    return user


def make_session_cookie(user: User) -> str:
    return _serializer().dumps({"id": user.id, "pwn": password_nonce(user)})


async def require_superuser_any(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DatabaseSessionDependency,
    background_tasks: BackgroundTasks,
) -> User:
    """Accept either a session cookie (admin UI) or a superuser Bearer token (API)."""
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        try:
            data = _serializer().loads(
                token, max_age=application_settings.session_max_age
            )
            user_id = data["id"]
            nonce = data["pwn"]
        except (BadSignature, SignatureExpired, KeyError):
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        user = await user_repository.get_by_id(session, user_id)
        if not user or not user.is_active or password_nonce(user) != nonce or not user.is_superuser:
            raise HTTPException(status_code=403, detail="Superuser access required")
        return user

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing API token")
    api_token = await api_token_repository.verify_token(session, credentials.credentials)
    if not api_token:
        raise HTTPException(status_code=401, detail="Invalid or inactive API token")
    if not api_token.user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")
    background_tasks.add_task(_update_last_used_bg, session, api_token.id)
    return api_token.user


BearerUserDependency = Annotated[User, Depends(require_bearer_token)]
SuperuserBearerUserDependency = Annotated[User, Depends(require_superuser_bearer_token)]
SessionDependency = Annotated[User, Depends(require_session)]
SuperuserSessionDependency = Annotated[User, Depends(require_superuser_session)]
SuperuserAnyDependency = Annotated[User, Depends(require_superuser_any)]
OptionalSessionDependency = Annotated["User | None", Depends(get_optional_session)]
