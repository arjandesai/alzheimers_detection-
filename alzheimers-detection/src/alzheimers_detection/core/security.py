"""Password hashing and JWT access tokens.

Uses `bcrypt` directly (not `passlib`, which is unmaintained and has had
compatibility breakage with newer bcrypt releases) and `pyjwt` directly
(no framework wrapper needed for a single HS256 access-token use case).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from alzheimers_detection.core.config import get_settings

_TOKEN_SUBJECT_CLAIM = "sub"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


class TokenError(Exception):
    """Raised for any invalid, expired, or malformed access token."""


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: dict[str, Any] = {_TOKEN_SUBJECT_CLAIM: subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Returns the token subject (user id, as a string) or raises TokenError."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as e:
        raise TokenError(str(e)) from e
    subject = payload.get(_TOKEN_SUBJECT_CLAIM)
    if subject is None:
        raise TokenError("Token missing subject claim")
    return subject
