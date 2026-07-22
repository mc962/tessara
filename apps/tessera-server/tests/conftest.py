import os

# Must come before any tessera_server imports — settings are loaded at module level.
os.environ.setdefault("APP_ENV", "lcl")
os.environ.setdefault("DATABASE__KIND", "sqlite")
os.environ.setdefault("DATABASE__PATH", ":memory:")
os.environ.setdefault("SESSION_SECRET", "test-secret-do-not-use-in-prod")

from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_server.main import app
from tessera_server.data.database.dependencies import get_db_session
from tessera_server.web.dependencies.auth import (
    require_api_key,
    require_session,
    require_superuser_any,
    require_superuser_api_key,
    require_superuser_session,
)
from tessera_server.web.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    # slowapi's storage is a module-level singleton and TestClient requests
    # all share one fake client IP, so without this every rate-limited test
    # would draw from one cumulative bucket across the whole test session.
    limiter.reset()
    yield
    limiter.reset()


def make_mock_key(is_superuser: bool = True, is_active: bool = True) -> MagicMock:
    key = MagicMock()
    key.id = 1
    key.name = "test-key"
    key.key_prefix = "tsr_1234"
    key.is_superuser = is_superuser
    key.is_active = is_active
    return key


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_svg_bytes() -> bytes:
    """The tile-mark logo used to generate the site's own favicons — kept as a test fixture,
    not the served favicon itself (that lives in static/images/, already generated)."""
    path = Path(__file__).parent / "fixtures" / "tessera-mark.svg"
    return path.read_bytes()


@pytest.fixture
def api_client(mock_db: AsyncMock):
    """TestClient with DB and auth overridden."""
    mock_key = make_mock_key()

    async def _db():
        yield mock_db

    async def _auth():
        return mock_key

    async def _superuser_auth():
        return mock_key

    async def _session():
        return mock_key

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[require_api_key] = _auth
    app.dependency_overrides[require_superuser_api_key] = _superuser_auth
    app.dependency_overrides[require_superuser_any] = _superuser_auth
    app.dependency_overrides[require_session] = _session
    app.dependency_overrides[require_superuser_session] = _session

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def regular_api_client(mock_db: AsyncMock):
    """Like api_client, but the authenticated key is a non-superuser one."""
    mock_key = make_mock_key(is_superuser=False)

    async def _db():
        yield mock_db

    async def _auth():
        return mock_key

    async def _session():
        return mock_key

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[require_api_key] = _auth
    app.dependency_overrides[require_session] = _session

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(mock_db: AsyncMock):
    """TestClient with DB overridden but no auth override — tests real auth rejection."""

    async def _db():
        yield mock_db

    app.dependency_overrides[get_db_session] = _db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()
