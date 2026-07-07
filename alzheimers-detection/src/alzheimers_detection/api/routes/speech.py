"""Speech analysis endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from alzheimers_detection.api.deps import get_current_user
from alzheimers_detection.core.audit import record_audit_event
from alzheimers_detection.core.db import get_db
from alzheimers_detection.core.models import AnalysisRecord, User
from alzheimers_detection.speech.pipeline import analyze_audio_bytes
from alzheimers_detection.speech.schemas import SpeechAnalysisResult
from alzheimers_detection.speech.transcription import TranscriptionError

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/webm", "audio/ogg"}


@router.post(
    "/analyze",
    response_model=SpeechAnalysisResult,
    summary="Analyze a speech sample for acoustic and linguistic biomarkers",
)
async def analyze_speech(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SpeechAnalysisResult:
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type '{file.content_type}'. "
            f"Expected one of: {sorted(_ALLOWED_CONTENT_TYPES)}",
        )

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = analyze_audio_bytes(audio_bytes, filename_hint=file.filename or "upload.wav")
    except TranscriptionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ValueError as e:
        # e.g. audio too long -- a client-fixable input problem, not a server error
        raise HTTPException(status_code=400, detail=str(e)) from e

    record = AnalysisRecord(
        user_id=current_user.id, modality="speech", result_json=result.model_dump_json()
    )
    db.add(record)
    db.flush()  # populate record.id before it's referenced by the audit entry
    record_audit_event(
        db,
        action="create",
        resource_type="analysis_record",
        resource_id=str(record.id),
        user_id=current_user.id,
        metadata={"modality": "speech"},
    )
    return result
