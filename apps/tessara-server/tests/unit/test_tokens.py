"""Tests for tessara_server.web.dependencies.tokens — signed verify/reset tokens."""

from unittest.mock import MagicMock

from tessara_server.web.dependencies import tokens


def _user(user_id: int = 1, password_hash: str = "hash-a") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.password_hash = password_hash
    return user


class TestEmailToken:
    def test_round_trips(self):
        user = _user()
        token = tokens.make_email_token(user)
        data = tokens.decode_email_token(token)
        assert data is not None
        assert data["uid"] == user.id
        assert tokens.nonce_matches(user, data["nonce"])

    def test_invalidated_by_password_change(self):
        user = _user(password_hash="hash-a")
        token = tokens.make_email_token(user)
        user.password_hash = "hash-b"
        data = tokens.decode_email_token(token)
        assert data is not None
        assert not tokens.nonce_matches(user, data["nonce"])

    def test_garbage_token_returns_none(self):
        assert tokens.decode_email_token("not-a-real-token") is None

    def test_reset_token_not_accepted_as_email_token(self):
        user = _user()
        token = tokens.make_reset_token(user)
        assert tokens.decode_email_token(token) is None


class TestResetToken:
    def test_round_trips(self):
        user = _user()
        token = tokens.make_reset_token(user)
        data = tokens.decode_reset_token(token)
        assert data is not None
        assert data["uid"] == user.id
        assert tokens.nonce_matches(user, data["nonce"])

    def test_invalidated_after_password_reset(self):
        user = _user(password_hash="hash-a")
        token = tokens.make_reset_token(user)
        user.password_hash = "hash-b"  # simulates set_password having run
        data = tokens.decode_reset_token(token)
        assert data is not None
        assert not tokens.nonce_matches(user, data["nonce"])
