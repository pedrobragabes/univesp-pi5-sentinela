from __future__ import annotations

import math
import re
from datetime import datetime, timezone

DEVICE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")
BOOT_PATTERN = re.compile(r"^[0-9a-f]{8}$")
REQUIRED_FIELDS = {
    "schema_version",
    "device_id",
    "boot_id",
    "sequence",
    "observed_at",
    "temperature_c_raw",
    "temperature_c_filtered",
    "humidity_pct_raw",
    "humidity_pct_filtered",
    "rssi_dbm",
}


class PayloadError(ValueError):
    pass


def _number(payload: dict, field: str, minimum: float, maximum: float) -> float:
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise PayloadError(f"{field} deve ser um número finito.")
    if not minimum <= value <= maximum:
        raise PayloadError(f"{field} deve estar entre {minimum} e {maximum}.")
    return float(value)


def validate_payload(payload: object, now: datetime | None = None) -> dict:
    if not isinstance(payload, dict):
        raise PayloadError("O corpo deve ser um objeto JSON.")
    missing = REQUIRED_FIELDS - payload.keys()
    unknown = payload.keys() - REQUIRED_FIELDS
    if missing:
        raise PayloadError(f"Campos obrigatórios ausentes: {', '.join(sorted(missing))}.")
    if unknown:
        raise PayloadError(f"Campos desconhecidos: {', '.join(sorted(unknown))}.")
    if payload["schema_version"] != 1:
        raise PayloadError("schema_version incompatível.")
    if not isinstance(payload["device_id"], str) or not DEVICE_PATTERN.fullmatch(payload["device_id"]):
        raise PayloadError("device_id inválido.")
    if not isinstance(payload["boot_id"], str) or not BOOT_PATTERN.fullmatch(payload["boot_id"]):
        raise PayloadError("boot_id inválido.")
    sequence = payload["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or not 0 <= sequence <= 4_294_967_295:
        raise PayloadError("sequence inválida.")
    observed_at = payload["observed_at"]
    if isinstance(observed_at, bool) or not isinstance(observed_at, int):
        raise PayloadError("observed_at deve ser um timestamp Unix inteiro.")
    if not 0 <= observed_at <= 4_102_444_800:
        raise PayloadError("observed_at está fora da faixa suportada.")
    clock = now or datetime.now(timezone.utc)
    observed = datetime.fromtimestamp(observed_at, timezone.utc)
    if abs((clock - observed).total_seconds()) > 86_400:
        raise PayloadError("observed_at está fora da janela de 24 horas.")

    cleaned = {
        "schema_version": 1,
        "device_id": payload["device_id"],
        "boot_id": payload["boot_id"],
        "sequence": sequence,
        "observed_at": observed.isoformat(),
        "temperature_c_raw": _number(payload, "temperature_c_raw", -40, 80),
        "temperature_c_filtered": _number(payload, "temperature_c_filtered", -40, 80),
        "humidity_pct_raw": _number(payload, "humidity_pct_raw", 0, 100),
        "humidity_pct_filtered": _number(payload, "humidity_pct_filtered", 0, 100),
        "rssi_dbm": _number(payload, "rssi_dbm", -120, 0),
    }
    return cleaned
