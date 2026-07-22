"""Tests for brandcc_server.utility.security."""

from brandcc_server.utility.security import hash_secure_value, verify_secure_value


class TestHashSecureValue:
    def test_returns_string(self):
        assert isinstance(hash_secure_value("secret"), str)

    def test_different_hashes_for_same_value(self):
        # Argon2 uses random salt
        assert hash_secure_value("secret") != hash_secure_value("secret")

    def test_hash_not_equal_to_input(self):
        assert hash_secure_value("secret") != "secret"


class TestVerifySecureValue:
    def test_correct_value_returns_true(self):
        hashed = hash_secure_value("correct")
        assert verify_secure_value(hashed, "correct") is True

    def test_wrong_value_returns_false(self):
        hashed = hash_secure_value("correct")
        assert verify_secure_value(hashed, "wrong") is False

    def test_empty_value_returns_false(self):
        hashed = hash_secure_value("correct")
        assert verify_secure_value(hashed, "") is False

    def test_invalid_hash_returns_false(self):
        assert verify_secure_value("not-a-valid-hash", "anything") is False
