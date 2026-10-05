#include <unity.h>

#include <cmath>

#include "sentinel_core.h"
#include "pending_reading.h"

constexpr const char* kAccepted = "{\"id\":1,\"status\":\"accepted\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"51a7e1a0\",\"sequence\":0}";
constexpr const char* kDuplicate = "{\"id\":1,\"status\":\"duplicate\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"51a7e1a0\",\"sequence\":0}";

void test_lost_receipt_preserves_the_exact_body_and_sequence() {
  sentinela::PendingReading pending;
  const char* first = "{\"observed_at\":1786459200,\"temperature_c_raw\":26.42}";
  TEST_ASSERT_TRUE(pending.capture(first, strlen(first)));
  TEST_ASSERT_FALSE(pending.capture("new measurement", 15));
  TEST_ASSERT_EQUAL_STRING(first, pending.body());
  TEST_ASSERT_EQUAL_UINT32(0, pending.sequence());
  TEST_ASSERT_FALSE(pending.acknowledge(-1, "", 0, "sentinela-test-01", "51a7e1a0"));
  TEST_ASSERT_EQUAL_STRING(first, pending.body());
  TEST_ASSERT_TRUE(pending.acknowledge(200, kDuplicate, strlen(kDuplicate), "sentinela-test-01", "51a7e1a0"));
  TEST_ASSERT_FALSE(pending.pending());
  TEST_ASSERT_EQUAL_UINT32(1, pending.sequence());
  TEST_ASSERT_TRUE(pending.capture("next", 4));
}

void test_only_a_correlated_valid_json_receipt_can_release_the_slot() {
  const char* invalid[] = {
      "<html>OK</html>", "{", "{}", "[]",
      "{\"id\":1,\"status\":\"accepted\",\"device_id\":\"another-device\",\"boot_id\":\"51a7e1a0\",\"sequence\":0}",
      "{\"id\":1,\"status\":\"accepted\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"00000000\",\"sequence\":0}",
      "{\"id\":1,\"status\":\"accepted\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"51a7e1a0\",\"sequence\":1}",
      "{\"id\":1,\"status\":\"accepted\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"51a7e1a0\",\"sequence\":false}",
      "{\"id\":1,\"status\":\"accepted\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"51a7e1a0\",\"sequence\":0.0}",
      "{\"status\":\"accepted\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"51a7e1a0\",\"sequence\":0}",
      "{\"id\":0,\"status\":\"accepted\",\"device_id\":\"sentinela-test-01\",\"boot_id\":\"51a7e1a0\",\"sequence\":0}",
  };
  sentinela::PendingReading pending;
  TEST_ASSERT_TRUE(pending.capture("unchanged", 9));
  for (const char* receipt : invalid) {
    TEST_ASSERT_FALSE(pending.acknowledge(201, receipt, strlen(receipt), "sentinela-test-01", "51a7e1a0"));
    TEST_ASSERT_TRUE(pending.pending());
    TEST_ASSERT_EQUAL_STRING("unchanged", pending.body());
  }
  TEST_ASSERT_FALSE(pending.acknowledge(409, kAccepted, strlen(kAccepted), "sentinela-test-01", "51a7e1a0"));
  TEST_ASSERT_FALSE(pending.acknowledge(200, kAccepted, strlen(kAccepted), "sentinela-test-01", "51a7e1a0"));
  TEST_ASSERT_FALSE(pending.acknowledge(201, kDuplicate, strlen(kDuplicate), "sentinela-test-01", "51a7e1a0"));
  TEST_ASSERT_TRUE(pending.acknowledge(201, kAccepted, strlen(kAccepted), "sentinela-test-01", "51a7e1a0"));
  TEST_ASSERT_EQUAL_UINT32(1, pending.sequence());
  TEST_ASSERT_FALSE(pending.acknowledge(201, kAccepted, strlen(kAccepted), "sentinela-test-01", "51a7e1a0"));
}

void test_payload_and_receipt_bounds_do_not_drop_a_pending_measurement() {
  sentinela::PendingReading pending;
  char oversized[sentinela::PendingReading::kCapacity + 1] = {};
  TEST_ASSERT_FALSE(pending.capture(nullptr, 1));
  TEST_ASSERT_FALSE(pending.capture("", 0));
  TEST_ASSERT_FALSE(pending.capture(oversized, sizeof(oversized)));
  TEST_ASSERT_FALSE(pending.pending());
  TEST_ASSERT_TRUE(pending.capture("valid", 5));
  TEST_ASSERT_FALSE(pending.acknowledge(201, kAccepted, 1025, "sentinela-test-01", "51a7e1a0"));
  TEST_ASSERT_TRUE(pending.pending());
}

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
  RUN_TEST(test_lost_receipt_preserves_the_exact_body_and_sequence);
  RUN_TEST(test_only_a_correlated_valid_json_receipt_can_release_the_slot);
  RUN_TEST(test_payload_and_receipt_bounds_do_not_drop_a_pending_measurement);
  return UNITY_END();
}
