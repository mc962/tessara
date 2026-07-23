"""Tests for /signup, /verify-email, /login, /logout, /forgot-password, /reset-password."""

from unittest.mock import AsyncMock, MagicMock, patch

from tessara_server.data.model.user import User


def _mock_user(is_superuser: bool = False, is_active: bool = True, is_verified: bool = True) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "user@example.com"
    user.password_hash = "hashed"
    user.is_superuser = is_superuser
    user.is_active = is_active
    user.is_verified = is_verified
    return user


class TestSignup:
    def test_creates_user_and_shows_verify_notice(self, unauthed_client, csrf_headers):
        with (
            patch(
                "tessara_server.data.repository.user_repository.get_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "tessara_server.data.repository.user_repository.create",
                new=AsyncMock(return_value=_mock_user(is_verified=False)),
            ),
            patch("tessara_server.web.html.auth.send_email", new=AsyncMock()) as send,
        ):
            resp = unauthed_client.post(
                "/signup",
                data={"email": "user@example.com", "password": "longenough"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 200
        assert b"Check your email" in resp.content
        send.assert_awaited_once()

    def test_existing_email_returns_400(self, unauthed_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.get_by_email",
            new=AsyncMock(return_value=_mock_user()),
        ):
            resp = unauthed_client.post(
                "/signup",
                data={"email": "user@example.com", "password": "longenough"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 400

    def test_short_password_returns_400(self, unauthed_client, csrf_headers):
        resp = unauthed_client.post(
            "/signup",
            data={"email": "user@example.com", "password": "short"},
            headers=csrf_headers(unauthed_client),
        )
        assert resp.status_code == 400

    def test_missing_csrf_token_returns_403(self, unauthed_client):
        resp = unauthed_client.post(
            "/signup", data={"email": "user@example.com", "password": "longenough"}
        )
        assert resp.status_code == 403


class TestVerifyEmail:
    def test_valid_token_verifies_user(self, unauthed_client):
        from tessara_server.web.dependencies.tokens import make_email_token

        user = _mock_user(is_verified=False)
        token = make_email_token(user)
        with (
            patch(
                "tessara_server.data.repository.user_repository.get_by_id",
                new=AsyncMock(return_value=user),
            ),
            patch(
                "tessara_server.data.repository.user_repository.set_verified",
                new=AsyncMock(),
            ) as set_verified,
        ):
            resp = unauthed_client.get(f"/verify-email?token={token}")
        assert resp.status_code == 200
        set_verified.assert_awaited_once()
        assert set_verified.await_args.args[1] == user.id

    def test_garbage_token_returns_400(self, unauthed_client):
        resp = unauthed_client.get("/verify-email?token=not-a-real-token")
        assert resp.status_code == 400


class TestLogin:
    def test_valid_login_sets_cookie(self, unauthed_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.verify_password",
            new=AsyncMock(return_value=_mock_user()),
        ):
            resp = unauthed_client.post(
                "/login",
                data={"email": "user@example.com", "password": "correct"},
                headers=csrf_headers(unauthed_client),
                follow_redirects=False,
            )
        assert resp.status_code == 303
        assert "tessara_session" in resp.cookies

    def test_default_redirect_is_generate(self, unauthed_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.verify_password",
            new=AsyncMock(return_value=_mock_user()),
        ):
            resp = unauthed_client.post(
                "/login",
                data={"email": "user@example.com", "password": "correct"},
                headers=csrf_headers(unauthed_client),
                follow_redirects=False,
            )
        assert resp.headers["location"] == "/generate"

    def test_next_param_is_respected(self, unauthed_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.verify_password",
            new=AsyncMock(return_value=_mock_user()),
        ):
            resp = unauthed_client.post(
                "/login",
                data={"email": "user@example.com", "password": "correct", "next": "/admin/users"},
                headers=csrf_headers(unauthed_client),
                follow_redirects=False,
            )
        assert resp.headers["location"] == "/admin/users"

    def test_invalid_credentials_returns_401(self, unauthed_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.verify_password",
            new=AsyncMock(return_value=None),
        ):
            resp = unauthed_client.post(
                "/login",
                data={"email": "user@example.com", "password": "bad"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 401

    def test_unverified_user_returns_401(self, unauthed_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.verify_password",
            new=AsyncMock(return_value=_mock_user(is_verified=False)),
        ):
            resp = unauthed_client.post(
                "/login",
                data={"email": "user@example.com", "password": "correct"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 401
        assert b"verify your email" in resp.content

    def test_rate_limited_after_too_many_attempts(self, unauthed_client, csrf_headers):
        headers = csrf_headers(unauthed_client)
        with patch(
            "tessara_server.data.repository.user_repository.verify_password",
            new=AsyncMock(return_value=None),
        ):
            for _ in range(5):
                resp = unauthed_client.post(
                    "/login",
                    data={"email": "user@example.com", "password": "bad"},
                    headers=headers,
                )
                assert resp.status_code == 401
            resp = unauthed_client.post(
                "/login",
                data={"email": "user@example.com", "password": "bad"},
                headers=headers,
            )
        assert resp.status_code == 429

    def test_missing_csrf_token_returns_403(self, unauthed_client):
        with patch(
            "tessara_server.data.repository.user_repository.verify_password",
            new=AsyncMock(return_value=_mock_user()),
        ):
            resp = unauthed_client.post(
                "/login", data={"email": "user@example.com", "password": "correct"}
            )
        assert resp.status_code == 403


class TestForgotPassword:
    def test_always_shows_sent_message(self, unauthed_client, csrf_headers):
        with patch(
            "tessara_server.data.repository.user_repository.get_by_email",
            new=AsyncMock(return_value=None),
        ):
            resp = unauthed_client.post(
                "/forgot-password",
                data={"email": "nobody@x.com"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 200
        assert b"we've sent a link" in resp.content

    def test_sends_email_for_existing_user(self, unauthed_client, csrf_headers):
        with (
            patch(
                "tessara_server.data.repository.user_repository.get_by_email",
                new=AsyncMock(return_value=_mock_user()),
            ),
            patch("tessara_server.web.html.auth.send_email", new=AsyncMock()) as send,
        ):
            resp = unauthed_client.post(
                "/forgot-password",
                data={"email": "user@example.com"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 200
        send.assert_awaited_once()


class TestResetPassword:
    def test_valid_token_resets_password(self, unauthed_client, csrf_headers):
        from tessara_server.web.dependencies.tokens import make_reset_token

        user = _mock_user()
        token = make_reset_token(user)
        with (
            patch(
                "tessara_server.data.repository.user_repository.get_by_id",
                new=AsyncMock(return_value=user),
            ),
            patch(
                "tessara_server.data.repository.user_repository.set_password",
                new=AsyncMock(),
            ) as set_password,
        ):
            resp = unauthed_client.post(
                "/reset-password",
                data={"token": token, "password": "newlongpassword"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 200
        set_password.assert_awaited_once()

    def test_garbage_token_returns_400(self, unauthed_client, csrf_headers):
        resp = unauthed_client.post(
            "/reset-password",
            data={"token": "not-a-real-token", "password": "newlongpassword"},
            headers=csrf_headers(unauthed_client),
        )
        assert resp.status_code == 400

    def test_short_password_returns_400(self, unauthed_client, csrf_headers):
        from tessara_server.web.dependencies.tokens import make_reset_token

        user = _mock_user()
        token = make_reset_token(user)
        with patch(
            "tessara_server.data.repository.user_repository.get_by_id",
            new=AsyncMock(return_value=user),
        ):
            resp = unauthed_client.post(
                "/reset-password",
                data={"token": token, "password": "short"},
                headers=csrf_headers(unauthed_client),
            )
        assert resp.status_code == 400


class TestLogout:
    def test_clears_session_cookie(self, unauthed_client, csrf_headers):
        resp = unauthed_client.post(
            "/logout", headers=csrf_headers(unauthed_client), follow_redirects=False
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    def test_missing_csrf_token_returns_403(self, unauthed_client):
        resp = unauthed_client.post("/logout")
        assert resp.status_code == 403
