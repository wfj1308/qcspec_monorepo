"""Geo and sensor helpers for TripRole execution."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict,
    parse_iso_epoch_ms,
    safe_json_loads,
    sha256_json,
    to_bool,
    to_float,
    to_text,
    utc_iso,
)

MAX_CLIENT_SERVER_SKEW_MS = 5 * 60 * 1000


def normalize_geo_location(raw: Any) -> dict[str, Any]:
    payload = as_dict(raw)
    lat = to_float(payload.get("lat"))
    if lat is None:
        lat = to_float(payload.get("latitude"))
    lng = to_float(payload.get("lng"))
    if lng is None:
        lng = to_float(payload.get("lon"))
    if lng is None:
        lng = to_float(payload.get("longitude"))

    if lat is None or lng is None:
        raise HTTPException(400, "geo_location.lat/lng are required")
    if lat < -90.0 or lat > 90.0 or lng < -180.0 or lng > 180.0:
        raise HTTPException(400, "geo_location out of range")

    accuracy = to_float(payload.get("accuracy_m"))
    altitude = to_float(payload.get("altitude_m"))
    provider = to_text(payload.get("provider") or payload.get("source") or "").strip() or "gps"
    captured_at = to_text(payload.get("captured_at") or payload.get("timestamp") or "").strip()
    if not captured_at:
        raise HTTPException(400, "geo_location.captured_at is required")

    normalized = {
        "lat": round(float(lat), 7),
        "lng": round(float(lng), 7),
        "accuracy_m": round(float(accuracy), 3) if accuracy is not None else None,
        "altitude_m": round(float(altitude), 3) if altitude is not None else None,
        "provider": provider,
        "captured_at": captured_at,
    }
    normalized["geo_fingerprint"] = sha256_json(normalized)
    return normalized


def normalize_server_timestamp_proof(
    raw: Any,
    *,
    now_iso: str,
    action: str,
    input_proof_id: str,
    executor_uri: str,
) -> dict[str, Any]:
    payload = as_dict(raw)
    ntp_server = to_text(payload.get("ntp_server") or payload.get("server") or "").strip()
    if not ntp_server:
        raise HTTPException(400, "server_timestamp_proof.ntp_server is required")

    client_ts = to_text(
        payload.get("client_timestamp")
        or payload.get("captured_at")
        or payload.get("device_time")
        or "",
    ).strip()
    if not client_ts:
        raise HTTPException(400, "server_timestamp_proof.client_timestamp is required")

    offset_ms = to_float(payload.get("ntp_offset_ms"))
    if offset_ms is None:
        offset_ms = to_float(payload.get("offset_ms"))
    if offset_ms is None:
        raise HTTPException(400, "server_timestamp_proof.ntp_offset_ms is required")
    if abs(float(offset_ms)) > 60_000:
        raise HTTPException(400, "server_timestamp_proof.ntp_offset_ms too large")

    rtt_ms = to_float(payload.get("ntp_round_trip_ms"))
    if rtt_ms is None:
        rtt_ms = to_float(payload.get("round_trip_ms"))
    if rtt_ms is None:
        rtt_ms = 0.0

    client_epoch_ms = parse_iso_epoch_ms(client_ts)
    server_epoch_ms = parse_iso_epoch_ms(now_iso)
    if client_epoch_ms is None or server_epoch_ms is None:
        raise HTTPException(400, "invalid timestamp format in server_timestamp_proof")

    skew_ms = abs(server_epoch_ms - client_epoch_ms)
    if skew_ms > MAX_CLIENT_SERVER_SKEW_MS:
        raise HTTPException(
            409,
            f"server_timestamp_proof skew too large: {skew_ms}ms > {MAX_CLIENT_SERVER_SKEW_MS}ms",
        )

    normalized = {
        "client_timestamp": client_ts,
        "server_received_at": now_iso,
        "server_epoch_ms": server_epoch_ms,
        "client_epoch_ms": client_epoch_ms,
        "clock_skew_ms": int(skew_ms),
        "ntp_server": ntp_server,
        "ntp_offset_ms": round(float(offset_ms), 3),
        "ntp_round_trip_ms": round(float(rtt_ms), 3),
        "ntp_sample_id": to_text(payload.get("ntp_sample_id") or "").strip(),
        "ntp_raw_hash": to_text(payload.get("ntp_raw_hash") or "").strip().lower(),
    }
    normalized["timestamp_fingerprint"] = sha256_json(
        {
            "action": action,
            "input_proof_id": input_proof_id,
            "executor_uri": executor_uri,
            **normalized,
        },
    )
    return normalized


def build_spatiotemporal_anchor(
    *,
    action: str,
    input_proof_id: str,
    executor_uri: str,
    now_iso: str,
    geo_location_raw: Any,
    server_timestamp_raw: Any,
) -> dict[str, Any]:
    geo_location = normalize_geo_location(geo_location_raw)
    server_timestamp_proof = normalize_server_timestamp_proof(
        server_timestamp_raw,
        now_iso=now_iso,
        action=action,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
    )
    anchor_hash = sha256_json(
        {
            "action": action,
            "input_proof_id": input_proof_id,
            "executor_uri": executor_uri,
            "geo_fingerprint": geo_location.get("geo_fingerprint"),
            "timestamp_fingerprint": server_timestamp_proof.get("timestamp_fingerprint"),
            "server_received_at": now_iso,
        },
    )
    return {
        "geo_location": geo_location,
        "server_timestamp_proof": server_timestamp_proof,
        "spatiotemporal_anchor_hash": anchor_hash,
    }


def decode_sensor_payload(raw_payload: Any) -> tuple[dict[str, Any], str]:
    if isinstance(raw_payload, dict):
        normalized = dict(raw_payload)
        canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str)
        return normalized, hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    text = to_text(raw_payload).strip()
    if not text:
        raise HTTPException(400, "raw_payload is required")
    if text.startswith("{"):
        parsed = safe_json_loads(text)
        if not parsed:
            raise HTTPException(400, "raw_payload json parse failed")
        return parsed, hashlib.sha256(text.encode("utf-8")).hexdigest()

    padded = text + "=" * (-len(text) % 4)
    try:
        decoded_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
    except Exception:
        raise HTTPException(400, "raw_payload format unsupported")
    decoded_text = decoded_bytes.decode("utf-8", errors="replace").strip()
    parsed = safe_json_loads(decoded_text)
    if not parsed:
        raise HTTPException(400, "raw_payload decode failed")
    return parsed, hashlib.sha256(decoded_bytes).hexdigest()


def extract_values(payload: dict[str, Any]) -> list[float]:
    raw_vals = payload.get("values")
    out: list[float] = []
    if isinstance(raw_vals, list):
        for item in raw_vals:
            num = to_float(item)
            if num is not None:
                out.append(float(num))
        return out

    if isinstance(raw_vals, str):
        parts = re.split(r"[,，;\s\n]+", raw_vals)
        for part in parts:
            num = to_float(part)
            if num is not None:
                out.append(float(num))
        if out:
            return out

    single = to_float(payload.get("value"))
    if single is not None:
        return [float(single)]
    return out


def normalize_sensor_payload(device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    source = as_dict(payload.get("measurement"))
    if not source:
        source = payload
    values = extract_values(source)
    value = to_float(source.get("value") if "value" in source else source.get("measured_value"))
    if value is None and values:
        value = round(float(sum(values) / len(values)), 6)
    if value is None:
        raise HTTPException(400, "sensor payload missing measured value")

    calibration_valid_until = to_text(
        payload.get("calibration_valid_until")
        or payload.get("calibration_expire_at")
        or payload.get("calibration_due_at")
        or "",
    ).strip()
    calibration_epoch = parse_iso_epoch_ms(calibration_valid_until)
    now_epoch = parse_iso_epoch_ms(utc_iso()) or 0
    calibration_valid = (
        calibration_epoch is not None and calibration_epoch >= now_epoch
        if calibration_valid_until
        else to_bool(payload.get("calibration_valid") if "calibration_valid" in payload else True)
    )

    clean_payload = dict(payload)
    for key in ("payload_hash", "packet_hash", "raw_payload_hash", "signature", "token"):
        clean_payload.pop(key, None)

    sensor_hardware = {
        "device_id": to_text(device_id).strip(),
        "device_sn": to_text(
            payload.get("device_sn")
            or payload.get("sn")
            or payload.get("serial_no")
            or payload.get("serial_number")
            or device_id,
        ).strip(),
        "transport": to_text(payload.get("transport") or payload.get("channel") or "ble").strip().lower(),
        "manufacturer": to_text(payload.get("manufacturer") or "").strip(),
        "model": to_text(payload.get("model") or "").strip(),
        "firmware_version": to_text(payload.get("firmware_version") or payload.get("fw_version") or "").strip(),
        "calibration_valid_until": calibration_valid_until,
        "calibration_valid": bool(calibration_valid),
    }
    sensor_hardware["hardware_fingerprint"] = sha256_json(sensor_hardware)

    measured_at = to_text(
        source.get("measured_at")
        or payload.get("measured_at")
        or payload.get("captured_at")
        or source.get("timestamp")
        or payload.get("timestamp")
        or "",
    ).strip()
    if not measured_at:
        measured_at = utc_iso()

    normalized = {
        "boq_item_uri": to_text(
            payload.get("boq_item_uri")
            or payload.get("item_uri")
            or payload.get("boq_uri")
            or "",
        ).strip(),
        "value": round(float(value), 6),
        "values": [round(float(v), 6) for v in values] if values else [round(float(value), 6)],
        "unit": to_text(source.get("unit") or payload.get("unit") or "").strip(),
        "measured_at": measured_at,
        "sensor_hardware": sensor_hardware,
        "sensor_payload": clean_payload,
    }
    normalized["sensor_payload_hash"] = sha256_json(clean_payload)
    normalized["sensor_reading_hash"] = sha256_json(
        {
            "boq_item_uri": normalized["boq_item_uri"],
            "value": normalized["value"],
            "values": normalized["values"],
            "unit": normalized["unit"],
            "measured_at": normalized["measured_at"],
            "hardware_fingerprint": sensor_hardware["hardware_fingerprint"],
        },
    )
    return normalized


__all__ = [
    "MAX_CLIENT_SERVER_SKEW_MS",
    "normalize_geo_location",
    "normalize_server_timestamp_proof",
    "build_spatiotemporal_anchor",
    "decode_sensor_payload",
    "extract_values",
    "normalize_sensor_payload",
]
