#include "sensor_fusion.h"

#include <math.h>

#include "config.h"

namespace {

ComplementaryFilter filter(COMPLEMENTARY_ALPHA);
uint64_t lastUpdateUs = 0;
float fusedAngleDeg = 0.0f;
int cachedRawFlex = 0;
bool imuReady = false;

#if USE_MOCK_SENSORS
float mockAngle = 15.0f;
uint32_t mockPhase = 0;
#endif

int readFlexRaw() {
  uint32_t acc = 0;
  for (uint8_t i = 0; i < FLEX_SAMPLES; ++i) {
    acc += static_cast<uint32_t>(analogRead(FLEX_PIN));
  }
  return static_cast<int>(acc / FLEX_SAMPLES);
}

}  // namespace

void sensorFusionBegin() {
  pinMode(FLEX_PIN, INPUT);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);  // ~0–3.3 V full scale

#if !USE_MOCK_SENSORS
  imuReady = mpu6050Begin();
  if (imuReady) {
    Serial.println(F("[IMU] MPU6050 OK — calibrating gyro, keep still..."));
    mpu6050CalibrateGyroStatic(CALIBRATION_SAMPLES);
    Serial.println(F("[IMU] Gyro bias done"));
  } else {
    Serial.println(F("[IMU] MPU6050 init failed — check wiring / I2C addr"));
  }
#else
  imuReady = true;
  Serial.println(F("[IMU] Mock mode"));
#endif

  lastUpdateUs = micros();
  filter.setAlpha(COMPLEMENTARY_ALPHA);
  filter.reset(0.0f);
}

void sensorFusionReset() {
  lastUpdateUs = micros();
  filter.reset(0.0f);
}

bool sensorFusionStep() {
  const uint64_t nowUs = micros();
  float dt = (nowUs - lastUpdateUs) * 1e-6f;
  lastUpdateUs = nowUs;

  if (dt <= 0.0f || dt > SENSOR_MAX_DT_SEC) {
    return false;
  }

#if USE_MOCK_SENSORS
  mockPhase++;
  mockAngle = 45.0f + 25.0f * sinf(mockPhase * 0.02f);
  fusedAngleDeg = filter.update(0.0f, mockAngle, dt);
  cachedRawFlex = readFlexRaw();
  return true;
#else
  if (!imuReady) {
    return false;
  }

  ImuSample imu{};
  if (!mpu6050Read(imu)) {
    return false;
  }

#if FUSION_USE_PITCH
  const float accelAngle = imuPitchFromAccel(imu.ax, imu.ay, imu.az);
  const float gyroRate = imu.gy;  // ω quanh trục Y — đổi nếu lắp khác
#else
  const float accelAngle = imuRollFromAccel(imu.ay, imu.az);
  const float gyroRate = imu.gx;
#endif

  fusedAngleDeg = filter.update(gyroRate, accelAngle, dt);
  cachedRawFlex = readFlexRaw();
  return true;
#endif
}

FusionState sensorFusionSnapshot() {
  FusionState st{};
  st.angle = fusedAngleDeg;
  cachedRawFlex = readFlexRaw();
  st.rawFlex = cachedRawFlex;
  return st;
}

float sensorFusionAngleDeg() { return fusedAngleDeg; }

int sensorFusionRawFlex() { return cachedRawFlex; }
