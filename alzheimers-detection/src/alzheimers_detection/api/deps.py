"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from alzheimers_detection.core.db import get_db
from alzheimers_detection.core.models import User
from alzheimers_detection.core.security import TokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        subject = decode_access_token(token)
        user_id = int(subject)
    except (TokenError, ValueError) as e:
        raise credentials_exception from e

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user
