"""Data contracts for auth and persisted-result endpoints.

Follows the same convention as speech/schemas.py: explicit Pydantic models
per package rather than passing dicts around.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters; hashed with bcrypt before storage")


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AnalysisRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    modality: str
    created_at: datetime
    result: dict = Field(description="The stored pipeline result, deserialized from result_json")
