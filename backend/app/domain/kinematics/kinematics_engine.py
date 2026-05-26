"""
Động học / ROM — lớp miền thuần (không phụ thuộc FastAPI).

Công thức:
  ROM_session = max(angle) − min(angle)   (trong phiên)
  completion_% = min(100, ROM_session / ROM_reference × 100)

  peak_completion_% = min(100, (max(angle) − θ_ref_min) / ROM_reference × 100)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KinematicsSnapshot:
    """Kết quả sau mỗi mẫu góc thô."""

    angle_deg: float
    rom_session_deg: float
    rom_reference_deg: float
    completion_percent: float
    peak_completion_percent: float
    min_angle_deg: float
    max_angle_deg: float


class KinematicsEngine:
    """
    Tích lũy góc khớp → ROM và % hoàn thành so với biên độ chuẩn.

    ROM_reference: biên độ vận động bình thường (ví dụ 140° khủy tay).
  """

    def __init__(
        self,
        reference_rom_deg: float = 140.0,
        reference_angle_min_deg: float = 0.0,
        reference_angle_max_deg: float = 140.0,
    ) -> None:
        if reference_rom_deg <= 0:
            raise ValueError("reference_rom_deg must be positive")
        self._ref_rom = reference_rom_deg
        self._ref_min = reference_angle_min_deg
        self._ref_max = reference_angle_max_deg
        self.reset()

    def reset(self) -> None:
        self._min_obs = float("inf")
        self._max_obs = float("-inf")
        self._sample_count = 0

    @property
    def sample_count(self) -> int:
        return self._sample_count

    @property
    def peak_angle_deg(self) -> float:
        if self._sample_count == 0:
            return 0.0
        return self._max_obs

    @property
    def min_angle_deg(self) -> float:
        if self._sample_count == 0:
            return 0.0
        return self._min_obs

    def update(self, angle_deg: float) -> KinematicsSnapshot:
        self._sample_count += 1
        self._min_obs = min(self._min_obs, angle_deg)
        self._max_obs = max(self._max_obs, angle_deg)

        rom_session = self._max_obs - self._min_obs
        completion = min(100.0, (rom_session / self._ref_rom) * 100.0)

        span_to_peak = self._max_obs - self._ref_min
        peak_completion = min(100.0, max(0.0, (span_to_peak / self._ref_rom) * 100.0))

        return KinematicsSnapshot(
            angle_deg=angle_deg,
            rom_session_deg=rom_session,
            rom_reference_deg=self._ref_rom,
            completion_percent=completion,
            peak_completion_percent=peak_completion,
            min_angle_deg=self._min_obs,
            max_angle_deg=self._max_obs,
        )
