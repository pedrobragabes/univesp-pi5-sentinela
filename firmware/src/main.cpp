#include <Arduino.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <time.h>

#include "sentinel_core.h"

#if __has_include("local_config.h")
#include "local_config.h"
#else
#define SENTINELA_WIFI_SSID "compile-only"
#define SENTINELA_WIFI_PASSWORD "compile-only"
#define SENTINELA_API_URL "http://127.0.0.1:3004/api/v1/readings"
#define SENTINELA_API_KEY "development-only-change-me"
#define SENTINELA_DEVICE_ID "sentinela-compile-01"
#endif

namespace {
constexpr uint8_t kDhtPin = 4;
constexpr uint8_t kDhtType = DHT22;
constexpr unsigned long kSampleIntervalMs = 30000;
constexpr unsigned long kWifiTimeoutMs = 10000;
constexpr time_t kMinimumValidEpoch = 1704067200;  // 2024-01-01 UTC

DHT dht(kDhtPin, kDhtType);
sentinela::EmaFilter temperature_filter(0.25F);
sentinela::EmaFilter humidity_filter(0.25F);
unsigned long last_sample_ms = 0;
uint32_t sequence_number = 0;
uint32_t boot_id = 0;

bool connect_wifi() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(SENTINELA_WIFI_SSID, SENTINELA_WIFI_PASSWORD);
    const unsigned long started = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - started < kWifiTimeoutMs) {
      delay(200);
    }
  }
  if (WiFi.status() != WL_CONNECTED) return false;
  if (time(nullptr) < kMinimumValidEpoch) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  }
  return true;
}

bool send_reading(float temperature_raw, float temperature_filtered,
                  float humidity_raw, float humidity_filtered) {
  if (!connect_wifi()) return false;
  const time_t observed_at = time(nullptr);
  if (observed_at < kMinimumValidEpoch) return false;

  char payload[512];
  const int payload_size = snprintf(payload, sizeof(payload),
           "{\"schema_version\":1,\"device_id\":\"%s\",\"boot_id\":\"%08lx\","
           "\"sequence\":%lu,\"observed_at\":%lld,\"temperature_c_raw\":%.2f,"
           "\"temperature_c_filtered\":%.2f,\"humidity_pct_raw\":%.2f,"
           "\"humidity_pct_filtered\":%.2f,\"rssi_dbm\":%ld}",
           SENTINELA_DEVICE_ID, static_cast<unsigned long>(boot_id),
           static_cast<unsigned long>(sequence_number), static_cast<long long>(observed_at),
           temperature_raw, temperature_filtered, humidity_raw, humidity_filtered,
           static_cast<long>(WiFi.RSSI()));
  if (payload_size < 0 || payload_size >= static_cast<int>(sizeof(payload))) return false;

  HTTPClient http;
  http.setTimeout(5000);
  if (!http.begin(SENTINELA_API_URL)) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", SENTINELA_API_KEY);
  const int status = http.POST(reinterpret_cast<uint8_t*>(payload), strlen(payload));
  http.end();
  return status == 200 || status == 201;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  dht.begin();
  boot_id = esp_random();
  connect_wifi();
}

void loop() {
  const unsigned long now = millis();
  if (last_sample_ms != 0 && now - last_sample_ms < kSampleIntervalMs) {
    delay(50);
    return;
  }
  last_sample_ms = now;

  const float temperature_raw = dht.readTemperature();
  const float humidity_raw = dht.readHumidity();
  if (!sentinela::is_valid_reading(temperature_raw, humidity_raw)) {
    Serial.println("reading_invalid");
    return;
  }
  const float temperature_filtered = temperature_filter.update(temperature_raw);
  const float humidity_filtered = humidity_filter.update(humidity_raw);
  const bool sent = send_reading(temperature_raw, temperature_filtered, humidity_raw, humidity_filtered);
  Serial.println(sent ? "reading_sent" : "reading_pending");
  if (sent) sequence_number++;
}
