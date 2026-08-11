#include <unity.h>

#include <cmath>

#include "sentinel_core.h"

void test_valid_ranges() {
  TEST_ASSERT_TRUE(sentinela::is_valid_reading(24.0F, 55.0F));
  TEST_ASSERT_TRUE(sentinela::is_valid_reading(-40.0F, 0.0F));
  TEST_ASSERT_FALSE(sentinela::is_valid_reading(81.0F, 50.0F));
  TEST_ASSERT_FALSE(sentinela::is_valid_reading(20.0F, 101.0F));
  TEST_ASSERT_FALSE(sentinela::is_valid_reading(NAN, 50.0F));
}

void test_ema_uses_first_sample_as_initial_value() {
  sentinela::EmaFilter filter(0.25F);
  TEST_ASSERT_FALSE(filter.initialized());
  TEST_ASSERT_FLOAT_WITHIN(0.001F, 20.0F, filter.update(20.0F));
  TEST_ASSERT_TRUE(filter.initialized());
}

void test_ema_smooths_second_sample() {
  sentinela::EmaFilter filter(0.25F);
  filter.update(20.0F);
  TEST_ASSERT_FLOAT_WITHIN(0.001F, 22.0F, filter.update(28.0F));
}

void test_ema_clamps_invalid_alpha() {
  sentinela::EmaFilter filter(2.0F);
  filter.update(10.0F);
  TEST_ASSERT_FLOAT_WITHIN(0.001F, 20.0F, filter.update(20.0F));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_valid_ranges);
  RUN_TEST(test_ema_uses_first_sample_as_initial_value);
  RUN_TEST(test_ema_smooths_second_sample);
  RUN_TEST(test_ema_clamps_invalid_alpha);
  return UNITY_END();
}
