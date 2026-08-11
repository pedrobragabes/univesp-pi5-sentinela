from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    temperature_c_raw REAL NOT NULL,
    temperature_c_filtered REAL NOT NULL,
    humidity_pct_raw REAL NOT NULL,
    humidity_pct_filtered REAL NOT NULL,
    rssi_dbm REAL NOT NULL,
    UNIQUE(device_id, boot_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_readings_device_received
ON readings(device_id, received_at DESC);
"""


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript(SCHEMA)
