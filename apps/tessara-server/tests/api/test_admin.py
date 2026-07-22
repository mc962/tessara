"""Tests for /admin/login — any active key can sign in, only /admin/api-keys needs superuser."""

from unittest.mock import AsyncMock, MagicMock, patch

from tessara_server.data.model.api_key import ApiKey


def _mock_key(is_superuser: bool = False) -> MagicMock:
    key = MagicMock(spec=ApiKey)
    key.id = 1
    key.is_superuser = is_superuser
    key.is_active = True
    return key


class TestPostLogin:
    def test_non_superuser_key_logs_in(self, unauthed_client):
        with patch(
            "tessara_server.data.repository.api_key_repository.verify_key",
            new=AsyncMock(return_value=_mock_key(is_superuser=False)),
        ):
            resp = unauthed_client.post(
                "/admin/login", data={"api_key": "tsa_x"}, follow_redirects=False
            )
        assert resp.status_code == 303
        assert "tessara_session" in resp.cookies

    def test_default_redirect_is_generate_not_admin(self, unauthed_client):
        with patch(
            "tessara_server.data.repository.api_key_repository.verify_key",
            new=AsyncMock(return_value=_mock_key(is_superuser=False)),
        ):
            resp = unauthed_client.post(
                "/admin/login", data={"api_key": "tsa_x"}, follow_redirects=False
            )
        assert resp.headers["location"] == "/generate"

    def test_next_param_is_respected(self, unauthed_client):
        with patch(
            "tessara_server.data.repository.api_key_repository.verify_key",
            new=AsyncMock(return_value=_mock_key(is_superuser=False)),
        ):
            resp = unauthed_client.post(
                "/admin/login",
                data={"api_key": "tsa_x", "next": "/admin/api-keys"},
                follow_redirects=False,
            )
        assert resp.headers["location"] == "/admin/api-keys"

    def test_invalid_key_returns_401(self, unauthed_client):
        with patch(
            "tessara_server.data.repository.api_key_repository.verify_key",
            new=AsyncMock(return_value=None),
        ):
            resp = unauthed_client.post("/admin/login", data={"api_key": "bad"})
        assert resp.status_code == 401

    def test_rate_limited_after_too_many_attempts(self, unauthed_client):
        # rate_limit_login defaults to "5/minute" — the 6th attempt within
        # the window should be rejected regardless of whether the key is valid.
        with patch(
            "tessara_server.data.repository.api_key_repository.verify_key",
            new=AsyncMock(return_value=None),
        ):
            for _ in range(5):
                resp = unauthed_client.post("/admin/login", data={"api_key": "bad"})
                assert resp.status_code == 401
            resp = unauthed_client.post("/admin/login", data={"api_key": "bad"})
        assert resp.status_code == 429
