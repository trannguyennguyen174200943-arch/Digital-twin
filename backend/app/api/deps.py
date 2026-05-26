from __future__ import annotations

from fastapi import HTTPException

from app.application.services.stream_processor import StreamProcessor
from app.application.services.training_session_service import TrainingSessionService
from app.core.config import Settings, get_settings
from app.infrastructure.websocket.connection_manager import ConnectionManager

_manager = ConnectionManager()
_session_service = TrainingSessionService()


def get_connection_manager() -> ConnectionManager:
    return _manager


def get_stream_processor() -> StreamProcessor:
    from app.api.session_registry import get_active_processor

    processor = get_active_processor()
    if processor is None:
        raise HTTPException(status_code=409, detail="No active hardware training session")
    return processor


def get_training_session_service() -> TrainingSessionService:
    return _session_service


def get_settings_dep() -> Settings:
    return get_settings()
