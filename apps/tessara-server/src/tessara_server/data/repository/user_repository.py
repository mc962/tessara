"""Repository for User — creation, password verification, and management."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessara_server.data.model.user import User
from tessara_server.utility.security import hash_secure_value, verify_secure_value


async def create(
    session: AsyncSession,
    email: str,
    password: str,
    *,
    is_superuser: bool = False,
    is_verified: bool = False,
) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=hash_secure_value(password),
        is_superuser=is_superuser,
        is_verified=is_verified,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(User.email == email.strip().lower())
    )
    return result.scalar_one_or_none()


async def verify_password(session: AsyncSession, email: str, password: str) -> User | None:
    """Verify an email/password pair and return the user if valid and active."""
    user = await get_by_email(session, email)
    if user is None or not user.is_active:
        return None
    if not verify_secure_value(user.password_hash, password):
        return None
    return user


async def list_all(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def set_verified(session: AsyncSession, user_id: int) -> None:
    await session.execute(update(User).where(User.id == user_id).values(is_verified=True))
    await session.commit()


async def set_password(session: AsyncSession, user_id: int, new_password: str) -> None:
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=hash_secure_value(new_password))
    )
    await session.commit()


async def toggle_active(session: AsyncSession, user_id: int) -> None:
    user = await get_by_id(session, user_id)
    if user:
        await session.execute(
            update(User).where(User.id == user_id).values(is_active=not user.is_active)
        )
        await session.commit()


async def toggle_superuser(session: AsyncSession, user_id: int) -> None:
    user = await get_by_id(session, user_id)
    if user:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_superuser=not user.is_superuser)
        )
        await session.commit()


async def delete(session: AsyncSession, user_id: int) -> None:
    user = await get_by_id(session, user_id)
    if user:
        await session.delete(user)
        await session.commit()
