"""Unit tests — góc torso / vai (không cần webcam)."""

from app.domain.vision.pose_analyzer import (
    compute_shoulder_tilt_deg,
    compute_torso_compensation_deg,
)


def test_vertical_spine_zero_tilt() -> None:
    hip = (100.0, 200.0)
    shoulder = (100.0, 100.0)
    assert compute_torso_compensation_deg(shoulder, hip) < 1.0


def test_leaned_spine_detected() -> None:
    hip = (100.0, 200.0)
    shoulder = (140.0, 100.0)
    tilt = compute_torso_compensation_deg(shoulder, hip)
    assert tilt > 15.0


def test_shoulder_tilt() -> None:
    left = (50.0, 100.0)
    right = (150.0, 120.0)
    assert compute_shoulder_tilt_deg(left, right) > 5.0
