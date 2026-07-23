"""Tests for /api/api-tokens endpoints."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tessara_server.data.model.api_token import ApiToken


def _mock_token(
    id: int = 1,
    user_id: int = 1,
    name: str = "test",
    token_prefix: str = "tsa_1234",
    is_active: bool = True,
) -> MagicMock:
    token = MagicMock(spec=ApiToken)
    token.id = id
    token.user_id = user_id
    token.name = name
    token.token_prefix = token_prefix
    token.is_active = is_active
    token.last_used_at = None
    token.created_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    return token


class TestListApiTokens:
    def test_no_auth_returns_401(self, unauthed_client):
        resp = unauthed_client.get("/api/api-tokens", params={"user_id": 1})
        assert resp.status_code == 401

    def test_returns_empty_list(self, api_client):
        with patch(
            "tessara_server.data.repository.api_token_repository.list_for_user",
            new=AsyncMock(return_value=[]),
        ):
            resp = api_client.get("/api/api-tokens", params={"user_id": 1})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_token_list(self, api_client):
        toks = [_mock_token(id=1, name="claude"), _mock_token(id=2, name="ci")]
        with patch(
            "tessara_server.data.repository.api_token_repository.list_for_user",
            new=AsyncMock(return_value=toks),
        ):
            resp = api_client.get("/api/api-tokens", params={"user_id": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["name"] == "claude"
        assert body[1]["name"] == "ci"


class TestCreateApiToken:
    def test_no_auth_returns_401(self, unauthed_client):
        resp = unauthed_client.post("/api/api-tokens", json={"user_id": 1, "name": "new"})
        assert resp.status_code == 401

    def test_creates_token_returns_201(self, api_client):
        created = _mock_token(name="new-token")
        with patch(
            "tessara_server.data.repository.api_token_repository.create",
            new=AsyncMock(return_value=(created, "tsa_plaintexttoken")),
        ):
            resp = api_client.post("/api/api-tokens", json={"user_id": 1, "name": "new-token"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "new-token"
        assert body["token"] == "tsa_plaintexttoken"

    def test_empty_name_returns_422(self, api_client):
        resp = api_client.post("/api/api-tokens", json={"user_id": 1, "name": ""})
        assert resp.status_code == 422

    def test_missing_fields_returns_422(self, api_client):
        resp = api_client.post("/api/api-tokens", json={})
        assert resp.status_code == 422


class TestToggleApiToken:
    def test_token_not_found_returns_404(self, api_client):
        with patch(
            "tessara_server.data.repository.api_token_repository.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            resp = api_client.patch("/api/api-tokens/99/toggle")
        assert resp.status_code == 404

    def test_toggles_and_returns_token(self, api_client):
        token = _mock_token(is_active=True)
        with (
            patch(
                "tessara_server.data.repository.api_token_repository.get_by_id",
                new=AsyncMock(return_value=token),
            ),
            patch(
                "tessara_server.data.repository.api_token_repository.toggle_active",
                new=AsyncMock(),
            ),
        ):
            resp = api_client.patch("/api/api-tokens/1/toggle")
        assert resp.status_code == 200


class TestDeleteApiToken:
    def test_token_not_found_returns_404(self, api_client):
        with patch(
            "tessara_server.data.repository.api_token_repository.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            resp = api_client.delete("/api/api-tokens/99")
        assert resp.status_code == 404

    def test_deletes_token_returns_204(self, api_client):
        token = _mock_token()
        with (
            patch(
                "tessara_server.data.repository.api_token_repository.get_by_id",
                new=AsyncMock(return_value=token),
            ),
            patch(
                "tessara_server.data.repository.api_token_repository.delete",
                new=AsyncMock(),
            ),
        ):
            resp = api_client.delete("/api/api-tokens/1")
        assert resp.status_code == 204
