"""Sinh dữ liệu góc giả lập: gập tay bình thường → mỏi (chậm + giật)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MockSession:
    angles_deg: list[float]
    timestamps_ms: list[int]


def generate_fatigue_session(
    *,
    interval_ms: int = 30,
    healthy_cycles: int = 4,
    fatigued_cycles: int = 4,
    angle_min: float = 15.0,
    angle_max: float = 95.0,
    seed: int = 42,
) -> MockSession:
    """
    Phase khỏe: gập/duỗi nhanh, ít rung.
    Phase mỏi: cùng biên độ nhưng chu kỳ dài gấp ~3× + rung HF (sin) biên độ lớn.
    """
    rng = random.Random(seed)
    angles: list[float] = []
    timestamps: list[int] = []
    t = 0

    def add_phase(
        cycles: int,
        steps_per_half: int,
        dt_ms: int,
        noise_std: float,
        tremor_amp: float,
        tremor_freq: float,
    ) -> None:
        nonlocal t
        for _ in range(cycles):
            for half in (0, 1):  # gập rồi duỗi
                for i in range(steps_per_half):
                    phase = i / max(steps_per_half - 1, 1)
                    if half == 1:
                        phase = 1.0 - phase
                    base = angle_min + (angle_max - angle_min) * (0.5 - 0.5 * math.cos(math.pi * phase))
                    tremor = tremor_amp * math.sin(tremor_freq * (len(angles) + i))
                    noise = rng.gauss(0, noise_std)
                    angles.append(base + tremor + noise)
                    timestamps.append(t)
                    t += dt_ms

    # Khỏe: 14 bước/nửa chu kỳ, 30 ms
    add_phase(
        healthy_cycles,
        steps_per_half=14,
        dt_ms=interval_ms,
        noise_std=0.25,
        tremor_amp=0.15,
        tremor_freq=0.4,
    )
    # Mỏi: 40 bước/nửa chu kỳ (~3× chậm), rung mạnh
    add_phase(
        fatigued_cycles,
        steps_per_half=40,
        dt_ms=interval_ms,
        noise_std=0.4,
        tremor_amp=5.0,
        tremor_freq=1.35,
    )

    return MockSession(angles_deg=angles, timestamps_ms=timestamps)
