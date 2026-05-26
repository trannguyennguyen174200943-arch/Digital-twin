"""Làm mượt góc — tránh giật khi uplink ~30 Hz, sim ~60 Hz."""

from __future__ import annotations

import math


class AngleSmoother:
    """Low-pass theo bước: y += (x - y) * (1 - exp(-dt/tau))."""

    def __init__(self, tau_sec: float = 0.04) -> None:
        self._tau = max(tau_sec, 1e-4)
        self._value_deg = 0.0
        self._initialized = False

    def reset(self, deg: float = 0.0) -> None:
        self._value_deg = deg
        self._initialized = True

    def update(self, target_deg: float, dt_sec: float) -> float:
        if not self._initialized:
            self.reset(target_deg)
            return self._value_deg
        if dt_sec <= 0.0:
            return self._value_deg
        alpha = 1.0 - math.exp(-dt_sec / self._tau)
        self._value_deg += (target_deg - self._value_deg) * alpha
        return self._value_deg

    @property
    def value_deg(self) -> float:
        return self._value_deg


def deg_to_rad(deg: float, offset_deg: float, sign: float) -> float:
    return sign * (deg + offset_deg) * math.pi / 180.0
