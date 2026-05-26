"""Điều khiển từ xa — dashboard / bác sĩ."""

from pydantic import BaseModel, Field


class ForceControlRequest(BaseModel):
    force_level: int = Field(..., ge=0, le=255)
    direction: int = Field(default=1, ge=-1, le=1)
