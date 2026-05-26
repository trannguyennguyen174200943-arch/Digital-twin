"""WebSocket stream kết quả MediaPipe Pose → frontend."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.application.services.pose_stream_service import get_pose_hub

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/pose")
async def pose_stream(websocket: WebSocket) -> None:
    """
    Stream JSON:
      - type pose_frame: landmarks + torso_compensation_deg + cheat_detected
      - type pose_alert: sai tư thế + đã ngắt lực
    """
    await websocket.accept()
    hub = get_pose_hub()
    queue = await hub.subscribe()
    logger.info("Pose WS client connected: %s", websocket.client)

    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
                continue
            await websocket.send_text(json.dumps(payload, separators=(",", ":")))
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unsubscribe(queue)
        logger.info("Pose WS client disconnected")
