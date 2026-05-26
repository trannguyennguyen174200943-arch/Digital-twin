#include "safety_layer.h"

#include "config.h"
#include "haptic_control.h"

namespace {

volatile bool latched = false;
volatile bool notifyPending = false;

}  // namespace

void safetyBegin() {
  latched = false;
  notifyPending = false;
}

SafetyEvent safetyEvaluateAngle(float angleDeg) {
  if (angleDeg < SAFETY_ANGLE_MIN_DEG || angleDeg > SAFETY_ANGLE_MAX_DEG) {
    if (!latched) {
      latched = true;
      notifyPending = true;
      hapticEmergencyCut();
      Serial.printf(
          F("[SAFETY] EMERGENCY angle=%.1f (limits %.1f–%.1f)\n"),
          angleDeg, SAFETY_ANGLE_MIN_DEG, SAFETY_ANGLE_MAX_DEG);
      return SafetyEvent::EmergencyTriggered;
    }
    hapticEmergencyCut();
    return SafetyEvent::None;
  }
  return SafetyEvent::None;
}

bool safetyIsLatched() { return latched; }

void safetyClearLatch() {
  latched = false;
  notifyPending = false;
}

bool safetyConsumeEmergencyNotify() {
  if (!notifyPending) {
    return false;
  }
  notifyPending = false;
  return true;
}
