"""Registration, login, and current-user endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from alzheimers_detection.api.deps import get_current_user
from alzheimers_detection.core.audit import record_audit_event
from alzheimers_detection.core.db import get_db
from alzheimers_detection.core.models import User
from alzheimers_detection.core.schemas_auth import Token, UserCreate, UserRead
from alzheimers_detection.core.security import create_access_token, hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.flush()  # populate user.id before it's referenced by the audit entry
    record_audit_event(db, action="register", resource_type="user", resource_id=str(user.id), user_id=user.id)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    record_audit_event(db, action="login", resource_type="user", resource_id=str(user.id), user_id=user.id)
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    """GDPR right-to-erasure: deletes the account and, via ON DELETE CASCADE,
    all of its AnalysisRecords. Lives here (not results.py) because it
    deletes the account itself, not just individual results. The audit
    trail survives -- AuditLogEntry.user_id is ON DELETE SET NULL -- so the
    fact that an erasure happened remains provable."""
    record_audit_event(
        db, action="delete", resource_type="user", resource_id=str(current_user.id), user_id=current_user.id
    )
    db.delete(current_user)
