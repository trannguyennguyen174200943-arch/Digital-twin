"""
WebSocket nền — websocket-client (khuyến nghị cho Webots).

Webots bắt buộc vòng lặp đồng bộ robot.step(); không dùng asyncio trong main thread.
Thread này chỉ cập nhật góc mới nhất (không queue lag).
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

try:
    import websocket
except ImportError as exc:
    raise ImportError("pip install websocket-client") from exc

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TelemetryFrame:
    joint_angle_deg: float
    raw_flex: int = 0
    timestamp: int = 0


@dataclass(slots=True)
class ForceCommand:
    force_level: int
    direction: int = 1


class TwinWebSocketBridge:
    def __init__(self, url: str) -> None:
        self._url = url
        self._lock = threading.Lock()
        self._frame = TelemetryFrame(0.0)
        self._connected = False
        self._outbox: queue.Queue[str] = queue.Queue(maxsize=16)
        self._thread: threading.Thread | None = None
        self._ws_app: websocket.WebSocketApp | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="twin-ws", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._ws_app:
            self._ws_app.close()
        self._connected = False

    def get_frame(self) -> TelemetryFrame:
        with self._lock:
            return TelemetryFrame(
                self._frame.joint_angle_deg,
                self._frame.raw_flex,
                self._frame.timestamp,
            )

    def send_force(self, cmd: ForceCommand) -> None:
        text = json.dumps(
            {
                "force_level": int(cmd.force_level),
                "direction": int(cmd.direction),
                "source": "webots_twin",
            },
            separators=(",", ":"),
        )
        try:
            self._outbox.put_nowait(text)
        except queue.Full:
            try:
                self._outbox.get_nowait()
            except queue.Empty:
                pass
            self._outbox.put_nowait(text)

    def _run(self) -> None:
        while True:
            self._ws_app = websocket.WebSocketApp(
                self._url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self._ws_app.run_forever(ping_interval=20, ping_timeout=10)
            self._connected = False
            time.sleep(2.0)

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        self._connected = True
        logger.info("Connected %s", self._url)
        threading.Thread(target=self._flush, args=(ws,), daemon=True).start()

    def _flush(self, ws: websocket.WebSocketApp) -> None:
        while self._connected:
            try:
                msg = self._outbox.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                ws.send(msg)
            except Exception:
                logger.exception("send failed")

    def _on_message(self, _ws: websocket.WebSocketApp, message: str) -> None:
        try:
            data: dict[str, Any] = json.loads(message)
        except json.JSONDecodeError:
            return
        if data.get("status") == "EMERGENCY_STOP":
            logger.warning("EMERGENCY_STOP")
            return
        angle = data.get("joint_angle", data.get("angle"))
        if angle is None:
            return
        frame = TelemetryFrame(
            joint_angle_deg=float(angle),
            raw_flex=int(data.get("raw_flex", 0)),
            timestamp=int(data.get("timestamp", 0)),
        )
        with self._lock:
            self._frame = frame

    def _on_error(self, _ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.error("WS error: %s", error)

    def _on_close(self, *_args: object) -> None:
        self._connected = False
