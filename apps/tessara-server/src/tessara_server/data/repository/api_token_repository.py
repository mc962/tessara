"""Repository for ApiToken — creation, verification, and management."""

import secrets

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from tessara_server.data.model.api_token import ApiToken
from tessara_server.utility.security import hash_secure_value, verify_secure_value

_PREFIX = "tsa_"
_TOKEN_BYTES = 32  # 64 hex chars


def generate_api_token() -> str:
    return _PREFIX + secrets.token_hex(_TOKEN_BYTES)


async def create(session: AsyncSession, user_id: int, name: str) -> tuple[ApiToken, str]:
    """Create a new API token for a user. Returns (model, plaintext) — plaintext is shown once."""
    plaintext = generate_api_token()
    token_prefix = plaintext[:8]  # "tsa_" + 4 hex chars
    token_hash = hash_secure_value(plaintext)
    token = ApiToken(
        user_id=user_id,
        name=name,
        token_prefix=token_prefix,
        token_hash=token_hash,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token, plaintext


async def verify_token(session: AsyncSession, plaintext: str) -> ApiToken | None:
    """Verify a plaintext token and return the model (with .user loaded) if valid and active."""
    if not plaintext.startswith(_PREFIX) or len(plaintext) < 8:
        return None
    token_prefix = plaintext[:8]
    result = await session.execute(
        select(ApiToken)
        .options(selectinload(ApiToken.user))
        .where(ApiToken.token_prefix == token_prefix, ApiToken.is_active.is_(True))
    )
    token = result.scalar_one_or_none()
    if token is None or not verify_secure_value(token.token_hash, plaintext):
        return None
    if not token.user.is_active:
        return None
    return token


async def list_for_user(session: AsyncSession, user_id: int) -> list[ApiToken]:
    result = await session.execute(
        select(ApiToken)
        .where(ApiToken.user_id == user_id)
        .order_by(ApiToken.created_at)
    )
    return list(result.scalars().all())


async def count_for_user(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(ApiToken).where(ApiToken.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_by_id(session: AsyncSession, token_id: int) -> ApiToken | None:
    result = await session.execute(
        select(ApiToken)
        .options(selectinload(ApiToken.user))
        .where(ApiToken.id == token_id)
    )
    return result.scalar_one_or_none()


async def toggle_active(session: AsyncSession, token_id: int) -> None:
    token = await get_by_id(session, token_id)
    if token:
        await session.execute(
            update(ApiToken)
            .where(ApiToken.id == token_id)
            .values(is_active=not token.is_active)
        )
        await session.commit()


async def delete(session: AsyncSession, token_id: int) -> None:
    token = await get_by_id(session, token_id)
    if token:
        await session.delete(token)
        await session.commit()


async def update_last_used(session: AsyncSession, token_id: int) -> None:
    await session.execute(
        update(ApiToken).where(ApiToken.id == token_id).values(last_used_at=func.now())
    )
    await session.commit()
