"""DTO / schema giao tiếp API & WebSocket."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class SensorUplink(BaseModel):
    angle: float
    raw_flex: int = Field(..., ge=0, le=4095)
    timestamp: int = Field(..., ge=0)


class ForceDownlink(BaseModel):
    force_level: int = Field(..., ge=0, le=255)
    direction: int = Field(default=1, ge=-1, le=1)


class EmergencyUplink(BaseModel):
    status: str = Field(..., pattern="^EMERGENCY_STOP$")
    timestamp: int | None = None
    angle: float | None = None


class TwinBroadcast(BaseModel):
    """Dữ liệu đã xử lý gửi sang Digital Twin."""

    angle: float
    joint_angle: float | None = None  # alias cho Webots (mặc định = angle khi dump)
    raw_flex: int
    timestamp: int
    rom_session_deg: float
    rom_reference_deg: float
    completion_percent: float
    peak_completion_percent: float
    min_angle_deg: float
    max_angle_deg: float
    applied_force_level: int = 0
    flex_force_proxy: float = 0.0
    fatigue_score: float = 0.0
    angular_velocity_deg_s: float | None = None
    tremor_index: float | None = None
    fatigue_active: bool = False


class SessionFinalizeRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=64)


class TrainingSessionResponse(BaseModel):
    id: int
    patient_id: str
    session_date: date
    max_angle_deg: float
    avg_resistance_force: float
    rom_session_deg: float
    completion_percent: float
    created_at: datetime
