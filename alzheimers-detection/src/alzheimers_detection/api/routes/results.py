"""List/get/delete a user's own persisted analysis results.

Scoped to the current user throughout -- there is no admin/cross-user read
path here, so a record's `user_id` is always filtered against
`current_user.id` rather than trusted from the URL.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from alzheimers_detection.api.deps import get_current_user
from alzheimers_detection.core.audit import record_audit_event
from alzheimers_detection.core.db import get_db
from alzheimers_detection.core.models import AnalysisRecord, User
from alzheimers_detection.core.schemas_auth import AnalysisRecordRead

router = APIRouter()


def _to_read_model(record: AnalysisRecord) -> AnalysisRecordRead:
    return AnalysisRecordRead(
        id=record.id,
        modality=record.modality,
        created_at=record.created_at,
        result=json.loads(record.result_json),
    )


def _get_owned_record_or_404(db: Session, record_id: int, user: User) -> AnalysisRecord:
    record = db.get(AnalysisRecord, record_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found")
    return record


@router.get("", response_model=list[AnalysisRecordRead])
def list_results(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[AnalysisRecordRead]:
    records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current_user.id)
        .order_by(AnalysisRecord.created_at.desc())
        .all()
    )
    return [_to_read_model(r) for r in records]


@router.get("/{record_id}", response_model=AnalysisRecordRead)
def get_result(
    record_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AnalysisRecordRead:
    record = _get_owned_record_or_404(db, record_id, current_user)
    record_audit_event(
        db, action="view", resource_type="analysis_record", resource_id=str(record.id), user_id=current_user.id
    )
    return _to_read_model(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(
    record_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    record = _get_owned_record_or_404(db, record_id, current_user)
    record_audit_event(
        db, action="delete", resource_type="analysis_record", resource_id=str(record.id), user_id=current_user.id
    )
    db.delete(record)
