"""Tests for /api/api-keys endpoints."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tessera_server.data.model.api_key import ApiKey


def _mock_key(
    id: int = 1,
    name: str = "test",
    key_prefix: str = "tsr_1234",
    is_superuser: bool = False,
    is_active: bool = True,
) -> MagicMock:
    key = MagicMock(spec=ApiKey)
    key.id = id
    key.name = name
    key.key_prefix = key_prefix
    key.is_superuser = is_superuser
    key.is_active = is_active
    key.last_used_at = None
    key.created_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    return key


class TestListApiKeys:
    def test_no_auth_returns_401(self, unauthed_client):
        resp = unauthed_client.get("/api/api-keys")
        assert resp.status_code == 401

    def test_returns_empty_list(self, api_client):
        with patch(
            "tessera_server.data.repository.api_key_repository.list_all",
            new=AsyncMock(return_value=[]),
        ):
            resp = api_client.get("/api/api-keys")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_key_list(self, api_client):
        keys = [_mock_key(id=1, name="claude"), _mock_key(id=2, name="ci")]
        with patch(
            "tessera_server.data.repository.api_key_repository.list_all",
            new=AsyncMock(return_value=keys),
        ):
            resp = api_client.get("/api/api-keys")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["name"] == "claude"
        assert body[1]["name"] == "ci"


class TestCreateApiKey:
    def test_no_auth_returns_401(self, unauthed_client):
        resp = unauthed_client.post("/api/api-keys", json={"name": "new"})
        assert resp.status_code == 401

    def test_creates_key_returns_201(self, api_client):
        created = _mock_key(name="new-key")
        with patch(
            "tessera_server.data.repository.api_key_repository.create",
            new=AsyncMock(return_value=(created, "tsr_plaintextkey")),
        ):
            resp = api_client.post("/api/api-keys", json={"name": "new-key"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "new-key"
        assert body["key"] == "tsr_plaintextkey"

    def test_empty_name_returns_422(self, api_client):
        resp = api_client.post("/api/api-keys", json={"name": ""})
        assert resp.status_code == 422

    def test_missing_name_returns_422(self, api_client):
        resp = api_client.post("/api/api-keys", json={})
        assert resp.status_code == 422


class TestToggleApiKey:
    def test_key_not_found_returns_404(self, api_client):
        with patch(
            "tessera_server.data.repository.api_key_repository.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            resp = api_client.patch("/api/api-keys/99/toggle")
        assert resp.status_code == 404

    def test_toggles_and_returns_key(self, api_client):
        key = _mock_key(is_active=True)
        with (
            patch(
                "tessera_server.data.repository.api_key_repository.get_by_id",
                new=AsyncMock(return_value=key),
            ),
            patch(
                "tessera_server.data.repository.api_key_repository.toggle_active",
                new=AsyncMock(),
            ),
        ):
            resp = api_client.patch("/api/api-keys/1/toggle")
        assert resp.status_code == 200


class TestDeleteApiKey:
    def test_key_not_found_returns_404(self, api_client):
        with patch(
            "tessera_server.data.repository.api_key_repository.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            resp = api_client.delete("/api/api-keys/99")
        assert resp.status_code == 404

    def test_deletes_key_returns_204(self, api_client):
        key = _mock_key()
        with (
            patch(
                "tessera_server.data.repository.api_key_repository.get_by_id",
                new=AsyncMock(return_value=key),
            ),
            patch(
                "tessera_server.data.repository.api_key_repository.delete",
                new=AsyncMock(),
            ),
        ):
            resp = api_client.delete("/api/api-keys/1")
        assert resp.status_code == 204
