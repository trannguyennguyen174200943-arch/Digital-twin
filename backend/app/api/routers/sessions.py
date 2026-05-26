"""REST — lịch sử tập luyện."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_stream_processor, get_training_session_service
from app.application.dto.messages import SessionFinalizeRequest, TrainingSessionResponse
from app.application.services.stream_processor import StreamProcessor
from app.application.services.training_session_service import TrainingSessionService
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/finalize", response_model=TrainingSessionResponse)
async def finalize_session(
    body: SessionFinalizeRequest,
    db: AsyncSession = Depends(get_db_session),
    processor: StreamProcessor = Depends(get_stream_processor),
    service: TrainingSessionService = Depends(get_training_session_service),
) -> TrainingSessionResponse:
    """Kết thúc buổi tập thủ công và lưu DB (không cần đợi ngắt WebSocket)."""
    if processor.peak_angle_deg <= 0 and processor.avg_resistance_force() <= 0:
        raise HTTPException(status_code=400, detail="No active training data to save")
    return await service.save_session(db, body.patient_id, processor)


@router.get("/patient/{patient_id}", response_model=list[TrainingSessionResponse])
async def list_patient_sessions(
    patient_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    service: TrainingSessionService = Depends(get_training_session_service),
) -> list[TrainingSessionResponse]:
    return await service.list_by_patient(db, patient_id, limit=limit)
