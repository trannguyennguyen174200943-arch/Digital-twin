"""
Capture video + MediaPipe trên thread nền — không chặn event loop FastAPI.

Khi cheat_detected chuyển True → gửi force_level=0 xuống ESP32 (một lần / sự kiện).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any

from app.api.deps import get_connection_manager
from app.api.session_registry import get_active_processor
from app.application.dto.messages import ForceDownlink
from app.application.services.force_dispatch import forward_force_to_hardware
from app.core.config import Settings, get_settings
from app.domain.vision.pose_analyzer import PoseAnalyzer

logger = logging.getLogger(__name__)


class PoseStreamHub:
    """Phát kết quả pose tới các client WebSocket /ws/pose."""

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._latest: dict[str, Any] | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=8)
        async with self._lock:
            self._clients.add(q)
            if self._latest is not None:
                try:
                    q.put_nowait(self._latest)
                except asyncio.QueueFull:
                    pass
        return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._clients.discard(q)

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        self._latest = payload
        async with self._lock:
            clients = list(self._clients)
        for q in clients:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

    def publish_from_thread(self, payload: dict[str, Any]) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)


_hub = PoseStreamHub()


def get_pose_hub() -> PoseStreamHub:
    return _hub


class PoseCaptureWorker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cheat_latched = False

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if not self._settings.pose_enabled:
            logger.info("Pose capture disabled (POSE_ENABLED=false)")
            return
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pose-capture", daemon=True)
        self._thread.start()
        logger.info("Pose capture thread started source=%s", self._settings.pose_video_source)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def _parse_source(self) -> int | str:
        src = self._settings.pose_video_source.strip()
        if src.isdigit():
            return int(src)
        return src

    def _run(self) -> None:
        import cv2

        source = self._parse_source()
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error("Cannot open video source: %s", source)
            return

        analyzer = PoseAnalyzer(
            cheat_tilt_deg=self._settings.pose_cheat_tilt_deg,
            cheat_shoulder_tilt_deg=self._settings.pose_shoulder_tilt_deg,
        )
        hub = get_pose_hub()
        frame_skip = max(1, self._settings.pose_frame_skip)
        frame_idx = 0

        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    if isinstance(source, str):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.05)
                    continue

                frame_idx += 1
                if frame_idx % frame_skip != 0:
                    continue

                result = analyzer.analyze(frame)
                payload = result.to_payload()

                if result.cheat_detected and not self._cheat_latched:
                    self._cheat_latched = True
                    payload["type"] = "pose_alert"
                    self._trigger_haptic_cut()
                elif not result.cheat_detected:
                    self._cheat_latched = False

                hub.publish_from_thread(payload)
        finally:
            analyzer.close()
            cap.release()
            logger.info("Pose capture thread stopped")

    def _trigger_haptic_cut(self) -> None:
        loop = _hub._loop
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._async_haptic_cut(), loop)

    async def _async_haptic_cut(self) -> None:
        manager = get_connection_manager()
        processor = get_active_processor()
        downlink = ForceDownlink(force_level=0, direction=0)
        sent = await forward_force_to_hardware(manager, processor, downlink)
        alert = {
            "type": "pose_alert",
            "cheat_detected": True,
            "warning": "Ngắt lực haptic — sai tư thế toàn thân",
            "action": "force_level_0",
            "hardware_notified": sent,
        }
        await _hub._broadcast(alert)
        logger.warning("Cheat posture — haptic cut sent=%s", sent)


_worker: PoseCaptureWorker | None = None


def get_pose_worker() -> PoseCaptureWorker:
    global _worker
    if _worker is None:
        _worker = PoseCaptureWorker(get_settings())
    return _worker
