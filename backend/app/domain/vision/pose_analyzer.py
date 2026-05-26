"""
Phân tích tư thế MediaPipe Pose — thuần xử lý ảnh / toán học.

Góc bù trừ thân người (torso compensation):
  Đo độ lệch cột sốn so với phương thẳng đứng trong mặt phẳng ảnh:
    θ = |atan2(Δx, −Δy)| với vector vai_mid → hông_mid (y hướng xuống trong OpenCV).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# MediaPipe landmark indices (PoseLandmark enum values — stable across versions)
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_HIP = 23
RIGHT_HIP = 24


@dataclass(slots=True)
class JointLandmark:
    x: float
    y: float
    z: float
    visibility: float


@dataclass(slots=True)
class PoseFrameResult:
    frame_id: int
    detected: bool
    torso_compensation_deg: float = 0.0
    shoulder_tilt_deg: float = 0.0
    left_elbow_deg: float | None = None
    right_elbow_deg: float | None = None
    cheat_detected: bool = False
    warning: str | None = None
    landmarks: dict[str, JointLandmark] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "pose_frame",
            "frame_id": self.frame_id,
            "detected": self.detected,
            "torso_compensation_deg": round(self.torso_compensation_deg, 2),
            "shoulder_tilt_deg": round(self.shoulder_tilt_deg, 2),
            "left_elbow_deg": (
                round(self.left_elbow_deg, 2) if self.left_elbow_deg is not None else None
            ),
            "right_elbow_deg": (
                round(self.right_elbow_deg, 2) if self.right_elbow_deg is not None else None
            ),
            "cheat_detected": self.cheat_detected,
            "warning": self.warning,
            "landmarks": {
                k: {"x": v.x, "y": v.y, "z": v.z, "visibility": v.visibility}
                for k, v in self.landmarks.items()
            },
        }


def _lm_to_point(landmarks: Any, idx: int, w: int, h: int) -> tuple[float, float, float, float]:
    p = landmarks[idx]
    return p.x * w, p.y * h, p.z, p.visibility


def _angle_deg(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Góc ABC (độ)."""
    bax, bay = a[0] - b[0], a[1] - b[1]
    bcx, bcy = c[0] - b[0], c[1] - b[1]
    norm_ba = math.hypot(bax, bay)
    norm_bc = math.hypot(bcx, bcy)
    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return 0.0
    cos_angle = (bax * bcx + bay * bcy) / (norm_ba * norm_bc)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))


def compute_torso_compensation_deg(
    shoulder_mid: tuple[float, float],
    hip_mid: tuple[float, float],
) -> float:
    """
    Góc lệch cột sốn so với phương thẳng đứng (độ).
    Vector hông → vai; so với trục đứng (−y trong ảnh).
    """
    dx = shoulder_mid[0] - hip_mid[0]
    dy = shoulder_mid[1] - hip_mid[1]
    return abs(math.degrees(math.atan2(dx, -dy + 1e-9)))


def compute_shoulder_tilt_deg(
    left_shoulder: tuple[float, float],
    right_shoulder: tuple[float, float],
) -> float:
    """Góc đường vai so với trục ngang — phát hiện nhún vai / xiên."""
    dx = right_shoulder[0] - left_shoulder[0]
    dy = right_shoulder[1] - left_shoulder[1]
    return abs(math.degrees(math.atan2(dy, dx + 1e-9)))


class PoseAnalyzer:
    """Phân tích một frame BGR OpenCV."""

    def __init__(
        self,
        cheat_tilt_deg: float = 15.0,
        cheat_shoulder_tilt_deg: float = 12.0,
        min_visibility: float = 0.5,
    ) -> None:
        import mediapipe as mp

        self._cheat_tilt = cheat_tilt_deg
        self._cheat_shoulder = cheat_shoulder_tilt_deg
        self._min_vis = min_visibility
        self._pose = mp.solutions.pose.Pose(
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._frame_id = 0

    def close(self) -> None:
        self._pose.close()

    def analyze(self, frame_bgr: Any) -> PoseFrameResult:
        import cv2

        self._frame_id += 1
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._pose.process(rgb)

        if not result.pose_landmarks:
            return PoseFrameResult(frame_id=self._frame_id, detected=False)

        lms = result.pose_landmarks.landmark
        ls = _lm_to_point(lms, LEFT_SHOULDER, w, h)
        rs = _lm_to_point(lms, RIGHT_SHOULDER, w, h)
        le = _lm_to_point(lms, LEFT_ELBOW, w, h)
        re = _lm_to_point(lms, RIGHT_ELBOW, w, h)
        lh = _lm_to_point(lms, LEFT_HIP, w, h)
        rh = _lm_to_point(lms, RIGHT_HIP, w, h)

        vis_ok = min(ls[3], rs[3], lh[3], rh[3]) >= self._min_vis
        if not vis_ok:
            return PoseFrameResult(
                frame_id=self._frame_id,
                detected=False,
                warning="Landmark visibility too low",
            )

        shoulder_mid = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
        hip_mid = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)

        torso_deg = compute_torso_compensation_deg(shoulder_mid, hip_mid)
        shoulder_tilt = compute_shoulder_tilt_deg((ls[0], ls[1]), (rs[0], rs[1]))

        left_elbow = _angle_deg((ls[0], ls[1]), (le[0], le[1]), (lh[0], lh[1]))
        right_elbow = _angle_deg((rs[0], rs[1]), (re[0], re[1]), (rh[0], rh[1]))

        cheat = torso_deg > self._cheat_tilt or shoulder_tilt > self._cheat_shoulder
        warning: str | None = None
        if torso_deg > self._cheat_tilt:
            warning = f"Sai tư thế: nghiêng thân {torso_deg:.1f}° (ngưỡng {self._cheat_tilt}°)"
        elif shoulder_tilt > self._cheat_shoulder:
            warning = f"Sai tư thế: vai xiên {shoulder_tilt:.1f}° (ngưỡng {self._cheat_shoulder}°)"

        landmarks = {
            "left_shoulder": JointLandmark(ls[0], ls[1], ls[2], ls[3]),
            "right_shoulder": JointLandmark(rs[0], rs[1], rs[2], rs[3]),
            "left_elbow": JointLandmark(le[0], le[1], le[2], le[3]),
            "right_elbow": JointLandmark(re[0], re[1], re[2], re[3]),
            "left_hip": JointLandmark(lh[0], lh[1], lh[2], lh[3]),
            "right_hip": JointLandmark(rh[0], rh[1], rh[2], rh[3]),
            "spine_mid": JointLandmark(
                (shoulder_mid[0] + hip_mid[0]) / 2,
                (shoulder_mid[1] + hip_mid[1]) / 2,
                (ls[2] + lh[2]) / 2,
                min(ls[3], lh[3]),
            ),
        }

        return PoseFrameResult(
            frame_id=self._frame_id,
            detected=True,
            torso_compensation_deg=torso_deg,
            shoulder_tilt_deg=shoulder_tilt,
            left_elbow_deg=left_elbow,
            right_elbow_deg=right_elbow,
            cheat_detected=cheat,
            warning=warning,
            landmarks=landmarks,
        )
