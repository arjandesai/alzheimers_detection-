"""ORM models for Milestone 2 (persistence + auth).

Two design choices worth calling out:

- `AnalysisRecord` is generic across modalities (`modality` string +
  `result_json` blob) rather than one table per modality. Milestone 1 only
  has speech, but the whole point of this table existing now is that
  Milestone 4+ (drawing, facial, typing, ...) can reuse it without a schema
  migration per modality -- see docs/ARCHITECTURE.md roadmap.
- `AuditLogEntry.user_id` is nullable and the row is never deleted when a
  user is (see the `ondelete="SET NULL"` FK below): the audit trail must
  outlive the account it describes, otherwise "right to erasure" would also
  erase the evidence that erasure happened.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alzheimers_detection.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    analysis_records: Mapped[list[AnalysisRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AnalysisRecord(Base):
    """One stored result from any modality pipeline (speech today; drawing,
    facial, typing, etc. in future milestones reuse this same table)."""

    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    modality: Mapped[str] = mapped_column(String(50), nullable=False)
    result_json: Mapped[str] = mapped_column(
        Text, nullable=False, doc="JSON-serialized pipeline result (e.g. SpeechAnalysisResult)"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="analysis_records")


class AuditLogEntry(Base):
    """Append-only audit trail. Never update or delete rows here from
    application code -- only insert. `user_id` is nullable and set to NULL
    (not cascade-deleted) when the referenced user is removed, so erasure
    requests don't also erase the record that erasure occurred."""

    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="e.g. 'create', 'view', 'delete', 'login', 'register'"
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, doc="e.g. 'analysis_record', 'user'")
    resource_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
