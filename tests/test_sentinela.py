from __future__ import annotations

import tempfile
import time
import unittest
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
