"""Tests for tessera_server.data.repository.api_key_repository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera_server.data.repository import api_key_repository


class TestGenerateApiKey:
    def test_has_tsr_prefix(self):
        key = api_key_repository.generate_api_key()
        assert key.startswith("tsr_")

    def test_length(self):
        key = api_key_repository.generate_api_key()
        # "tsr_" + 64 hex chars
        assert len(key) == 68

    def test_unique(self):
        assert (
            api_key_repository.generate_api_key()
            != api_key_repository.generate_api_key()
        )


class TestVerifyKey:
    @pytest.mark.asyncio
    async def test_wrong_prefix_returns_none(self, mock_db):
        result = await api_key_repository.verify_key(mock_db, "bad_notakey")
        assert result is None

    @pytest.mark.asyncio
    async def test_too_short_returns_none(self, mock_db):
        result = await api_key_repository.verify_key(mock_db, "tsr_")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_matching_prefix_returns_none(self, mock_db):
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: None)
        )
        result = await api_key_repository.verify_key(mock_db, "tsr_" + "a" * 64)
        assert result is None

    @pytest.mark.asyncio
    async def test_hash_mismatch_returns_none(self, mock_db):
        from tessera_server.utility.security import hash_secure_value
        from tessera_server.data.model.api_key import ApiKey

        key = MagicMock(spec=ApiKey)
        key.key_hash = hash_secure_value("different_secret")

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: key)
        )
        result = await api_key_repository.verify_key(mock_db, "tsr_" + "a" * 64)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_key_returns_model(self, mock_db):
        from tessera_server.utility.security import hash_secure_value
        from tessera_server.data.model.api_key import ApiKey

        plaintext = api_key_repository.generate_api_key()
        key = MagicMock(spec=ApiKey)
        key.key_hash = hash_secure_value(plaintext)

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: key)
        )
        result = await api_key_repository.verify_key(mock_db, plaintext)
        assert result is key
