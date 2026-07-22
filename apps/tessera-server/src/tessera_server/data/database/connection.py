from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import Any


class DatabaseSessionManager:
    _engine: AsyncEngine | None
    _sessionmaker: async_sessionmaker[AsyncSession] | None

    def __init__(self, host: str, engine_kwargs: dict[str, Any] | None = None):
        self._engine = create_async_engine(host, **(engine_kwargs or {}))
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self) -> None:
        if self._engine is None:
            return
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")
        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def get_engine(self) -> AsyncEngine | None:
        return self._engine


_sessionmanager: DatabaseSessionManager | None = None


def get_sessionmanager() -> DatabaseSessionManager:
    global _sessionmanager
    if _sessionmanager is None:
        from tessera_server.configuration.settings import (
            application_settings,
            NullDatabaseSettings,
        )

        if isinstance(application_settings.database, NullDatabaseSettings):
            raise ValueError(
                "DATABASE__KIND must be set to 'postgres' or 'sqlite' — got 'null'."
            )
        _sessionmanager = DatabaseSessionManager(
            application_settings.database_connection_string,
            {"echo": application_settings.database.echo},
        )

        assert isinstance(_sessionmanager, DatabaseSessionManager)
    return _sessionmanager


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmanager().session() as session:
        yield session
