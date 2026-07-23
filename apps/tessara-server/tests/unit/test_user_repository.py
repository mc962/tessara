"""Tests for tessara_server.data.repository.user_repository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tessara_server.data.repository import user_repository


class TestVerifyPassword:
    @pytest.mark.asyncio
    async def test_no_matching_user_returns_none(self, mock_db, monkeypatch):
        monkeypatch.setattr(
            user_repository, "get_by_email", AsyncMock(return_value=None)
        )
        result = await user_repository.verify_password(mock_db, "nobody@x.com", "pw")
        assert result is None

    @pytest.mark.asyncio
    async def test_inactive_user_returns_none(self, mock_db, monkeypatch):
        user = MagicMock(is_active=False)
        monkeypatch.setattr(
            user_repository, "get_by_email", AsyncMock(return_value=user)
        )
        result = await user_repository.verify_password(mock_db, "x@x.com", "pw")
        assert result is None

    @pytest.mark.asyncio
    async def test_wrong_password_returns_none(self, mock_db, monkeypatch):
        from tessara_server.utility.security import hash_secure_value

        user = MagicMock(is_active=True, password_hash=hash_secure_value("correct"))
        monkeypatch.setattr(
            user_repository, "get_by_email", AsyncMock(return_value=user)
        )
        result = await user_repository.verify_password(mock_db, "x@x.com", "wrong")
        assert result is None

    @pytest.mark.asyncio
    async def test_correct_password_returns_user(self, mock_db, monkeypatch):
        from tessara_server.utility.security import hash_secure_value

        user = MagicMock(is_active=True, password_hash=hash_secure_value("correct"))
        monkeypatch.setattr(
            user_repository, "get_by_email", AsyncMock(return_value=user)
        )
        result = await user_repository.verify_password(mock_db, "x@x.com", "correct")
        assert result is user


class TestGetByEmail:
    @pytest.mark.asyncio
    async def test_lowercases_and_strips_email(self, mock_db):
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: None)
        )
        result = await user_repository.get_by_email(mock_db, "  Foo@Example.com  ")
        assert result is None
        mock_db.execute.assert_awaited_once()
