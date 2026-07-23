"""Tests for /account/tokens — self-service token management for the logged-in user."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tessara_server.data.model.api_token import ApiToken


def _mock_token(id: int = 1, user_id: int = 1, name: str = "laptop") -> MagicMock:
    token = MagicMock(spec=ApiToken)
    token.id = id
    token.user_id = user_id
    token.name = name
    token.token_prefix = "tsa_1234"
    token.is_active = True
    token.last_used_at = None
    token.created_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    return token


class TestGetTokens:
    def test_no_auth_redirects_to_login(self, unauthed_client):
        resp = unauthed_client.get("/account/tokens", follow_redirects=False)
        assert resp.status_code == 303

    def test_lists_own_tokens(self, regular_api_client):
        with patch(
            "tessara_server.data.repository.api_token_repository.list_for_user",
            new=AsyncMock(return_value=[_mock_token()]),
        ):
            resp = regular_api_client.get("/account/tokens")
        assert resp.status_code == 200
        assert b"laptop" in resp.content


class TestCreateToken:
    def test_creates_token_for_self(self, regular_api_client, csrf_headers):
        with (
            patch(
                "tessara_server.data.repository.api_token_repository.count_for_user",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "tessara_server.data.repository.api_token_repository.create",
                new=AsyncMock(return_value=(_mock_token(), "tsa_plaintext")),
            ),
        ):
            resp = regular_api_client.post(
                "/account/tokens",
                data={"name": "laptop"},
                headers=csrf_headers(regular_api_client),
            )
        assert resp.status_code == 200
        assert b"tsa_plaintext" in resp.content

    def test_enforces_cap(self, regular_api_client, monkeypatch, csrf_headers):
        from tessara_server.configuration.settings import application_settings

        monkeypatch.setattr(application_settings, "max_api_tokens_per_user", 1)
        with patch(
            "tessara_server.data.repository.api_token_repository.count_for_user",
            new=AsyncMock(return_value=1),
        ):
            resp = regular_api_client.post(
                "/account/tokens",
                data={"name": "one-too-many"},
                headers=csrf_headers(regular_api_client),
            )
        assert resp.status_code == 400

    def test_missing_csrf_token_returns_403(self, regular_api_client):
        resp = regular_api_client.post("/account/tokens", data={"name": "laptop"})
        assert resp.status_code == 403


class TestToggleAndDeleteOwnership:
    def test_cannot_toggle_someone_elses_token(self, regular_api_client, csrf_headers):
        # regular_api_client's mock user has id=1; this token belongs to user 2.
        other_users_token = _mock_token(user_id=2)
        with patch(
            "tessara_server.data.repository.api_token_repository.get_by_id",
            new=AsyncMock(return_value=other_users_token),
        ):
            resp = regular_api_client.post(
                "/account/tokens/1/toggle", headers=csrf_headers(regular_api_client)
            )
        assert resp.status_code == 403

    def test_cannot_delete_someone_elses_token(self, regular_api_client, csrf_headers):
        other_users_token = _mock_token(user_id=2)
        with patch(
            "tessara_server.data.repository.api_token_repository.get_by_id",
            new=AsyncMock(return_value=other_users_token),
        ):
            resp = regular_api_client.post(
                "/account/tokens/1/delete", headers=csrf_headers(regular_api_client)
            )
        assert resp.status_code == 403

    def test_can_toggle_own_token(self, regular_api_client, csrf_headers):
        own_token = _mock_token(user_id=1)
        with (
            patch(
                "tessara_server.data.repository.api_token_repository.get_by_id",
                new=AsyncMock(return_value=own_token),
            ),
            patch(
                "tessara_server.data.repository.api_token_repository.toggle_active",
                new=AsyncMock(),
            ),
        ):
            resp = regular_api_client.post(
                "/account/tokens/1/toggle", headers=csrf_headers(regular_api_client)
            )
        assert resp.status_code == 200
