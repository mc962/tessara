"""Tests for tessara_server.data.repository.api_token_repository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tessara_server.data.repository import api_token_repository


class TestGenerateApiToken:
    def test_has_tsa_prefix(self):
        token = api_token_repository.generate_api_token()
        assert token.startswith("tsa_")

    def test_length(self):
        token = api_token_repository.generate_api_token()
        # "tsa_" + 64 hex chars
        assert len(token) == 68

    def test_unique(self):
        assert (
            api_token_repository.generate_api_token()
            != api_token_repository.generate_api_token()
        )


class TestVerifyToken:
    @pytest.mark.asyncio
    async def test_wrong_prefix_returns_none(self, mock_db):
        result = await api_token_repository.verify_token(mock_db, "bad_notatoken")
        assert result is None

    @pytest.mark.asyncio
    async def test_too_short_returns_none(self, mock_db):
        result = await api_token_repository.verify_token(mock_db, "tsa_")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_matching_prefix_returns_none(self, mock_db):
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: None)
        )
        result = await api_token_repository.verify_token(mock_db, "tsa_" + "a" * 64)
        assert result is None

    @pytest.mark.asyncio
    async def test_hash_mismatch_returns_none(self, mock_db):
        from tessara_server.utility.security import hash_secure_value

        token = MagicMock()
        token.token_hash = hash_secure_value("different_secret")

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: token)
        )
        result = await api_token_repository.verify_token(mock_db, "tsa_" + "a" * 64)
        assert result is None

    @pytest.mark.asyncio
    async def test_inactive_user_returns_none(self, mock_db):
        from tessara_server.utility.security import hash_secure_value

        plaintext = api_token_repository.generate_api_token()
        token = MagicMock()
        token.token_hash = hash_secure_value(plaintext)
        token.user = MagicMock(is_active=False)

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: token)
        )
        result = await api_token_repository.verify_token(mock_db, plaintext)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_model(self, mock_db):
        from tessara_server.utility.security import hash_secure_value

        plaintext = api_token_repository.generate_api_token()
        token = MagicMock()
        token.token_hash = hash_secure_value(plaintext)
        token.user = MagicMock(is_active=True)

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: token)
        )
        result = await api_token_repository.verify_token(mock_db, plaintext)
        assert result is token
