"""ORM — lịch sử tập luyện."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TrainingSessionRecord(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    max_angle_deg: Mapped[float] = mapped_column(Float, nullable=False)
    avg_resistance_force: Mapped[float] = mapped_column(Float, nullable=False)
    rom_session_deg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completion_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
