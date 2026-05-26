"""
Động cơ dự đoán mỏi cơ — Adaptive Haptic Controller.

Đặc trưng:
  - Vận tốc góc ω (°/s) từ dθ/dt
  - Tremor index: độ lệch chuẩn tín hiệu sau khi trừ trung bình trượt (proxy rung cơ)

Fatigue Score 0–100 (rule-based):
  - So sánh |ω| và tremor hiện tại với baseline đầu phiên
  - Score > ngưỡng → giảm force_level tuyến tính
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AngleSample:
    angle_deg: float
    timestamp_ms: int


@dataclass(frozen=True, slots=True)
class MotionFeatures:
    angular_velocity_deg_s: float
    tremor_index: float
    velocity_ratio: float
    tremor_ratio: float


@dataclass(slots=True)
class FatigueState:
    fatigue_score: float
    features: MotionFeatures | None
    adapted_force_level: int
    base_force_level: int
    fatigue_active: bool
    sample_count: int


@dataclass
class AdaptiveHapticController:
    """
    Nhận luồng (angle_deg, timestamp_ms); trả FatigueState sau mỗi mẫu.

    baseline_window: số mẫu đầu dùng hiệu chỉnh "khỏe"
    analysis_window: cửa sổ trượt tính đặc trưng
    """

    base_force_level: int = 128
    fatigue_threshold: float = 70.0
    safe_force_floor: int = 25
    analysis_window: int = 24
    baseline_window: int = 12
    min_dt_ms: float = 5.0

    _samples: deque[AngleSample] = field(default_factory=deque, init=False, repr=False)
    _baseline_speed: float | None = field(default=None, init=False, repr=False)
    _baseline_tremor: float | None = field(default=None, init=False, repr=False)
    _baseline_buffer: list[AngleSample] = field(default_factory=list, init=False, repr=False)

    def reset(self) -> None:
        self._samples.clear()
        self._baseline_speed = None
        self._baseline_tremor = None
        self._baseline_buffer.clear()

    def ingest(self, angle_deg: float, timestamp_ms: int) -> FatigueState:
        sample = AngleSample(angle_deg, timestamp_ms)
        if len(self._baseline_buffer) < self.baseline_window:
            self._baseline_buffer.append(sample)
            if len(self._baseline_buffer) == self.baseline_window:
                self._calibrate_baseline(self._baseline_buffer)

        self._samples.append(sample)
        max_len = max(self.analysis_window, self.baseline_window) + 2
        while len(self._samples) > max_len:
            self._samples.popleft()

        features = self._extract_features()
        score = self._compute_fatigue_score(features)
        adapted = self.map_force_level(self.base_force_level, score)

        return FatigueState(
            fatigue_score=round(score, 1),
            features=features,
            adapted_force_level=adapted,
            base_force_level=self.base_force_level,
            fatigue_active=score >= self.fatigue_threshold,
            sample_count=len(self._samples),
        )

    def ingest_batch(self, angles: list[float], timestamps_ms: list[int]) -> list[FatigueState]:
        if len(angles) != len(timestamps_ms):
            raise ValueError("angles and timestamps_ms must have same length")
        return [
            self.ingest(a, t) for a, t in zip(angles, timestamps_ms, strict=True)
        ]

    def map_force_level(self, base_force: int, fatigue_score: float) -> int:
        """
        Score ≤ 70: giữ nguyên base.
        70 < score ≤ 100: nội suy tuyến tính về safe_force_floor.
        """
        base = max(0, min(255, base_force))
        if fatigue_score <= self.fatigue_threshold:
            return base

        t = (fatigue_score - self.fatigue_threshold) / (100.0 - self.fatigue_threshold)
        t = max(0.0, min(1.0, t))
        target = int(base * (1.0 - t) + self.safe_force_floor * t)
        return max(self.safe_force_floor, min(base, target))

    def _extract_features(self) -> MotionFeatures | None:
        if len(self._samples) < 3:
            return None

        recent = list(self._samples)[-self.analysis_window :]
        raw_angles = [s.angle_deg for s in recent]
        smoothed = self._moving_average(raw_angles, window=5)
        smooth_samples = [
            AngleSample(a, recent[i].timestamp_ms) for i, a in enumerate(smoothed)
        ]
        velocities = self._angular_velocities(smooth_samples)
        if not velocities:
            return None

        abs_vel = sorted(abs(v) for v in velocities)
        # Phân vị 25% — bỏ spike do rung HF khi đo "chậm lại"
        mean_speed = abs_vel[len(abs_vel) // 4]
        tremor = self._tremor_index(raw_angles)

        base_speed = self._baseline_speed or mean_speed
        base_tremor = self._baseline_tremor or max(tremor, 0.5)

        velocity_ratio = mean_speed / max(base_speed, 1e-6)
        tremor_ratio = tremor / max(base_tremor, 1e-6)

        return MotionFeatures(
            angular_velocity_deg_s=mean_speed,
            tremor_index=tremor,
            velocity_ratio=velocity_ratio,
            tremor_ratio=tremor_ratio,
        )

    def _moving_average(self, values: list[float], window: int) -> list[float]:
        n = len(values)
        if n == 0:
            return []
        out: list[float] = []
        for i in range(n):
            lo = max(0, i - window // 2)
            hi = min(n, i + window // 2 + 1)
            out.append(sum(values[lo:hi]) / (hi - lo))
        return out

    def _calibrate_baseline(self, samples: list[AngleSample]) -> None:
        angles = [s.angle_deg for s in samples]
        smooth = self._moving_average(angles, window=5)
        smooth_samples = [
            AngleSample(a, samples[i].timestamp_ms) for i, a in enumerate(smooth)
        ]
        b_vel = self._angular_velocities(smooth_samples)
        if b_vel:
            abs_b = sorted(abs(v) for v in b_vel)
            self._baseline_speed = abs_b[len(abs_b) // 4]
            self._baseline_tremor = max(
                self._tremor_index([s.angle_deg for s in samples]),
                0.5,
            )

    def _angular_velocities(self, samples: list[AngleSample]) -> list[float]:
        out: list[float] = []
        for i in range(1, len(samples)):
            dt = (samples[i].timestamp_ms - samples[i - 1].timestamp_ms) / 1000.0
            if dt * 1000.0 < self.min_dt_ms:
                continue
            d_angle = samples[i].angle_deg - samples[i - 1].angle_deg
            out.append(d_angle / dt)
        return out

    def _tremor_index(self, angles: list[float]) -> float:
        """Độ rung ≈ std(θ − moving_avg) — phương sai tín hiệu HF."""
        n = len(angles)
        if n < 3:
            return 0.0
        window = min(5, n)
        residuals: list[float] = []
        for i in range(n):
            lo = max(0, i - window // 2)
            hi = min(n, i + window // 2 + 1)
            local_mean = sum(angles[lo:hi]) / (hi - lo)
            residuals.append(angles[i] - local_mean)
        mean_r = sum(residuals) / len(residuals)
        var = sum((r - mean_r) ** 2 for r in residuals) / len(residuals)
        return math.sqrt(var)

    def _compute_fatigue_score(self, features: MotionFeatures | None) -> float:
        if features is None:
            return 0.0

        # Chậm lại: velocity_ratio < ~0.85 ; rung: tremor_ratio > 1
        slowdown = max(0.0, min(1.0, (0.85 - features.velocity_ratio) / 0.55))
        tremor_excess = max(0.0, min(1.0, (features.tremor_ratio - 1.0) / 1.5))

        score = 55.0 * slowdown + 45.0 * tremor_excess

        if slowdown > 0.35 and tremor_excess > 0.25:
            score = min(100.0, score + 10.0)

        return max(0.0, min(100.0, score))
