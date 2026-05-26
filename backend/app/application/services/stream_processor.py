"""Use case: xử lý uplink phần cứng → kinematics + ghi nhận lực cản."""

from __future__ import annotations

from app.application.dto.messages import ForceDownlink, SensorUplink, TwinBroadcast
from app.core.config import Settings
from app.domain.fatigue import AdaptiveHapticController
from app.domain.kinematics import KinematicsEngine, KinematicsSnapshot


class StreamProcessor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine = KinematicsEngine(
            reference_rom_deg=settings.reference_rom_deg,
            reference_angle_min_deg=settings.reference_angle_min_deg,
            reference_angle_max_deg=settings.reference_angle_max_deg,
        )
        self._force_samples: list[int] = []
        self._last_snapshot: KinematicsSnapshot | None = None
        self._applied_force_level: int = 0
        base = settings.fatigue_base_force or settings.default_force_level
        self._fatigue = AdaptiveHapticController(
            base_force_level=base,
            fatigue_threshold=settings.fatigue_threshold,
            safe_force_floor=settings.fatigue_safe_force_floor,
        )
        self._last_fatigue_score = 0.0
        self._fatigue_enabled = settings.fatigue_enabled

    def reset(self) -> None:
        self._engine.reset()
        self._force_samples.clear()
        self._last_snapshot = None
        self._applied_force_level = 0
        self._fatigue.reset()
        self._last_fatigue_score = 0.0

    def set_applied_force(self, level: int) -> None:
        self._applied_force_level = max(0, min(255, level))

    def process_uplink(self, uplink: SensorUplink) -> tuple[TwinBroadcast, KinematicsSnapshot]:
        snap = self._engine.update(uplink.angle)
        self._last_snapshot = snap

        flex_proxy = round(uplink.raw_flex * 255.0 / 4095.0, 1)

        fatigue_score = 0.0
        ang_vel: float | None = None
        tremor: float | None = None
        fatigue_active = False
        if self._fatigue_enabled:
            fstate = self._fatigue.ingest(uplink.angle, uplink.timestamp)
            self._last_fatigue_score = fstate.fatigue_score
            fatigue_score = fstate.fatigue_score
            fatigue_active = fstate.fatigue_active
            if fstate.features:
                ang_vel = fstate.features.angular_velocity_deg_s
                tremor = fstate.features.tremor_index

        broadcast = TwinBroadcast(
            angle=uplink.angle,
            joint_angle=uplink.angle,
            raw_flex=uplink.raw_flex,
            timestamp=uplink.timestamp,
            rom_session_deg=snap.rom_session_deg,
            rom_reference_deg=snap.rom_reference_deg,
            completion_percent=snap.completion_percent,
            peak_completion_percent=snap.peak_completion_percent,
            min_angle_deg=snap.min_angle_deg,
            max_angle_deg=snap.max_angle_deg,
            applied_force_level=self._applied_force_level,
            flex_force_proxy=flex_proxy,
            fatigue_score=fatigue_score,
            angular_velocity_deg_s=ang_vel,
            tremor_index=tremor,
            fatigue_active=fatigue_active,
        )
        return broadcast, snap

    def record_downlink_force(self, downlink: ForceDownlink) -> None:
        self._force_samples.append(downlink.force_level)

    def adaptive_downlink(self) -> ForceDownlink:
        """Lực cản sau khi điều chỉnh theo Fatigue Score."""
        base = self._settings.fatigue_base_force or self._settings.default_force_level
        if self._fatigue_enabled:
            level = self._fatigue.map_force_level(base, self._last_fatigue_score)
        else:
            level = base
        return ForceDownlink(
            force_level=level,
            direction=self._settings.default_force_direction,
        )

    def default_downlink(self) -> ForceDownlink:
        return self.adaptive_downlink()

    @property
    def peak_angle_deg(self) -> float:
        return self._engine.peak_angle_deg

    @property
    def completion_percent(self) -> float:
        if self._last_snapshot is None:
            return 0.0
        return self._last_snapshot.completion_percent

    @property
    def rom_session_deg(self) -> float:
        if self._last_snapshot is None:
            return 0.0
        return self._last_snapshot.rom_session_deg

    def avg_resistance_force(self) -> float:
        if not self._force_samples:
            return 0.0
        return sum(self._force_samples) / len(self._force_samples)
