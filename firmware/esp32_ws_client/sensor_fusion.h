#pragma once

#include "complementary_filter.h"
#include "mpu6050_io.h"

/** Trạng thái fusion sau mỗi bước cập nhật (dt từ micros). */
struct FusionState {
  float angle;     // ° — pitch hoặc roll đã lọc
  int rawFlex;   // ADC 0–4095
};

void sensorFusionBegin();
void sensorFusionReset();

/** Gọi mỗi vòng loop() — đọc IMU + lọc khi dt hợp lệ. */
bool sensorFusionStep();

/** Lấy góc hiện tại + đọc flex (trung bình nhanh). */
FusionState sensorFusionSnapshot();

/** Góc / flex cache — O(1), dùng trong safety & downlink (<10 ms). */
float sensorFusionAngleDeg();
int sensorFusionRawFlex();
