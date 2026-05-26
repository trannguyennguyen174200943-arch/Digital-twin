#pragma once

#include <Arduino.h>

/**
 * Điều khiển haptic: feedforward + PID nhẹ trên proxy lực (raw_flex).
 * Hot path downlink: ledcWrite trong <10 ms (không Serial, không cấp phát).
 */

void hapticBegin();

/** Cắt PWM tức thì — gọi từ safety / mất WS. */
void hapticEmergencyCut();

/**
 * Xử lý downlink — gọi trong WStype_TEXT sau parse JSON.
 * Trả false nếu safety latched (không áp lệnh).
 */
bool hapticOnDownlink(uint8_t forceLevel, int8_t direction, float angleDeg, int rawFlex);

/** Tinh chỉnh PID mỗi loop (dt từ fusion). */
void hapticControlTick(float dt, float angleDeg, int rawFlex);

uint8_t hapticCurrentDuty();
