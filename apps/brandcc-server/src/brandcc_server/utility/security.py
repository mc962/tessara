"""Cryptographic helpers — Argon2 for API key hashing."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ph = PasswordHasher()


def hash_secure_value(value: str) -> str:
    return _ph.hash(value)


def verify_secure_value(hashed: str, value: str) -> bool:
    try:
        return _ph.verify(hashed, value)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
