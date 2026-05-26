#!/usr/bin/env python3
"""
Demo Động cơ Mỏi cơ — chạy trên terminal (không cần ESP32).

  cd backend
  python scripts/demo_fatigue.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.domain.fatigue.adaptive_haptic_controller import AdaptiveHapticController
from app.domain.fatigue.mock_data import generate_fatigue_session


def main() -> None:
    session = generate_fatigue_session()
    ctrl = AdaptiveHapticController(base_force_level=180, fatigue_threshold=70.0)

    print("=" * 72)
    print("Fatigue Prediction Engine — mock session")
    print(f"Samples: {len(session.angles_deg)} | base force: {ctrl.base_force_level}")
    print("=" * 72)
    print(
        f"{'t(ms)':>8} {'angle':>7} {'|w|':>7} {'tremor':>7} "
        f"{'score':>6} {'force':>6} {'flag':>6}"
    )
    print("-" * 72)

    peak_score = 0.0
    for angle, ts in zip(session.angles_deg, session.timestamps_ms, strict=True):
        state = ctrl.ingest(angle, ts)
        peak_score = max(peak_score, state.fatigue_score)
        feat = state.features
        if feat is None:
            print(f"{ts:8d} {angle:7.1f}   —       —        —      —")
            continue
        flag = "FATIG" if state.fatigue_active else "ok"
        print(
            f"{ts:8d} {angle:7.1f} {feat.angular_velocity_deg_s:7.1f} "
            f"{feat.tremor_index:7.2f} {state.fatigue_score:6.1f} "
            f"{state.adapted_force_level:6d} {flag:>6}"
        )

    print("-" * 72)
    print(f"Peak fatigue score: {peak_score:.1f}")
    if peak_score >= ctrl.fatigue_threshold:
        print("OK: Fatigue >= 70 — force reduced.")
    else:
        print("Note: score < 70 — increase fatigued_cycles or lower threshold.")


if __name__ == "__main__":
    main()
