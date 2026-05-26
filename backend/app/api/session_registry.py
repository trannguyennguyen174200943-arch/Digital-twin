"""Trạng thái phiên tập luyện đang hoạt động (một hardware tại một thời điểm)."""

from __future__ import annotations

from app.application.services.stream_processor import StreamProcessor

_active_processor: StreamProcessor | None = None
_patient_id: str | None = None


def bind_session(processor: StreamProcessor, patient_id: str | None) -> None:
    global _active_processor, _patient_id
    _active_processor = processor
    _patient_id = patient_id


def clear_session() -> tuple[StreamProcessor | None, str | None]:
    global _active_processor, _patient_id
    processor = _active_processor
    patient_id = _patient_id
    _active_processor = None
    _patient_id = None
    return processor, patient_id


def get_active_processor() -> StreamProcessor | None:
    return _active_processor
