"""REST — điều chỉnh kháng lực từ dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_connection_manager
from app.api.session_registry import get_active_processor
from app.application.dto.control import ForceControlRequest
from app.application.dto.messages import ForceDownlink
from app.application.services.force_dispatch import forward_force_to_hardware
from app.infrastructure.websocket.connection_manager import ConnectionManager

router = APIRouter(prefix="/api/control", tags=["control"])


@router.post("/force")
async def set_force_level(
    body: ForceControlRequest,
    manager: ConnectionManager = Depends(get_connection_manager),
) -> dict[str, Any]:
    """Gửi mức lực cản xuống thiết bị đeo (ESP32)."""
    downlink = ForceDownlink(force_level=body.force_level, direction=body.direction)
    processor = get_active_processor()
    sent = await forward_force_to_hardware(manager, processor, downlink)
    if not sent:
        raise HTTPException(
            status_code=503,
            detail="Thiết bị phần cứng chưa kết nối — không gửi được lệnh",
        )
    return {
        "ok": True,
        "force_level": downlink.force_level,
        "direction": downlink.direction,
    }
