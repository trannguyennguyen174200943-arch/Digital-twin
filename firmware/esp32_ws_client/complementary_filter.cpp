#include "complementary_filter.h"

ComplementaryFilter::ComplementaryFilter(float alpha) : alpha_(alpha), angleDeg_(0.0f) {}

void ComplementaryFilter::setAlpha(float alpha) {
  if (alpha > 0.0f && alpha < 1.0f) {
    alpha_ = alpha;
  }
}

void ComplementaryFilter::reset(float angleDeg) { angleDeg_ = angleDeg; }

float ComplementaryFilter::update(float gyroRateDegPerSec, float accelAngleDeg, float dt) {
  if (dt <= 0.0f) {
    return angleDeg_;
  }

  // Nhánh gyro (tích phân Euler): θ_pred = θ̂_{k-1} + ω·dt
  const float thetaPred = angleDeg_ + gyroRateDegPerSec * dt;

  // Fusion bù: θ̂_k = α·θ_pred + (1−α)·θ_acc
  angleDeg_ = alpha_ * thetaPred + (1.0f - alpha_) * accelAngleDeg;

  return angleDeg_;
}
