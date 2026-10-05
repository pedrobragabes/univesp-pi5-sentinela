from __future__ import annotations

import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

from sentinela.database import connect
from sentinela.validation import PayloadError, validate_payload
from sentinela.web import create_app
from simulator.send_readings import build_payload


class SentinelaTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "test.db"
        self.key = "test-device-key"
        self.client = create_app(self.database, self.key).test_client()

    def tearDown(self):
        self.temporary.cleanup()

    def post(self, payload: dict, key: str | None = None):
        return self.client.post(
            "/api/v1/readings",
            json=payload,
            headers={"X-Device-Key": self.key if key is None else key},
        )

    def test_requires_device_key(self):
        response = self.post(build_payload(1), key="wrong")
        self.assertEqual(response.status_code, 401)

    def test_accepts_and_deduplicates_reading(self):
        payload = build_payload(2)
        first = self.post(payload)
        duplicate = self.post(payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.get_json()["status"], "accepted")
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.get_json()["status"], "duplicate")
        with connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 1)

    def test_conflicting_sequence_never_acknowledges_a_different_measurement(self):
        payload = build_payload(20)
        accepted = self.post(payload)
        self.assertEqual(accepted.status_code, 201)
        for field, value in {
            "observed_at": payload["observed_at"] - 1,
            "temperature_c_raw": 30,
            "temperature_c_filtered": 31,
            "humidity_pct_raw": 40,
            "humidity_pct_filtered": 41,
            "rssi_dbm": -70,
        }.items():
            with self.subTest(field=field):
                conflict = self.post({**payload, field: value})
                self.assertEqual(conflict.status_code, 409)
                self.assertEqual(conflict.get_json()["status"], "conflict")
        with connect(self.database) as connection:
            row = connection.execute("SELECT * FROM readings").fetchone()
            self.assertEqual(row["temperature_c_raw"], payload["temperature_c_raw"])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 1)

    def test_retry_after_restart_returns_the_same_correlated_receipt(self):
        payload = build_payload(21)
        first = self.post(payload).get_json()
        restarted = create_app(self.database, self.key).test_client()
        duplicate = restarted.post("/api/v1/readings", json=payload,
                                   headers={"X-Device-Key": self.key})
        self.assertEqual(duplicate.status_code, 200)
        receipt = duplicate.get_json()
        self.assertEqual(receipt["id"], first["id"])
        for field in ("device_id", "boot_id", "sequence"):
            self.assertEqual(receipt[field], payload[field])

    def test_committed_retry_remains_acknowledgeable_after_clock_window(self):
        payload = build_payload(22)
        self.assertEqual(self.post(payload).status_code, 201)
        future = datetime.fromtimestamp(payload["observed_at"] + 90_000, timezone.utc)
        with patch("sentinela.validation.datetime") as clock:
            clock.now.return_value = future
            clock.fromtimestamp.side_effect = datetime.fromtimestamp
            duplicate = self.post(payload)
            new = self.post({**payload, "sequence": 23})
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(new.status_code, 422)

    def test_concurrent_conflicting_messages_store_only_one_measurement(self):
        first = build_payload(24)
        second = {**first, "temperature_c_raw": 35}
        app = create_app(self.database, self.key)
        def send(payload):
            with app.test_client() as client:
                return client.post("/api/v1/readings", json=payload,
                                   headers={"X-Device-Key": self.key}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(send, (first, second)))
        self.assertCountEqual(statuses, [201, 409])
        with connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 1)

    def test_non_ascii_wrong_key_is_a_controlled_authentication_failure(self):
        self.assertEqual(self.post(build_payload(25), key="chave-inválida").status_code, 401)

    def test_schema_version_requires_an_integer(self):
        for version in (True, 1.0, "1", None):
            with self.subTest(version=version):
                self.assertEqual(self.post({**build_payload(26), "schema_version": version}).status_code, 422)

    def test_recent_contact_does_not_make_an_old_measurement_current(self):
        payload = build_payload(27)
        payload["observed_at"] -= 600
        self.assertEqual(self.post(payload).status_code, 201)
        device = self.client.get("/api/v1/status").get_json()["devices"][0]
        self.assertTrue(device["online"])
        self.assertFalse(device["fresh"])
        self.assertGreaterEqual(device["observation_age_seconds"], 600)
        self.assertIn("medição antiga", self.client.get("/").get_data(as_text=True))

    def test_delayed_delivery_does_not_replace_the_latest_observation(self):
        newest = build_payload(28)
        oldest = {**build_payload(29), "observed_at": newest["observed_at"] - 600}
        self.assertEqual(self.post(newest).status_code, 201)
        self.assertEqual(self.post(oldest).status_code, 201)
        device = self.client.get("/api/v1/status").get_json()["devices"][0]
        self.assertEqual(device["sequence"], 28)
        self.assertTrue(device["fresh"])

    def test_ahead_of_time_measurement_is_identified_in_the_dashboard(self):
        payload = build_payload(30)
        payload["observed_at"] += 600
        self.assertEqual(self.post(payload).status_code, 201)
        device = self.client.get("/api/v1/status").get_json()["devices"][0]
        self.assertFalse(device["fresh"])
        self.assertLess(device["observation_age_seconds"], -120)
        self.assertIn("relógio adiantado", self.client.get("/").get_data(as_text=True))

    def test_oversized_body_is_rejected_without_writing(self):
        response = self.client.post("/api/v1/readings", data=" " * 5000,
                                    content_type="application/json",
                                    headers={"X-Device-Key": self.key})
        self.assertEqual(response.status_code, 413)
        self.assertIsInstance(response.get_json(), dict)
        with connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 0)

    def test_importing_factory_does_not_initialize_a_database(self):
        import importlib
        import sentinela.web
        try:
            with patch("sentinela.database.initialize") as initialize:
                importlib.reload(sentinela.web)
                initialize.assert_not_called()
        finally:
            importlib.reload(sentinela.web)

    def test_rejects_unknown_and_out_of_range_values(self):
        payload = build_payload(3)
        payload["unexpected"] = True
        self.assertEqual(self.post(payload).status_code, 422)
        payload = build_payload(3)
        payload["humidity_pct_raw"] = 140
        self.assertEqual(self.post(payload).status_code, 422)

    def test_rejects_clock_outside_window(self):
        payload = build_payload(4)
        payload["observed_at"] = int(time.time()) - 90_000
        with self.assertRaisesRegex(PayloadError, "janela de 24 horas"):
            validate_payload(payload)
        payload["observed_at"] = 99_999_999_999
        with self.assertRaisesRegex(PayloadError, "faixa suportada"):
            validate_payload(payload)

    def test_status_marks_stale_device_offline(self):
        self.post(build_payload(5))
        with connect(self.database) as connection:
            connection.execute("UPDATE readings SET received_at = '2024-01-01T00:00:00+00:00'")
        response = self.client.get("/api/v1/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["devices"][0]["online"])

    def test_dashboard_has_warning_and_security_headers(self):
        response = self.client.get("/")
        content = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("PROTÓTIPO NÃO CERTIFICADO", content)
        self.assertIn("frame-ancestors", response.headers["Content-Security-Policy"])
        self.assertNotIn("style=", content)


if __name__ == "__main__":
    unittest.main()
