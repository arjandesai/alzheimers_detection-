"""Helper for writing AuditLogEntry rows consistently from route handlers.

Route handlers should call `record_audit_event` instead of constructing
`AuditLogEntry` directly, so every entry goes through the same shape and a
future change (e.g. adding a request-id column) only touches one place.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from alzheimers_detection.core.models import AuditLogEntry


def record_audit_event(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLogEntry:
    """Adds an AuditLogEntry to the session. Does not commit -- the caller's
    request-scoped session (see core/db.py::get_db) commits on success, so
    the audit entry lands atomically with whatever action it describes."""
    entry = AuditLogEntry(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata,
    )
    db.add(entry)
    return entry
