"""Cấu hình ứng dụng — đọc từ biến môi trường hoặc .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Rehab Digital Twin — Cyber Layer"
    database_url: str = "sqlite+aiosqlite:///./data/rehab.db"

    # ROM chuẩn người khỏe mạnh (ví dụ: gập khủy tay — chỉnh theo khớp tập luyện)
    reference_rom_deg: float = 140.0
    reference_angle_min_deg: float = 0.0
    reference_angle_max_deg: float = 140.0

    default_force_level: int = 128
    default_force_direction: int = 1

    # Computer Vision — MediaPipe Pose
    pose_enabled: bool = True
    pose_video_source: str = "0"  # 0 = webcam; hoặc đường dẫn file .mp4
    pose_cheat_tilt_deg: float = 15.0
    pose_shoulder_tilt_deg: float = 12.0
    pose_frame_skip: int = 2  # xử lý 1/N frame — giảm CPU

    # Fatigue engine — adaptive haptic
    fatigue_enabled: bool = True
    fatigue_threshold: float = 70.0
    fatigue_base_force: int | None = None  # None → dùng default_force_level
    fatigue_safe_force_floor: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()
