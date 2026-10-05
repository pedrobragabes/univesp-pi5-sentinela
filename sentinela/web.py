from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

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
    app.config["MAX_CONTENT_LENGTH"] = 4096
    app.config["DEVICE_KEY"] = device_key or os.getenv("SENTINELA_DEVICE_KEY", DEFAULT_DEVELOPMENT_KEY)
    initialize(app.config["DATABASE"])

    @app.errorhandler(RequestEntityTooLarge)
    def oversized_body(_error):
        return jsonify({"error": "Mensagem excede o limite de 4096 bytes."}), 413

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
        if not hmac.compare_digest(supplied_key.encode("utf-8"), app.config["DEVICE_KEY"].encode("utf-8")):
            return jsonify({"error": "Credencial do dispositivo inválida."}), 401
        try:
            payload = request.get_json(silent=True)
            reading = validate_payload(payload, check_freshness=False)
            received_at = datetime.now(timezone.utc).isoformat()
            with connect(app.config["DATABASE"]) as connection:
                # Reserve the write transaction before looking up the identity.
                # Concurrent deliveries cannot both accept different contents.
                connection.execute("BEGIN IMMEDIATE")
                previous = connection.execute(
                    "SELECT * FROM readings WHERE device_id = ? AND boot_id = ? AND sequence = ?",
                    (reading["device_id"], reading["boot_id"], reading["sequence"]),
                ).fetchone()
                if previous is not None:
                    if any(previous[field] != value for field, value in reading.items()
                           if field != "schema_version"):
                        return jsonify({"status": "conflict", "error": "Sequência já utilizada por outra leitura."}), 409
                    reading_id = previous["id"]
                    status, code = "duplicate", 200
                else:
                    # A stored exact retry remains valid after the clock window;
                    # a new observation must still satisfy the 24-hour limit.
                    validate_payload(payload)
                    columns = [field for field in reading if field != "schema_version"]
                    cursor = connection.execute(
                        "INSERT INTO readings (" + ", ".join(columns) + ", received_at) "
                        "VALUES (" + ", ".join("?" for _ in columns) + ", ?)",
                        tuple(reading[field] for field in columns) + (received_at,),
                    )
                    reading_id = cursor.lastrowid
                    status, code = "accepted", 201
        except PayloadError:
            return jsonify({"error": "Leitura rejeitada pelo contrato de telemetria."}), 422
        except (OverflowError, OSError):
            return jsonify({"error": "Leitura inválida ou fora da faixa suportada."}), 422

        return jsonify({"id": reading_id, "status": status,
                        "device_id": reading["device_id"], "boot_id": reading["boot_id"],
                        "sequence": reading["sequence"]}), code

    def dashboard_data() -> tuple[list[dict], list[dict]]:
        with connect(app.config["DATABASE"]) as connection:
            latest = connection.execute(
                """SELECT * FROM (
                    SELECT r.*, MAX(received_at) OVER (PARTITION BY device_id) AS last_received_at,
                    ROW_NUMBER() OVER (PARTITION BY device_id
                        ORDER BY observed_at DESC, received_at DESC, id DESC) AS observation_rank
                    FROM readings r
                ) WHERE observation_rank = 1 ORDER BY device_id"""
            ).fetchall()
            readings = connection.execute(
                "SELECT * FROM readings ORDER BY id DESC LIMIT 30"
            ).fetchall()
        now = datetime.now(timezone.utc)
        devices = []
        for row in latest:
            item = dict(row)
            item.pop("observation_rank")
            age_seconds = max(0, int((now - datetime.fromisoformat(item["last_received_at"])).total_seconds()))
            observation_age = int((now - datetime.fromisoformat(item["observed_at"])).total_seconds())
            item["age_seconds"] = age_seconds
            item["online"] = age_seconds <= 120
            item["observation_age_seconds"] = observation_age
            item["fresh"] = abs(observation_age) <= 120
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


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=3004, debug=False)
