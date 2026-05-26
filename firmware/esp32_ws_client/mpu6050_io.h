#pragma once

#include <Arduino.h>

/**
 * Đọc MPU6050 qua I2C (Wire) — không phụ thuộc thư viện ngoài.
 * Trả về gia tốc (g) và tốc độ góc (°/s) đã scale theo config.h.
 */

struct ImuSample {
  float ax, ay, az;       // g
  float gx, gy, gz;       // °/s
};

bool mpu6050Begin();
bool mpu6050Read(ImuSample& out);

/** θ_acc từ vector g (độ) — công thức atan2 chuẩn cho pitch/roll */
float imuPitchFromAccel(float ax, float ay, float az);
float imuRollFromAccel(float ay, float az);

/** Hiệu chỉnh offset gyro tĩnh (đứng yên lúc boot) */
void mpu6050CalibrateGyroStatic(uint16_t samples);
