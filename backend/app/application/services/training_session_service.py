"""Use case: lưu buổi tập vào CSDL."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.messages import TrainingSessionResponse
from app.application.services.stream_processor import StreamProcessor
from app.infrastructure.db.models import TrainingSessionRecord


class TrainingSessionService:
    async def save_session(
        self,
        db: AsyncSession,
        patient_id: str,
        processor: StreamProcessor,
        session_date: date | None = None,
    ) -> TrainingSessionResponse:
        when = session_date or datetime.now(timezone.utc).date()
        row = TrainingSessionRecord(
            patient_id=patient_id,
            session_date=when,
            max_angle_deg=processor.peak_angle_deg,
            avg_resistance_force=processor.avg_resistance_force(),
            rom_session_deg=processor.rom_session_deg,
            completion_percent=processor.completion_percent,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return TrainingSessionResponse(
            id=row.id,
            patient_id=row.patient_id,
            session_date=row.session_date,
            max_angle_deg=row.max_angle_deg,
            avg_resistance_force=row.avg_resistance_force,
            rom_session_deg=row.rom_session_deg,
            completion_percent=row.completion_percent,
            created_at=row.created_at,
        )

    async def list_by_patient(
        self,
        db: AsyncSession,
        patient_id: str,
        limit: int = 50,
    ) -> list[TrainingSessionResponse]:
        from sqlalchemy import select

        stmt = (
            select(TrainingSessionRecord)
            .where(TrainingSessionRecord.patient_id == patient_id)
            .order_by(TrainingSessionRecord.session_date.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            TrainingSessionResponse(
                id=r.id,
                patient_id=r.patient_id,
                session_date=r.session_date,
                max_angle_deg=r.max_angle_deg,
                avg_resistance_force=r.avg_resistance_force,
                rom_session_deg=r.rom_session_deg,
                completion_percent=r.completion_percent,
                created_at=r.created_at,
            )
            for r in rows
        ]
