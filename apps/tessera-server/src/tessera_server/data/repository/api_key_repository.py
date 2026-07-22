"""Repository for ApiKey — creation, verification, and management."""

import secrets

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from tessera_server.data.model.api_key import ApiKey
from tessera_server.utility.security import hash_secure_value, verify_secure_value

_PREFIX = "tsr_"
_KEY_BYTES = 32  # 64 hex chars


def generate_api_key() -> str:
    return _PREFIX + secrets.token_hex(_KEY_BYTES)


async def create(
    session: AsyncSession,
    name: str,
    is_superuser: bool = False,
) -> tuple[ApiKey, str]:
    """Create a new API key. Returns (model, plaintext). Plaintext is shown only once."""
    plaintext = generate_api_key()
    key_prefix = plaintext[:8]  # "tsr_" + 4 hex chars
    key_hash = hash_secure_value(plaintext)
    key = ApiKey(
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        is_superuser=is_superuser,
    )
    session.add(key)
    await session.commit()
    await session.refresh(key)
    return key, plaintext


async def verify_key(session: AsyncSession, plaintext: str) -> ApiKey | None:
    """Verify a plaintext key and return the model if valid and active."""
    if not plaintext.startswith(_PREFIX) or len(plaintext) < 8:
        return None
    key_prefix = plaintext[:8]
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.key_prefix == key_prefix, ApiKey.is_active.is_(True)
        )
    )
    key = result.scalar_one_or_none()
    if key is None or not verify_secure_value(key.key_hash, plaintext):
        return None
    return key


async def list_all(session: AsyncSession) -> list[ApiKey]:
    result = await session.execute(select(ApiKey).order_by(ApiKey.created_at))
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, key_id: int) -> ApiKey | None:
    result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
    return result.scalar_one_or_none()


async def toggle_active(session: AsyncSession, key_id: int) -> None:
    key = await get_by_id(session, key_id)
    if key:
        await session.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(is_active=not key.is_active)
        )
        await session.commit()


async def delete(session: AsyncSession, key_id: int) -> None:
    key = await get_by_id(session, key_id)
    if key:
        await session.delete(key)
        await session.commit()


async def update_last_used(session: AsyncSession, key_id: int) -> None:
    await session.execute(
        update(ApiKey).where(ApiKey.id == key_id).values(last_used_at=func.now())
    )
    await session.commit()
