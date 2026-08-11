#pragma once

#include <cmath>

namespace sentinela {

inline bool is_valid_reading(float temperature_c, float humidity_pct) {
  return std::isfinite(temperature_c) && std::isfinite(humidity_pct) &&
         temperature_c >= -40.0F && temperature_c <= 80.0F &&
         humidity_pct >= 0.0F && humidity_pct <= 100.0F;
}

class EmaFilter {
 public:
  explicit EmaFilter(float alpha)
      : alpha_(alpha < 0.0F ? 0.0F : (alpha > 1.0F ? 1.0F : alpha)),
        initialized_(false), value_(0.0F) {}

  float update(float sample) {
    if (!initialized_) {
      value_ = sample;
      initialized_ = true;
    } else {
      value_ = alpha_ * sample + (1.0F - alpha_) * value_;
    }
    return value_;
  }

  bool initialized() const { return initialized_; }
  float value() const { return value_; }

 private:
  float alpha_;
  bool initialized_;
  float value_;
};

}  // namespace sentinela
