#pragma once

/**
 * Bộ lọc bù (Complementary Filter) — fusion 1 trục (Pitch hoặc Roll)
 *
 * Mô hình:
 *   - Gia tốc kế: đo góc tuyệt đối θ_acc (hạ tần, nhiễu HF khi chuyển động nhanh).
 *   - Con quay: ω → tích phân θ_gyro = θ_{k-1} + ω·dt (hạ cao, drift dài hạn).
 *
 * Công thức discrete-time (α ∈ (0,1)):
 *
 *   θ̂_k = α · ( θ̂_{k-1} + ω_k · dt ) + (1 − α) · θ_acc,k
 *
 * Tương đương tách tần: α·(high-pass gyro path) + (1−α)·(low-pass accel path).
 * Chọn α ≈ 0.96–0.99 cho khớp ngón/cánh tay (~30–100 Hz uplink, dt chính xác).
 */

class ComplementaryFilter {
 public:
  explicit ComplementaryFilter(float alpha = 0.98f);

  void setAlpha(float alpha);
  void reset(float angleDeg = 0.0f);

  /**
   * @param gyroRateDegPerSec  ω từ MPU6050 (°/s), trục khớp đã map
   * @param accelAngleDeg      θ_acc = atan2(·) từ vector gia tốc (°)
   * @param dt                 Δt (s) từ micros() — bắt buộc > 0
   */
  float update(float gyroRateDegPerSec, float accelAngleDeg, float dt);

  float angleDeg() const { return angleDeg_; }

 private:
  float alpha_;
  float angleDeg_;
};
