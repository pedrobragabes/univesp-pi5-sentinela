#pragma once

#include <ArduinoJson.h>
#include <cstdint>
#include <cstring>

namespace sentinela {

// One immutable RAM slot. Sampling pauses while its receipt is outstanding.
// Rebooting loses the slot; this is deliberately not a persistent queue.
class PendingReading {
 public:
  static constexpr size_t kCapacity = 512;
  static constexpr size_t kMaxReceiptSize = 1024;

  bool capture(const char* body, size_t size) {
    if (pending_ || !body || size == 0 || size >= kCapacity) return false;
    std::memcpy(body_, body, size);
    body_[size] = '\0';
    size_ = size;
    pending_ = true;
    return true;
  }

  bool acknowledge(int code, const char* receipt, size_t size,
                   const char* device_id, const char* boot_id) {
    if (!pending_ || !receipt || size == 0 || size > kMaxReceiptSize ||
        (code != 200 && code != 201)) return false;
    JsonDocument document;
    if (deserializeJson(document, receipt, size, DeserializationOption::NestingLimit(4))) return false;
    if (!document.is<JsonObject>() || !document["status"].is<const char*>() ||
        !document["device_id"].is<const char*>() || !document["boot_id"].is<const char*>() ||
        !document["sequence"].is<uint32_t>() || !document["id"].is<uint64_t>() ||
        document["id"].as<uint64_t>() == 0) return false;
    const char* expected_status = code == 201 ? "accepted" : "duplicate";
    if (std::strcmp(document["status"].as<const char*>(), expected_status) != 0 ||
        std::strcmp(document["device_id"].as<const char*>(), device_id) != 0 ||
        std::strcmp(document["boot_id"].as<const char*>(), boot_id) != 0 ||
        document["sequence"].as<uint32_t>() != sequence_) return false;
    pending_ = false;
    size_ = 0;
    body_[0] = '\0';
    ++sequence_;
    return true;
  }

  bool pending() const { return pending_; }
  const char* body() const { return body_; }
  size_t size() const { return size_; }
  uint32_t sequence() const { return sequence_; }

 private:
  char body_[kCapacity] = {};
  size_t size_ = 0;
  uint32_t sequence_ = 0;
  bool pending_ = false;
};

}  // namespace sentinela
