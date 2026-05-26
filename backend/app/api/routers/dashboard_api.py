"""REST — tổng quan cho dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_connection_manager
from app.api.session_registry import get_active_processor
from app.infrastructure.db.models import TrainingSessionRecord
from app.infrastructure.db.session import get_db_session
from app.infrastructure.websocket.connection_manager import ConnectionManager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/status")
async def dashboard_status(
    manager: ConnectionManager = Depends(get_connection_manager),
) -> dict:
    processor = get_active_processor()
    live_peak = processor.peak_angle_deg if processor else 0.0
    return {
        **manager.status_payload(),
        "session_peak_angle_deg": live_peak,
        "completion_percent": processor.completion_percent if processor else 0.0,
    }


@router.get("/summary/{patient_id}")
async def daily_summary(
    patient_id: str,
    db: AsyncSession = Depends(get_db_session),
    manager: ConnectionManager = Depends(get_connection_manager),
) -> dict:
    today = datetime.now(timezone.utc).date()
    stmt = select(func.max(TrainingSessionRecord.max_angle_deg)).where(
        TrainingSessionRecord.patient_id == patient_id,
        TrainingSessionRecord.session_date == today,
    )
    result = await db.execute(stmt)
    db_max = result.scalar() or 0.0

    processor = get_active_processor()
    live_peak = processor.peak_angle_deg if processor else 0.0

    return {
        "patient_id": patient_id,
        "date": today.isoformat(),
        "max_angle_today_deg": max(db_max, live_peak),
        "hardware_connected": manager.has_hardware,
    }
