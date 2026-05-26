#pragma once

// ========== Wi-Fi ==========
#define WIFI_SSID "YOUR_SSID"
#define WIFI_PASSWORD "YOUR_PASSWORD"

// ========== WebSocket server ==========
#define WS_HOST "192.168.1.100"
#define WS_PORT 8000
#define WS_PATH "/ws/device"

// ========== PWM haptic (LEDC) + chiều DC driver ==========
#define PWM_PIN 25
#define PWM_CHANNEL 0
#define PWM_FREQ_HZ 5000
#define PWM_RES_BITS 8
#define HAPTIC_DIR_PIN 26       // IN1/DIR trên driver L298N / DRV8833
#define HAPTIC_USE_DIR_PIN 1    // 0 nếu chỉ dùng servo một chiều

// PID mềm: flex ADC làm proxy lực (0–255), tinh chỉnh quanh feedforward
#define HAPTIC_KP 0.35f
#define HAPTIC_KI 0.05f
#define HAPTIC_KD 0.002f
#define HAPTIC_INTEGRAL_MAX 40.0f

// ========== Giới hạn góc khớp an toàn (°) — IMU sau complementary filter ==========
#define SAFETY_ANGLE_MIN_DEG 10.0f    // co quá mức
#define SAFETY_ANGLE_MAX_DEG 170.0f   // duỗi quá mức

// ========== I2C — MPU6050 ==========
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22
#define MPU6050_I2C_ADDR 0x68

// Phạm vi đo (ghi vào thanh ghi 0x1B / 0x1C)
// Gyro ±500 °/s → hệ số 65.5 LSB/(°/s)
// Accel ±4 g    → hệ số 8192 LSB/g
#define MPU_GYRO_FS_SEL 0x08   // ±500 °/s
#define MPU_ACCEL_FS_SEL 0x08  // ±4 g
#define MPU_GYRO_LSB_PER_DPS 65.5f
#define MPU_ACCEL_LSB_PER_G 8192.0f

// ========== Flex sensor (ADC 12-bit ESP32: 0–4095) ==========
#define FLEX_PIN 34          // GPIO34 — input only, an toàn cho divider
#define FLEX_SAMPLES 4       // lấy mẫu trung bình nhanh, giảm nhiễu ADC

// ========== Trục fusion — đổi nếu lắp IMU khác hướng ==========
// Góc khớp chính gửi uplink: pitch (gập duỗi) hoặc roll (xoay cánh tay)
#define FUSION_USE_PITCH 1     // 1 = pitch, 0 = roll

// ========== Bộ lọc bù (Complementary Filter) ==========
// α ∈ (0,1): càng gần 1 → tin gyro (mượt, lọc HF); (1-α) → tin accel (sửa drift)
// τ ≈ dt·(1-α)/α  ; với dt≈0.003s, α=0.98 → cutoff vài Hz cho nhánh accel
#define COMPLEMENTARY_ALPHA 0.98f

// ========== Tần số xử lý & uplink ==========
#define SENSOR_MAX_DT_SEC 0.05f   // bỏ frame nếu dt quá lớn (treo debugger)
#define UPLINK_INTERVAL_MS 30
#define CALIBRATION_SAMPLES 300   // đứng yên khi boot để hiệu chỉnh gyro

// ========== Kết nối lại ==========
#define WIFI_RECONNECT_MS 5000
#define WS_RECONNECT_MS 3000

// Bật mock khi chưa gắn phần cứng (0 = dùng MPU6050 thật)
#define USE_MOCK_SENSORS 0
