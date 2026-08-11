from __future__ import annotations

import hmac
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from sentinela.database import connect, initialize
from sentinela.validation import PayloadError, validate_payload

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "sentinela.db"
DEFAULT_DEVELOPMENT_KEY = "development-only-change-me"


def create_app(database_path: Path = DEFAULT_DATABASE, device_key: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.config["DATABASE"] = Path(database_path)
    app.config["DEVICE_KEY"] = device_key or os.getenv("SENTINELA_DEVICE_KEY", DEFAULT_DEVELOPMENT_KEY)
    initialize(app.config["DATABASE"])

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; style-src 'self'"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.post("/api/v1/readings")
    def receive_reading():
        supplied_key = request.headers.get("X-Device-Key", "")
        if not hmac.compare_digest(supplied_key, app.config["DEVICE_KEY"]):
            return jsonify({"error": "Credencial do dispositivo inválida."}), 401
        try:
            reading = validate_payload(request.get_json(silent=True))
        except PayloadError:
            return jsonify({"error": "Leitura rejeitada pelo contrato de telemetria."}), 422
        except (OverflowError, OSError):
            return jsonify({"error": "Leitura inválida ou fora da faixa suportada."}), 422

        received_at = datetime.now(timezone.utc).isoformat()
        try:
            with connect(app.config["DATABASE"]) as connection:
                cursor = connection.execute(
                    """INSERT INTO readings (
                        device_id, boot_id, sequence, observed_at, received_at,
                        temperature_c_raw, temperature_c_filtered,
                        humidity_pct_raw, humidity_pct_filtered, rssi_dbm
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        reading["device_id"], reading["boot_id"], reading["sequence"],
                        reading["observed_at"], received_at,
                        reading["temperature_c_raw"], reading["temperature_c_filtered"],
                        reading["humidity_pct_raw"], reading["humidity_pct_filtered"], reading["rssi_dbm"],
                    ),
                )
                reading_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return jsonify({"status": "duplicate"}), 200
        return jsonify({"id": reading_id, "status": "accepted"}), 201

    def dashboard_data() -> tuple[list[dict], list[dict]]:
        with connect(app.config["DATABASE"]) as connection:
            latest = connection.execute(
                """SELECT r.* FROM readings r
                JOIN (SELECT device_id, MAX(id) AS id FROM readings GROUP BY device_id) last
                ON r.id = last.id ORDER BY r.device_id"""
            ).fetchall()
            readings = connection.execute(
                "SELECT * FROM readings ORDER BY id DESC LIMIT 30"
            ).fetchall()
        now = datetime.now(timezone.utc)
        devices = []
        for row in latest:
            item = dict(row)
            age_seconds = max(0, int((now - datetime.fromisoformat(item["received_at"])).total_seconds()))
            item["age_seconds"] = age_seconds
            item["online"] = age_seconds <= 120
            devices.append(item)
        return devices, [dict(row) for row in readings]

    @app.get("/")
    def dashboard():
        devices, readings = dashboard_data()
        return render_template("dashboard.html", devices=devices, readings=readings, development_key=app.config["DEVICE_KEY"] == DEFAULT_DEVELOPMENT_KEY)

    @app.get("/api/v1/status")
    def status():
        devices, readings = dashboard_data()
        return jsonify({"devices": devices, "readings": readings})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3004, debug=False)
