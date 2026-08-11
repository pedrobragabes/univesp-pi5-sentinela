from __future__ import annotations

import argparse
import json
import math
import os
import random
import secrets
import time
import urllib.request


def build_payload(sequence: int, seed: int = 42, boot_id: str = "51a7e1a0") -> dict:
    randomizer = random.Random(seed + sequence)
    raw_temperature = 24 + math.sin(sequence / 4) * 3 + randomizer.gauss(0, 0.8)
    raw_humidity = 62 - math.sin(sequence / 4) * 8 + randomizer.gauss(0, 2)
    return {
        "schema_version": 1,
        "device_id": "sentinela-sim-01",
        "boot_id": boot_id,
        "sequence": sequence,
        "observed_at": int(time.time()),
        "temperature_c_raw": round(raw_temperature, 2),
        "temperature_c_filtered": round(24 + math.sin(sequence / 4) * 2.4, 2),
        "humidity_pct_raw": round(raw_humidity, 2),
        "humidity_pct_filtered": round(62 - math.sin(sequence / 4) * 6.4, 2),
        "rssi_dbm": round(-58 + randomizer.gauss(0, 2), 1),
    }


def send(url: str, key: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "X-Device-Key": key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Simula telemetria do Sentinela.")
    parser.add_argument("--url", default="http://127.0.0.1:3004/api/v1/readings")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--interval", type=float, default=0.3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    key = os.getenv("SENTINELA_DEVICE_KEY", "development-only-change-me")
    boot_id = secrets.token_hex(4)
    for sequence in range(args.count):
        payload = build_payload(sequence, boot_id=boot_id)
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(send(args.url, key, payload))
        if sequence + 1 < args.count:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
