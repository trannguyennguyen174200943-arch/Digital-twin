#pragma once

#include <Arduino.h>

/**
 * Tầng an toàn ROM — kiểm tra góc khớp (IMU đã lọc).
 * Vi phạm → cắt PWM ngay, khóa điều khiển, báo server (một lần / sự kiện).
 */

enum class SafetyEvent : uint8_t { None, EmergencyTriggered };

void safetyBegin();

/** Góc ngoài [MIN, MAX] → EMERGENCY (idempotent khi đã latched). */
SafetyEvent safetyEvaluateAngle(float angleDeg);

bool safetyIsLatched();
void safetyClearLatch();

/** Gọi sau safetyEvaluateAngle nếu trả về EmergencyTriggered. */
bool safetyConsumeEmergencyNotify();
