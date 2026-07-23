"""Stateless, signed tokens for email verification and password reset.

Both embed a nonce derived from the user's current password hash. Verifying
recomputes the nonce from the user's *current* password_hash — a mismatch
(the password changed since the link was issued, or a reset already
consumed it) invalidates the link with no token table or cleanup job.

The token itself only carries a user id + nonce (signed/timestamped by
itsdangerous); callers decode it, look the user up, then confirm the nonce
still matches via `nonce_matches`.
"""

import hashlib

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from tessara_server.configuration.settings import application_settings
from tessara_server.data.model.user import User

_EMAIL_SALT = "email-verify"
_RESET_SALT = "pwd-reset"


def password_nonce(user: User) -> str:
    """Short digest of the user's current password hash — changes whenever
    the password does, so tokens/sessions built from an old nonce stop
    matching automatically."""
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        application_settings.session_secret.get_secret_value(), salt=salt
    )


def nonce_matches(user: User, nonce: str) -> bool:
    return password_nonce(user) == nonce


def make_email_token(user: User) -> str:
    return _serializer(_EMAIL_SALT).dumps({"uid": user.id, "nonce": password_nonce(user)})


def decode_email_token(token: str) -> dict | None:
    return _decode(token, _EMAIL_SALT, application_settings.verification_token_max_age)


def make_reset_token(user: User) -> str:
    return _serializer(_RESET_SALT).dumps({"uid": user.id, "nonce": password_nonce(user)})


def decode_reset_token(token: str) -> dict | None:
    return _decode(token, _RESET_SALT, application_settings.password_reset_token_max_age)


def _decode(token: str, salt: str, max_age: int) -> dict | None:
    try:
        data = _serializer(salt).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired, KeyError):
        return None
    if "uid" not in data or "nonce" not in data:
        return None
    return data
