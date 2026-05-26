"""Unit tests — ROM / completion (không cần FastAPI)."""

from app.domain.kinematics import KinematicsEngine


def test_rom_and_completion() -> None:
    engine = KinematicsEngine(reference_rom_deg=100.0)
    engine.update(10.0)
    snap = engine.update(60.0)
    assert snap.rom_session_deg == 50.0
    assert snap.completion_percent == 50.0
    assert snap.max_angle_deg == 60.0
    assert snap.min_angle_deg == 10.0


def test_completion_caps_at_100() -> None:
    engine = KinematicsEngine(reference_rom_deg=50.0)
    engine.update(0.0)
    snap = engine.update(80.0)
    assert snap.completion_percent == 100.0
