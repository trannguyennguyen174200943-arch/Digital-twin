from app.domain.fatigue.adaptive_haptic_controller import AdaptiveHapticController
from app.domain.fatigue.mock_data import generate_fatigue_session


def test_mock_session_triggers_fatigue_reduction() -> None:
    session = generate_fatigue_session()
    ctrl = AdaptiveHapticController(base_force_level=200, fatigue_threshold=70.0)
    states = ctrl.ingest_batch(session.angles_deg, session.timestamps_ms)
    peak = max(s.fatigue_score for s in states)
    last = states[-1]
    assert peak >= 50.0
    if peak >= 70.0:
        assert last.adapted_force_level < last.base_force_level


def test_map_force_linear_above_threshold() -> None:
    ctrl = AdaptiveHapticController(base_force_level=200, fatigue_threshold=70.0)
    assert ctrl.map_force_level(200, 50) == 200
    reduced = ctrl.map_force_level(200, 85.0)
    assert reduced < 200
    assert reduced >= ctrl.safe_force_floor
