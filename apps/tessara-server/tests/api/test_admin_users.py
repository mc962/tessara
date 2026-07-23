"""Tests for /admin/users and /admin/users/{id}/tokens — superuser-only."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tessara_server.data.model.api_token import ApiToken
from tessara_server.data.model.user import User


def _mock_user(id: int = 2, email: str = "someone@x.com", is_superuser: bool = False) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = id
    user.email = email
    user.is_superuser = is_superuser
    user.is_active = True
    user.is_verified = True
    user.created_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    return user


def _mock_token(id: int = 1, user_id: int = 2, name: str = "tok") -> MagicMock:
    token = MagicMock(spec=ApiToken)
    token.id = id
    token.user_id = user_id
    token.name = name
    token.token_prefix = "tsa_1234"
    token.is_active = True
    token.last_used_at = None
    token.created_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    return token


class TestGetUsers:
    def test_regular_user_forbidden(self, regular_api_client):
        resp = regular_api_client.get("/admin/users", follow_redirects=False)
        assert resp.status_code == 303  # AdminLoginRequired -> redirect

    def test_superuser_can_list(self, api_client):
        with patch(
            "tessara_server.data.repository.user_repository.list_all",
            new=AsyncMock(return_value=[_mock_user()]),
        ):
            resp = api_client.get("/admin/users")
        assert resp.status_code == 200
        assert b"someone@x.com" in resp.content


class TestCreateUser:
    def test_creates_pre_verified_user(self, api_client, csrf_headers):
        with (
            patch(
                "tessara_server.data.repository.user_repository.get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "tessara_server.data.repository.user_repository.create",
                new=AsyncMock(return_value=_mock_user()),
            ) as create,
        ):
            resp = api_client.post(
                "/admin/users",
                data={"email": "someone@x.com", "password": "longenough"},
                headers=csrf_headers(api_client),
            )
        assert resp.status_code == 200
        create.assert_awaited_once()
        assert create.await_args.kwargs["is_verified"] is True

    def test_duplicate_email_returns_400(self, api_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.get_by_email",
            new=AsyncMock(return_value=_mock_user()),
        ):
            resp = api_client.post(
                "/admin/users",
                data={"email": "someone@x.com", "password": "longenough"},
                headers=csrf_headers(api_client),
            )
        assert resp.status_code == 400

    def test_missing_csrf_token_returns_403(self, api_client):
        resp = api_client.post(
            "/admin/users", data={"email": "someone@x.com", "password": "longenough"}
        )
        assert resp.status_code == 403


class TestUserTokens:
    def test_lists_only_that_users_tokens(self, api_client):
        with (
            patch(
                "tessara_server.data.repository.user_repository.get_by_id",
                new=AsyncMock(return_value=_mock_user()),
            ),
            patch(
                "tessara_server.data.repository.api_token_repository.list_for_user",
                new=AsyncMock(return_value=[_mock_token()]),
            ),
        ):
            resp = api_client.get("/admin/users/2/tokens")
        assert resp.status_code == 200
        assert b"tok" in resp.content

    def test_create_token_enforces_cap(self, api_client, monkeypatch, csrf_headers):
        from tessara_server.configuration.settings import application_settings

        monkeypatch.setattr(application_settings, "max_api_tokens_per_user", 1)
        with (
            patch(
                "tessara_server.data.repository.user_repository.get_by_id",
                new=AsyncMock(return_value=_mock_user()),
            ),
            patch(
                "tessara_server.data.repository.api_token_repository.count_for_user",
                new=AsyncMock(return_value=1),
            ),
        ):
            resp = api_client.post(
                "/admin/users/2/tokens",
                data={"name": "another"},
                headers=csrf_headers(api_client),
            )
        assert resp.status_code == 400
