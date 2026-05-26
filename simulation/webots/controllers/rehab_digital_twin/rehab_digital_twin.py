"""
Webots Digital Twin — đồng bộ góc khớp qua FastAPI WebSocket.

Chạy trong Webots (không chạy trực tiếp bằng python ngoài):
  controller = rehab_digital_twin

Cấu hình: twin_config.py | WS: REHAB_WS_HOST, REHAB_WS_PORT
"""

from __future__ import annotations

import logging
import os
import sys

from controller import Motor, Robot, TouchSensor

_CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
if _CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, _CONTROLLER_DIR)

from motion import AngleSmoother, deg_to_rad
from twin_config import (
    COLLISION_RESEND_STEPS,
    FLEX_TO_DEG_SCALE,
    FORCE_MAX,
    FORCE_MIN,
    MAX_MOTOR_VELOCITY,
    PRIMARY_MOTOR,
    PRIMARY_OFFSET_DEG,
    PRIMARY_SIGN,
    SECONDARY_MOTOR,
    SMOOTH_TAU_SEC,
    TOUCH_SENSOR,
    WS_HOST,
    WS_PATH,
    WS_PORT,
)
from ws_bridge import ForceCommand, TwinWebSocketBridge

logging.basicConfig(level=logging.INFO, format="[twin] %(message)s")
log = logging.getLogger("rehab_digital_twin")


class RehabDigitalTwin:
    def __init__(self) -> None:
        self.robot = Robot()
        self.dt_ms = int(self.robot.getBasicTimeStep())
        self.dt_s = self.dt_ms / 1000.0

        self.motor_primary: Motor = self.robot.getDevice(PRIMARY_MOTOR)
        self.motor_primary.setVelocity(MAX_MOTOR_VELOCITY)
        self.motor_primary.setPosition(0.0)

        self.motor_secondary: Motor | None = None
        if SECONDARY_MOTOR:
            try:
                self.motor_secondary = self.robot.getDevice(SECONDARY_MOTOR)
                self.motor_secondary.setVelocity(MAX_MOTOR_VELOCITY)
            except Exception:
                log.warning("Secondary motor '%s' not found", SECONDARY_MOTOR)

        self.touch: TouchSensor | None = None
        try:
            self.touch = self.robot.getDevice(TOUCH_SENSOR)
            self.touch.enable(self.dt_ms)
        except Exception:
            log.warning("TouchSensor '%s' not found", TOUCH_SENSOR)

        self.smoother = AngleSmoother(SMOOTH_TAU_SEC)
        self.flex_smoother = AngleSmoother(SMOOTH_TAU_SEC * 1.2)

        url = f"ws://{WS_HOST}:{WS_PORT}{WS_PATH}"
        self.bridge = TwinWebSocketBridge(url)
        self.bridge.start()

        self._collision_steps = 0
        self._was_touching = False

        log.info("Ready dt=%dms | WS %s | motor=%s", self.dt_ms, url, PRIMARY_MOTOR)

    def _apply_motor_rad(self, motor: Motor, rad: float) -> None:
        motor.setPosition(rad)

    def _collision_force(self, strength: float) -> int:
        if strength <= 0.0:
            return 0
        if strength <= 1.0:
            return FORCE_MIN
        return min(
            FORCE_MAX,
            int(FORCE_MIN + min(strength, 100.0) * (FORCE_MAX - FORCE_MIN) / 100.0),
        )

    def _handle_collision(self, strength: float) -> None:
        if strength <= 0.0:
            if self._was_touching:
                self.bridge.send_force(ForceCommand(0, 0))
            self._was_touching = False
            self._collision_steps = 0
            return

        self._collision_steps += 1
        if (not self._was_touching) or self._collision_steps >= COLLISION_RESEND_STEPS:
            self.bridge.send_force(ForceCommand(self._collision_force(strength), 1))
            self._collision_steps = 0
        self._was_touching = True

    def step_once(self) -> int:
        if self.robot.step(self.dt_ms) == -1:
            return -1

        frame = self.bridge.get_frame()
        smooth_deg = self.smoother.update(frame.joint_angle_deg, self.dt_s)
        rad = deg_to_rad(smooth_deg, PRIMARY_OFFSET_DEG, PRIMARY_SIGN)
        self._apply_motor_rad(self.motor_primary, rad)

        if self.motor_secondary is not None and frame.raw_flex > 0:
            flex_deg = self.flex_smoother.update(frame.raw_flex * FLEX_TO_DEG_SCALE, self.dt_s)
            rad2 = deg_to_rad(flex_deg, 0.0, PRIMARY_SIGN)
            self._apply_motor_rad(self.motor_secondary, rad2)

        if self.touch:
            self._handle_collision(float(self.touch.getValue()))

        return 0

    def run(self) -> None:
        try:
            while self.step_once() != -1:
                pass
        finally:
            self.bridge.stop()
            self.motor_primary.setPosition(0.0)
            self.robot.step(self.dt_ms)


def main() -> None:
    RehabDigitalTwin().run()


if __name__ == "__main__":
    main()
