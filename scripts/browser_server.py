"""Loopback browser fixture using only a disposable synthetic database."""
import tempfile
from pathlib import Path

from flask import render_template

from sentinela.database import connect
from sentinela.web import create_app
from simulator.send_readings import build_payload


def main():
    with tempfile.TemporaryDirectory(prefix="sentinela-browser-") as directory:
        app = create_app(Path(directory) / "fixture.db", "browser-fixture-only")
        @app.get("/empty-fixture")
        def empty():
            return render_template("dashboard.html", devices=[], readings=[], development_key=True)

        client = app.test_client()
        for index, device in enumerate(("sentinela-recent-01", "sentinela-old-01", "sentinela-offline-01", "sentinela-clock-abcdefghijklmnopqrstuvwx")):
            payload = build_payload(index)
            payload["device_id"] = device
            if index in (1, 2):
                payload["observed_at"] -= 600
            elif index == 3:
                payload["observed_at"] += 600
            response = client.post("/api/v1/readings", json=payload,
                                   headers={"X-Device-Key": "browser-fixture-only"})
            assert response.status_code == 201
        with connect(app.config["DATABASE"]) as connection:
            connection.execute("UPDATE readings SET received_at = '2024-01-01T00:00:00+00:00' WHERE device_id = 'sentinela-offline-01'")

        app.run(host="127.0.0.1", port=3486, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
