# Cấu hình Digital Twin — sửa theo world của bạn

import os

WS_HOST = os.environ.get("REHAB_WS_HOST", "127.0.0.1")
WS_PORT = int(os.environ.get("REHAB_WS_PORT", "8000"))
WS_PATH = "/ws/twin"

# Motor chính bám góc IMU (joint_angle / angle từ server)
PRIMARY_MOTOR = "joint_motor"
PRIMARY_OFFSET_DEG = 0.0
PRIMARY_SIGN = 1.0

# Motor phụ (tùy chọn): map raw_flex → góc; để "" nếu không dùng
SECONDARY_MOTOR = ""
FLEX_TO_DEG_SCALE = 0.12  # mỗi đơn vị ADC ≈ 0.12°

TOUCH_SENSOR = "finger_touch"

# Làm mượt: hằng số thời gian (s) — nhỏ = bám nhanh, lớn = mượt hơn
SMOOTH_TAU_SEC = 0.04
MAX_MOTOR_VELOCITY = 15.0

# Va chạm → ESP32
FORCE_MIN = 40
FORCE_MAX = 255
COLLISION_RESEND_STEPS = 3
