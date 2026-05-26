"""
WebSocket:
  /ws/device   — Hardware (ESP32, giữ tương thích)
  /ws/hardware — alias
  /ws/twin        — Digital Twin
  /ws/dashboard   — Bác sĩ / UI giám sát
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.deps import get_connection_manager, get_training_session_service
from app.api.session_registry import bind_session, clear_session
from app.application.dto.messages import (
    EmergencyUplink,
    ForceDownlink,
    SensorUplink,
)
from app.application.services.force_dispatch import forward_force_to_hardware
from app.application.services.stream_processor import StreamProcessor
from app.core.config import get_settings
from app.infrastructure.db.session import get_db_session
from app.infrastructure.websocket.connection_manager import ClientRole, ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

try:
    import orjson

    def dumps(obj: dict[str, Any]) -> str:
        return orjson.dumps(obj).decode()

except ImportError:

    def dumps(obj: dict[str, Any]) -> str:
        return json.dumps(obj, separators=(",", ":"))


async def _broadcast_telemetry(
    manager: ConnectionManager,
    broadcast_data: dict[str, Any],
) -> None:
    await manager.broadcast_to_twins(dumps(broadcast_data))
    dash = {"type": "telemetry", **broadcast_data}
    await manager.broadcast_to_dashboards(dumps(dash))


async def _handle_hardware_stream(
    websocket: WebSocket,
    patient_id: str | None,
) -> None:
    manager = get_connection_manager()
    processor = StreamProcessor(get_settings())

    await manager.connect(websocket, ClientRole.HARDWARE)
    processor.reset()
    bind_session(processor, patient_id)
    await manager.push_status_to_dashboards()

    try:
        while True:
            text = await websocket.receive_text()
            try:
                payload: dict[str, Any] = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from hardware")
                continue

            if payload.get("status") == "EMERGENCY_STOP":
                try:
                    emergency = EmergencyUplink.model_validate(payload)
                except ValidationError as exc:
                    logger.warning("Emergency schema error: %s", exc)
                    continue
                logger.critical(
                    "EMERGENCY_STOP patient=%s angle=%s",
                    patient_id,
                    emergency.angle,
                )
                alert = {"type": "alert", **payload}
                await manager.broadcast_to_twins(dumps(payload))
                await manager.broadcast_to_dashboards(dumps(alert))
                continue

            try:
                uplink = SensorUplink.model_validate(payload)
            except ValidationError as exc:
                logger.warning("Uplink schema error: %s", exc)
                continue

            broadcast, snap = processor.process_uplink(uplink)
            await _broadcast_telemetry(manager, broadcast.model_dump())

            downlink = processor.adaptive_downlink()
            await forward_force_to_hardware(manager, processor, downlink)

            logger.debug(
                "ROM=%.1f° completion=%.1f%% twins=%d",
                snap.rom_session_deg,
                snap.completion_percent,
                manager.twin_count,
            )

    except WebSocketDisconnect:
        logger.info("Hardware disconnected patient_id=%s", patient_id)
    finally:
        await manager.disconnect(websocket, ClientRole.HARDWARE)
        await manager.push_status_to_dashboards()
        saved_processor, saved_patient = clear_session()
        if saved_patient and saved_processor is not None:
            await _persist_session(saved_patient, saved_processor)


async def _persist_session(patient_id: str, processor: StreamProcessor) -> None:
    if processor.peak_angle_deg <= 0 and processor.avg_resistance_force() <= 0:
        return
    service = get_training_session_service()
    async for db in get_db_session():
        try:
            row = await service.save_session(db, patient_id, processor)
            logger.info(
                "Session saved id=%s patient=%s max_angle=%.1f",
                row.id,
                patient_id,
                row.max_angle_deg,
            )
        except Exception:
            logger.exception("Failed to save training session")
        break


@router.websocket("/ws/device")
@router.websocket("/ws/hardware")
async def hardware_ws(
    websocket: WebSocket,
    patient_id: str | None = Query(default=None, description="ID bệnh nhân — lưu DB khi ngắt kết nối"),
) -> None:
    await _handle_hardware_stream(websocket, patient_id)


@router.websocket("/ws/twin")
async def twin_ws(websocket: WebSocket) -> None:
    """Digital Twin: nhận broadcast ROM; gửi force_level khi va chạm → hardware."""
    manager = get_connection_manager()
    await manager.connect(websocket, ClientRole.TWIN)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                payload: dict[str, Any] = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from twin")
                continue

            if "force_level" not in payload:
                continue

            try:
                downlink = ForceDownlink.model_validate(payload)
            except ValidationError as exc:
                logger.warning("Twin downlink schema error: %s", exc)
                continue

            from app.api.session_registry import get_active_processor

            processor = get_active_processor()
            sent = await forward_force_to_hardware(manager, processor, downlink)
            if not sent:
                logger.warning("Twin force not forwarded — hardware offline")

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, ClientRole.TWIN)


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket) -> None:
    """Dashboard bác sĩ: telemetry + điều khiển force từ xa."""
    manager = get_connection_manager()
    await manager.connect(websocket, ClientRole.DASHBOARD)
    await websocket.send_text(dumps(manager.status_payload()))

    try:
        while True:
            text = await websocket.receive_text()
            try:
                payload: dict[str, Any] = json.loads(text)
            except json.JSONDecodeError:
                continue

            if payload.get("type") == "set_force" or "force_level" in payload:
                try:
                    downlink = ForceDownlink.model_validate(payload)
                except ValidationError:
                    continue
                from app.api.session_registry import get_active_processor

                processor = get_active_processor()
                await forward_force_to_hardware(manager, processor, downlink)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, ClientRole.DASHBOARD)
