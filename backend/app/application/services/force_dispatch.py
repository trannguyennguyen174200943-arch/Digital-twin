"""Gửi lệnh lực cản xuống phần cứng — dùng chung REST / WS."""

from __future__ import annotations

import json
from typing import Any

from app.application.dto.messages import ForceDownlink
from app.application.services.stream_processor import StreamProcessor
from app.infrastructure.websocket.connection_manager import ConnectionManager


def dumps(obj: dict[str, Any]) -> str:
    return json.dumps(obj, separators=(",", ":"))


async def forward_force_to_hardware(
    manager: ConnectionManager,
    processor: StreamProcessor | None,
    downlink: ForceDownlink,
) -> bool:
    if processor is not None:
        processor.record_downlink_force(downlink)
        processor.set_applied_force(downlink.force_level)
    return await manager.send_to_hardware(dumps(downlink.model_dump()))
