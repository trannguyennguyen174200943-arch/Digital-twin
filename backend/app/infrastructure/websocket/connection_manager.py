"""
Quản lý hai luồng WebSocket: Hardware (ESP32) và Digital Twin.

Hardware uplink → xử lý → broadcast sang mọi client Twin đang kết nối.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ClientRole(str, Enum):
    HARDWARE = "hardware"
    TWIN = "twin"
    DASHBOARD = "dashboard"


class ConnectionManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._hardware: WebSocket | None = None
        self._twins: set[WebSocket] = set()
        self._dashboards: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, role: ClientRole) -> None:
        await websocket.accept()
        async with self._lock:
            if role == ClientRole.HARDWARE:
                if self._hardware is not None:
                    logger.warning("Replacing existing hardware connection")
                self._hardware = websocket
                logger.info("Hardware connected: %s", websocket.client)
            elif role == ClientRole.TWIN:
                self._twins.add(websocket)
                logger.info("Digital Twin connected: %s (total=%d)", websocket.client, len(self._twins))
            else:
                self._dashboards.add(websocket)
                logger.info("Dashboard connected: %s (total=%d)", websocket.client, len(self._dashboards))

    async def disconnect(self, websocket: WebSocket, role: ClientRole) -> None:
        async with self._lock:
            if role == ClientRole.HARDWARE and self._hardware is websocket:
                self._hardware = None
                logger.info("Hardware disconnected")
            elif role == ClientRole.TWIN and websocket in self._twins:
                self._twins.discard(websocket)
                logger.info("Digital Twin disconnected (remaining=%d)", len(self._twins))
            elif role == ClientRole.DASHBOARD and websocket in self._dashboards:
                self._dashboards.discard(websocket)
                logger.info("Dashboard disconnected (remaining=%d)", len(self._dashboards))

    async def send_to_hardware(self, message: str) -> bool:
        async with self._lock:
            ws = self._hardware
        if ws is None:
            return False
        try:
            await ws.send_text(message)
            return True
        except Exception:
            logger.exception("Failed to send to hardware")
            return False

    async def _broadcast_to_set(
        self,
        message: str,
        targets: list[WebSocket],
        bucket: set[WebSocket],
    ) -> int:
        if not targets:
            return 0
        sent = 0
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(message)
                sent += 1
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    bucket.discard(ws)
        return sent

    async def broadcast_to_twins(self, message: str) -> int:
        async with self._lock:
            targets = list(self._twins)
            bucket = self._twins
        return await self._broadcast_to_set(message, targets, bucket)

    async def broadcast_to_dashboards(self, message: str) -> int:
        async with self._lock:
            targets = list(self._dashboards)
            bucket = self._dashboards
        return await self._broadcast_to_set(message, targets, bucket)

    def status_payload(self) -> dict[str, bool | int]:
        return {
            "type": "status",
            "hardware_connected": self.has_hardware,
            "twin_count": self.twin_count,
            "dashboard_count": len(self._dashboards),
        }

    async def push_status_to_dashboards(self) -> None:
        import json

        await self.broadcast_to_dashboards(json.dumps(self.status_payload(), separators=(",", ":")))

    @property
    def has_hardware(self) -> bool:
        return self._hardware is not None

    @property
    def twin_count(self) -> int:
        return len(self._twins)

