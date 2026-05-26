#include "mpu6050_io.h"

#include <Wire.h>

#include "config.h"

namespace {

constexpr uint8_t REG_PWR_MGMT_1 = 0x6B;
constexpr uint8_t REG_GYRO_CONFIG = 0x1B;
constexpr uint8_t REG_ACCEL_CONFIG = 0x1C;
constexpr uint8_t REG_ACCEL_XOUT_H = 0x3B;

float gyroBiasX = 0.0f;
float gyroBiasY = 0.0f;
float gyroBiasZ = 0.0f;

int16_t readWord(uint8_t reg) {
  Wire.beginTransmission(MPU6050_I2C_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return 0;
  }
  if (Wire.requestFrom(static_cast<uint8_t>(MPU6050_I2C_ADDR), static_cast<uint8_t>(2)) != 2) {
    return 0;
  }
  const int16_t hi = Wire.read();
  const int16_t lo = Wire.read();
  return (hi << 8) | lo;
}

}  // namespace

bool mpu6050Begin() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setClock(400000);

  Wire.beginTransmission(MPU6050_I2C_ADDR);
  Wire.write(REG_PWR_MGMT_1);
  Wire.write(0x00);  // wake
  if (Wire.endTransmission() != 0) {
    return false;
  }

  Wire.beginTransmission(MPU6050_I2C_ADDR);
  Wire.write(REG_GYRO_CONFIG);
  Wire.write(MPU_GYRO_FS_SEL);
  Wire.endTransmission();

  Wire.beginTransmission(MPU6050_I2C_ADDR);
  Wire.write(REG_ACCEL_CONFIG);
  Wire.write(MPU_ACCEL_FS_SEL);
  Wire.endTransmission();

  delay(50);
  return true;
}

bool mpu6050Read(ImuSample& out) {
  const int16_t axRaw = readWord(REG_ACCEL_XOUT_H);
  const int16_t ayRaw = readWord(REG_ACCEL_XOUT_H + 2);
  const int16_t azRaw = readWord(REG_ACCEL_XOUT_H + 4);
  const int16_t gxRaw = readWord(REG_ACCEL_XOUT_H + 8);
  const int16_t gyRaw = readWord(REG_ACCEL_XOUT_H + 10);
  const int16_t gzRaw = readWord(REG_ACCEL_XOUT_H + 12);

  if (axRaw == 0 && ayRaw == 0 && azRaw == 0 && gxRaw == 0 && gyRaw == 0 && gzRaw == 0) {
    return false;
  }

  out.ax = static_cast<float>(axRaw) / MPU_ACCEL_LSB_PER_G;
  out.ay = static_cast<float>(ayRaw) / MPU_ACCEL_LSB_PER_G;
  out.az = static_cast<float>(azRaw) / MPU_ACCEL_LSB_PER_G;

  out.gx = static_cast<float>(gxRaw) / MPU_GYRO_LSB_PER_DPS - gyroBiasX;
  out.gy = static_cast<float>(gyRaw) / MPU_GYRO_LSB_PER_DPS - gyroBiasY;
  out.gz = static_cast<float>(gzRaw) / MPU_GYRO_LSB_PER_DPS - gyroBiasZ;
  return true;
}

float imuPitchFromAccel(float ax, float ay, float az) {
  // θ_pitch = atan2( ax, sqrt(ay² + az²) ) — góc nghiêng quanh trục Y (rad → °)
  return atan2f(ax, sqrtf(ay * ay + az * az)) * 57.2957795f;
}

float imuRollFromAccel(float ay, float az) {
  // θ_roll = atan2( ay, az )
  return atan2f(ay, az) * 57.2957795f;
}

void mpu6050CalibrateGyroStatic(uint16_t samples) {
  float sumX = 0.0f, sumY = 0.0f, sumZ = 0.0f;
  uint16_t n = 0;

  for (uint16_t i = 0; i < samples; ++i) {
    ImuSample s{};
    if (mpu6050Read(s)) {
      sumX += s.gx;
      sumY += s.gy;
      sumZ += s.gz;
      ++n;
    }
    delay(2);
  }

  if (n > 0) {
    gyroBiasX = sumX / static_cast<float>(n);
    gyroBiasY = sumY / static_cast<float>(n);
    gyroBiasZ = sumZ / static_cast<float>(n);
  }
}
