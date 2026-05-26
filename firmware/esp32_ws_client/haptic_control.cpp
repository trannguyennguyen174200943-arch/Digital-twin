#include "haptic_control.h"

#include "config.h"
#include "safety_layer.h"

namespace {

// --- Setpoint từ server (volatile: ghi trong WS callback) ---
volatile uint8_t cmdForce = 0;
volatile int8_t cmdDir = 0;

uint8_t currentDuty = 0;
int8_t appliedDir = 0;

// --- PID trên proxy: flex ADC → "lực" 0..255 ---
float integral = 0.0f;
float prevError = 0.0f;

constexpr float kFlexTo255 = 255.0f / 4095.0f;

inline float flexToForceProxy(int rawFlex) {
  return static_cast<float>(rawFlex) * kFlexTo255;
}

/**
 * Một bước PID: u = Kp·e + Ki·∫e + Kd·de/dt
 * e = force_cmd − flex_proxy  (đóng vòng mềm, không cần load cell)
 */
uint8_t pidDuty(uint8_t forceCmd, int rawFlex, float dt, int8_t dir) {
  if (dir == 0 || dt <= 0.0f) {
    integral = 0.0f;
    prevError = 0.0f;
    return 0;
  }

  const float target = static_cast<float>(forceCmd);
  const float measured = flexToForceProxy(rawFlex);
  const float error = target - measured;

  integral += error * dt;
  if (integral > HAPTIC_INTEGRAL_MAX) {
    integral = HAPTIC_INTEGRAL_MAX;
  } else if (integral < -HAPTIC_INTEGRAL_MAX) {
    integral = -HAPTIC_INTEGRAL_MAX;
  }

  const float derivative = (error - prevError) / dt;
  prevError = error;

  const float u = HAPTIC_KP * error + HAPTIC_KI * integral + HAPTIC_KD * derivative;
  const int duty = static_cast<int>(target + u + 0.5f);
  if (duty < 0) {
    return 0;
  }
  if (duty > 255) {
    return 255;
  }
  return static_cast<uint8_t>(duty);
}

/** Ghi phần cứng — duy nhất chỗ gọi ledcWrite (độ trễ cực thấp). */
inline void writeMotorHw(uint8_t duty, int8_t dir) {
#if HAPTIC_USE_DIR_PIN
  if (dir < 0) {
    digitalWrite(HAPTIC_DIR_PIN, LOW);
  } else if (dir > 0) {
    digitalWrite(HAPTIC_DIR_PIN, HIGH);
  }
#endif
  ledcWrite(PWM_CHANNEL, duty);
  currentDuty = duty;
  appliedDir = dir;
}

}  // namespace

void hapticBegin() {
  pinMode(PWM_PIN, OUTPUT);
  ledcSetup(PWM_CHANNEL, PWM_FREQ_HZ, PWM_RES_BITS);
  ledcAttachPin(PWM_PIN, PWM_CHANNEL);

#if HAPTIC_USE_DIR_PIN
  pinMode(HAPTIC_DIR_PIN, OUTPUT);
  digitalWrite(HAPTIC_DIR_PIN, LOW);
#endif

  cmdForce = 0;
  cmdDir = 0;
  integral = 0.0f;
  prevError = 0.0f;
  writeMotorHw(0, 0);
}

void hapticEmergencyCut() {
  cmdForce = 0;
  cmdDir = 0;
  integral = 0.0f;
  prevError = 0.0f;
  writeMotorHw(0, 0);
}

bool hapticOnDownlink(uint8_t forceLevel, int8_t direction, float angleDeg, int rawFlex) {
  if (safetyIsLatched()) {
    hapticEmergencyCut();
    return false;
  }

  if (safetyEvaluateAngle(angleDeg) == SafetyEvent::EmergencyTriggered) {
    return false;
  }

  forceLevel = static_cast<uint8_t>(constrain(static_cast<int>(forceLevel), 0, 255));
  direction = static_cast<int8_t>(constrain(static_cast<int>(direction), -1, 1));

  cmdForce = forceLevel;
  cmdDir = direction;

  // Phản hồi <10 ms: feedforward ngay; P-only nhanh (bỏ I,D trong hot path)
  const float measured = flexToForceProxy(rawFlex);
  const float error = static_cast<float>(forceLevel) - measured;
  int duty = static_cast<int>(forceLevel + HAPTIC_KP * error + 0.5f);
  duty = constrain(duty, 0, 255);
  if (direction == 0) {
    duty = 0;
  }

  writeMotorHw(static_cast<uint8_t>(duty), direction);
  return true;
}

void hapticControlTick(float dt, float angleDeg, int rawFlex) {
  if (safetyIsLatched()) {
    if (currentDuty != 0) {
      hapticEmergencyCut();
    }
    return;
  }

  safetyEvaluateAngle(angleDeg);

  if (safetyIsLatched()) {
    return;
  }

  const int8_t dir = cmdDir;
  const uint8_t force = cmdForce;
  const uint8_t duty = pidDuty(force, rawFlex, dt, dir);
  if (duty != currentDuty || dir != appliedDir) {
    writeMotorHw(duty, dir);
  }
}

uint8_t hapticCurrentDuty() { return currentDuty; }
