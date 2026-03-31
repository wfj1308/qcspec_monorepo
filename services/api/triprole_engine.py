"""
TripRole lifecycle execution + provenance aggregation service.

Implements:
- TripRole action executor (quality.check / measure.record / variation.record / settlement.confirm)
- aggregate_provenance_chain(utxo_id)
- Gate locking for settlement (FAIL blocks unless compensated by VARIATION)
- DocFinal package builder by BOQ item URI
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
from typing import Any
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from services.api.boq_utxo_service import resolve_linked_gates
from services.api.docpeg_proof_chain_service import (
    build_dsp_zip_package,
    build_rebar_report_context,
    get_proof_chain,
    render_rebar_inspection_docx,
    render_rebar_inspection_pdf,
)
from services.api.evidence_center_service import get_all_evidence_for_item
from services.api.did_gate_service import (
    resolve_required_credential,
    verify_credential,
)
from services.api.labpeg_frequency_remediation_service import (
    open_remediation_trip,
    resolve_dual_pass_gate,
)
from services.api.normpeg_engine import resolve_normpeg_eval
from services.api.proof_utxo_common import normalize_result as _normalize_result
from services.api.proof_utxo_engine import ProofUTXOEngine
from services.api.shadow_ledger_service import sync_to_mirrors
from services.api.specdict_gate_service import (
    evaluate_with_threshold_pack,
    resolve_dynamic_threshold,
)
from services.api.sovereign_credit_service import calculate_sovereign_credit
from services.api.did_reputation_service import build_did_reputation_summary
from services.api.phygital_sealing_service import build_sealing_trip
from services.api.verify_service import get_project_name_by_id


VALID_TRIPROLE_ACTIONS = {
    "quality.check",
    "measure.record",
    "variation.record",
    "settlement.confirm",
    "dispute.resolve",
    "scan.entry",
    "meshpeg.verify",
    "formula.price",
    "gateway.sync",
}

CONSENSUS_REQUIRED_ROLES = ("contractor", "supervisor", "owner")
MAX_CLIENT_SERVER_SKEW_MS = 5 * 60 * 1000
DEFAULT_OFFLINE_PACKET_SORT_EPOCH = 253402300799000
SCAN_CONFIRM_MAX_TTL_DAYS = 120
CONSENSUS_ROLE_ALIASES = {
    "施工": "contractor",
    "施工方": "contractor",
    "承包方": "contractor",
    "contractor": "contractor",
    "监理": "supervisor",
    "监理方": "supervisor",
    "supervisor": "supervisor",
    "业主": "owner",
    "业主方": "owner",
    "甲方": "owner",
    "owner": "owner",
}


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_action(raw: Any) -> str:
    text = _to_text(raw).strip().lower()
    if text.startswith("triprole(") and text.endswith(")"):
        text = text[len("triprole(") : -1].strip()
    return text


def _safe_path_token(raw: Any, *, fallback: str = "node") -> str:
    text = _to_text(raw).strip()
    if not text:
        return fallback
    token = re.sub(r"[^a-zA-Z0-9_\-]+", "-", text).strip("-")
    return token[:80] or fallback


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _safe_json_loads(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    text = _to_text(raw).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_role(value: Any) -> str:
    text = _to_text(value).strip().lower()
    if not text:
        return ""
    mapped = CONSENSUS_ROLE_ALIASES.get(text)
    if mapped:
        return mapped
    mapped = CONSENSUS_ROLE_ALIASES.get(_to_text(value).strip())
    if mapped:
        return mapped
    return text


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = _to_text(value).strip()
        if not text:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _to_text(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_iso_epoch_ms(value: Any) -> int | None:
    text = _to_text(value).strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _decode_base64url_json(raw: Any) -> dict[str, Any]:
    text = _to_text(raw).strip()
    if not text:
        return {}
    if text.startswith("{"):
        return _safe_json_loads(text)
    padded = text + "=" * (-len(text) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return {}
    return _safe_json_loads(decoded)


def _scan_confirm_secret() -> str:
    return _to_text(
        os.getenv("QCSPEC_SCAN_CONFIRM_SECRET")
        or os.getenv("SCAN_CONFIRM_SECRET")
        or "qcspec-scan-confirm-v1"
    ).strip()


def _canonical_scan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof_id": _to_text(payload.get("proof_id") or "").strip(),
        "signer_did": _to_text(payload.get("signer_did") or "").strip(),
        "signer_role": _normalize_role(payload.get("signer_role")) or _to_text(payload.get("signer_role") or "").strip(),
        "issued_at": _to_text(payload.get("issued_at") or "").strip(),
        "expires_at": _to_text(payload.get("expires_at") or "").strip(),
        "nonce": _to_text(payload.get("nonce") or "").strip(),
    }


def _scan_payload_signature(payload: dict[str, Any]) -> str:
    canonical = _canonical_scan_payload(payload)
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    secret = _scan_confirm_secret()
    return hashlib.sha256(f"{raw}|{secret}".encode("utf-8")).hexdigest()


def _validate_scan_confirm_payload(raw_payload: Any) -> dict[str, Any]:
    payload = _decode_base64url_json(raw_payload)
    if not payload:
        raise HTTPException(400, "invalid scan qr payload")
    canonical = _canonical_scan_payload(payload)
    if not canonical["proof_id"]:
        raise HTTPException(400, "scan payload missing proof_id")
    if not canonical["signer_did"].startswith("did:"):
        raise HTTPException(400, "scan payload signer_did invalid")
    if not canonical["issued_at"] or not canonical["expires_at"]:
        raise HTTPException(400, "scan payload missing issued_at/expires_at")
    issued_ms = _parse_iso_epoch_ms(canonical["issued_at"])
    expires_ms = _parse_iso_epoch_ms(canonical["expires_at"])
    now_ms = _parse_iso_epoch_ms(_utc_iso())
    if issued_ms is None or expires_ms is None or now_ms is None:
        raise HTTPException(400, "scan payload timestamp invalid")
    if expires_ms <= issued_ms:
        raise HTTPException(400, "scan payload expires_at must be greater than issued_at")
    if expires_ms - issued_ms > SCAN_CONFIRM_MAX_TTL_DAYS * 24 * 3600 * 1000:
        raise HTTPException(400, "scan payload ttl too long")
    if now_ms > expires_ms:
        raise HTTPException(409, "scan payload expired")
    provided_sig = _to_text(payload.get("token_hash") or payload.get("token_sig") or "").strip().lower()
    expected_sig = _scan_payload_signature(payload)
    if not provided_sig or provided_sig != expected_sig:
        raise HTTPException(409, "scan payload signature mismatch")
    return {**canonical, "token_hash": expected_sig}


def _normalize_geo_location(raw: Any) -> dict[str, Any]:
    payload = _as_dict(raw)
    lat = _to_float(payload.get("lat"))
    if lat is None:
        lat = _to_float(payload.get("latitude"))
    lng = _to_float(payload.get("lng"))
    if lng is None:
        lng = _to_float(payload.get("lon"))
    if lng is None:
        lng = _to_float(payload.get("longitude"))

    if lat is None or lng is None:
        raise HTTPException(400, "geo_location.lat/lng are required")
    if lat < -90.0 or lat > 90.0 or lng < -180.0 or lng > 180.0:
        raise HTTPException(400, "geo_location out of range")

    accuracy = _to_float(payload.get("accuracy_m"))
    altitude = _to_float(payload.get("altitude_m"))
    provider = _to_text(payload.get("provider") or payload.get("source") or "").strip() or "gps"
    captured_at = _to_text(payload.get("captured_at") or payload.get("timestamp") or "").strip()
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
    normalized["geo_fingerprint"] = _sha256_json(normalized)
    return normalized


def _normalize_server_timestamp_proof(
    raw: Any,
    *,
    now_iso: str,
    action: str,
    input_proof_id: str,
    executor_uri: str,
) -> dict[str, Any]:
    payload = _as_dict(raw)
    ntp_server = _to_text(payload.get("ntp_server") or payload.get("server") or "").strip()
    if not ntp_server:
        raise HTTPException(400, "server_timestamp_proof.ntp_server is required")

    client_ts = _to_text(
        payload.get("client_timestamp")
        or payload.get("captured_at")
        or payload.get("device_time")
        or ""
    ).strip()
    if not client_ts:
        raise HTTPException(400, "server_timestamp_proof.client_timestamp is required")

    offset_ms = _to_float(payload.get("ntp_offset_ms"))
    if offset_ms is None:
        offset_ms = _to_float(payload.get("offset_ms"))
    if offset_ms is None:
        raise HTTPException(400, "server_timestamp_proof.ntp_offset_ms is required")
    if abs(float(offset_ms)) > 60_000:
        raise HTTPException(400, "server_timestamp_proof.ntp_offset_ms too large")

    rtt_ms = _to_float(payload.get("ntp_round_trip_ms"))
    if rtt_ms is None:
        rtt_ms = _to_float(payload.get("round_trip_ms"))
    if rtt_ms is None:
        rtt_ms = 0.0

    client_epoch_ms = _parse_iso_epoch_ms(client_ts)
    server_epoch_ms = _parse_iso_epoch_ms(now_iso)
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
        "ntp_sample_id": _to_text(payload.get("ntp_sample_id") or "").strip(),
        "ntp_raw_hash": _to_text(payload.get("ntp_raw_hash") or "").strip().lower(),
    }
    normalized["timestamp_fingerprint"] = _sha256_json(
        {
            "action": action,
            "input_proof_id": input_proof_id,
            "executor_uri": executor_uri,
            **normalized,
        }
    )
    return normalized


def _build_spatiotemporal_anchor(
    *,
    action: str,
    input_proof_id: str,
    executor_uri: str,
    now_iso: str,
    geo_location_raw: Any,
    server_timestamp_raw: Any,
) -> dict[str, Any]:
    geo_location = _normalize_geo_location(geo_location_raw)
    server_timestamp_proof = _normalize_server_timestamp_proof(
        server_timestamp_raw,
        now_iso=now_iso,
        action=action,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
    )
    anchor_hash = _sha256_json(
        {
            "action": action,
            "input_proof_id": input_proof_id,
            "executor_uri": executor_uri,
            "geo_fingerprint": geo_location.get("geo_fingerprint"),
            "timestamp_fingerprint": server_timestamp_proof.get("timestamp_fingerprint"),
            "server_received_at": now_iso,
        }
    )
    return {
        "geo_location": geo_location,
        "server_timestamp_proof": server_timestamp_proof,
        "spatiotemporal_anchor_hash": anchor_hash,
    }


def _decode_sensor_payload(raw_payload: Any) -> tuple[dict[str, Any], str]:
    if isinstance(raw_payload, dict):
        normalized = dict(raw_payload)
        canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str)
        return normalized, hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    text = _to_text(raw_payload).strip()
    if not text:
        raise HTTPException(400, "raw_payload is required")
    if text.startswith("{"):
        parsed = _safe_json_loads(text)
        if not parsed:
            raise HTTPException(400, "raw_payload json parse failed")
        return parsed, hashlib.sha256(text.encode("utf-8")).hexdigest()

    padded = text + "=" * (-len(text) % 4)
    try:
        decoded_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
    except Exception:
        raise HTTPException(400, "raw_payload format unsupported")
    decoded_text = decoded_bytes.decode("utf-8", errors="replace").strip()
    parsed = _safe_json_loads(decoded_text)
    if not parsed:
        raise HTTPException(400, "raw_payload decode failed")
    return parsed, hashlib.sha256(decoded_bytes).hexdigest()


def _normalize_sensor_payload(device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    source = _as_dict(payload.get("measurement"))
    if not source:
        source = payload
    values = _extract_values(source)
    value = _to_float(source.get("value") if "value" in source else source.get("measured_value"))
    if value is None and values:
        value = round(float(sum(values) / len(values)), 6)
    if value is None:
        raise HTTPException(400, "sensor payload missing measured value")

    calibration_valid_until = _to_text(
        payload.get("calibration_valid_until")
        or payload.get("calibration_expire_at")
        or payload.get("calibration_due_at")
        or ""
    ).strip()
    calibration_epoch = _parse_iso_epoch_ms(calibration_valid_until)
    now_epoch = _parse_iso_epoch_ms(_utc_iso()) or 0
    calibration_valid = (
        calibration_epoch is not None and calibration_epoch >= now_epoch
        if calibration_valid_until
        else _to_bool(payload.get("calibration_valid") if "calibration_valid" in payload else True)
    )

    clean_payload = dict(payload)
    for key in ("payload_hash", "packet_hash", "raw_payload_hash", "signature", "token"):
        clean_payload.pop(key, None)

    sensor_hardware = {
        "device_id": _to_text(device_id).strip(),
        "device_sn": _to_text(
            payload.get("device_sn")
            or payload.get("sn")
            or payload.get("serial_no")
            or payload.get("serial_number")
            or device_id
        ).strip(),
        "transport": _to_text(payload.get("transport") or payload.get("channel") or "ble").strip().lower(),
        "manufacturer": _to_text(payload.get("manufacturer") or "").strip(),
        "model": _to_text(payload.get("model") or "").strip(),
        "firmware_version": _to_text(payload.get("firmware_version") or payload.get("fw_version") or "").strip(),
        "calibration_valid_until": calibration_valid_until,
        "calibration_valid": bool(calibration_valid),
    }
    sensor_hardware["hardware_fingerprint"] = _sha256_json(sensor_hardware)

    measured_at = _to_text(
        source.get("measured_at")
        or payload.get("measured_at")
        or payload.get("captured_at")
        or source.get("timestamp")
        or payload.get("timestamp")
        or ""
    ).strip()
    if not measured_at:
        measured_at = _utc_iso()

    normalized = {
        "boq_item_uri": _to_text(
            payload.get("boq_item_uri")
            or payload.get("item_uri")
            or payload.get("boq_uri")
            or ""
        ).strip(),
        "value": round(float(value), 6),
        "values": [round(float(v), 6) for v in values] if values else [round(float(value), 6)],
        "unit": _to_text(source.get("unit") or payload.get("unit") or "").strip(),
        "measured_at": measured_at,
        "sensor_hardware": sensor_hardware,
        "sensor_payload": clean_payload,
    }
    normalized["sensor_payload_hash"] = _sha256_json(clean_payload)
    normalized["sensor_reading_hash"] = _sha256_json(
        {
            "boq_item_uri": normalized["boq_item_uri"],
            "value": normalized["value"],
            "values": normalized["values"],
            "unit": normalized["unit"],
            "measured_at": normalized["measured_at"],
            "hardware_fingerprint": sensor_hardware["hardware_fingerprint"],
        }
    )
    return normalized


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371000.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2.0) ** 2
    c = 2.0 * asin(min(1.0, sqrt(a)))
    return float(r * c)


def _point_in_polygon(*, lat: float, lng: float, polygon: list[dict[str, float]]) -> bool:
    if len(polygon) < 3:
        return False
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi = float(polygon[i]["lng"])
        yi = float(polygon[i]["lat"])
        xj = float(polygon[j]["lng"])
        yj = float(polygon[j]["lat"])
        intersects = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _normalize_geo_fence_boundary(raw: Any) -> dict[str, Any]:
    payload = _as_dict(raw)
    if not payload:
        return {"enforced": False, "type": "none"}

    boundary_type = _to_text(payload.get("type") or payload.get("boundary_type") or "").strip().lower()
    if not boundary_type:
        if isinstance(payload.get("polygon"), list) or isinstance(payload.get("coordinates"), list):
            boundary_type = "polygon"
        elif isinstance(payload.get("center"), dict) or ("radius_m" in payload):
            boundary_type = "circle"
        elif all(k in payload for k in ("min_lat", "max_lat", "min_lng", "max_lng")):
            boundary_type = "bbox"

    strict_mode = _to_bool(payload.get("strict_mode"))
    deviation_m = _to_float(payload.get("allowed_deviation_m"))
    if deviation_m is None:
        deviation_m = 0.0

    if boundary_type == "circle":
        center = _as_dict(payload.get("center"))
        center_lat = _to_float(center.get("lat") if "lat" in center else center.get("latitude"))
        center_lng = _to_float(center.get("lng") if "lng" in center else center.get("longitude"))
        radius = _to_float(payload.get("radius_m"))
        if center_lat is None or center_lng is None or radius is None or radius <= 0:
            return {"enforced": False, "type": "none"}
        normalized = {
            "enforced": True,
            "type": "circle",
            "center": {"lat": float(center_lat), "lng": float(center_lng)},
            "radius_m": float(radius),
            "allowed_deviation_m": float(deviation_m),
            "strict_mode": strict_mode,
        }
        normalized["boundary_fingerprint"] = _sha256_json(normalized)
        return normalized

    if boundary_type == "bbox":
        min_lat = _to_float(payload.get("min_lat"))
        max_lat = _to_float(payload.get("max_lat"))
        min_lng = _to_float(payload.get("min_lng"))
        max_lng = _to_float(payload.get("max_lng"))
        if None in {min_lat, max_lat, min_lng, max_lng}:
            return {"enforced": False, "type": "none"}
        normalized = {
            "enforced": True,
            "type": "bbox",
            "min_lat": float(min_lat),
            "max_lat": float(max_lat),
            "min_lng": float(min_lng),
            "max_lng": float(max_lng),
            "allowed_deviation_m": float(deviation_m),
            "strict_mode": strict_mode,
        }
        normalized["boundary_fingerprint"] = _sha256_json(normalized)
        return normalized

    points_raw = payload.get("polygon")
    if not isinstance(points_raw, list):
        points_raw = payload.get("coordinates")
    points: list[dict[str, float]] = []
    for item in _as_list(points_raw):
        if isinstance(item, dict):
            lat = _to_float(item.get("lat") if "lat" in item else item.get("latitude"))
            lng = _to_float(item.get("lng") if "lng" in item else item.get("longitude"))
            if lat is not None and lng is not None:
                points.append({"lat": float(lat), "lng": float(lng)})
                continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            lng = _to_float(item[0])
            lat = _to_float(item[1])
            if lat is not None and lng is not None:
                points.append({"lat": float(lat), "lng": float(lng)})
    if len(points) < 3:
        return {"enforced": False, "type": "none"}

    normalized = {
        "enforced": True,
        "type": "polygon",
        "polygon": points,
        "allowed_deviation_m": float(deviation_m),
        "strict_mode": strict_mode,
    }
    normalized["boundary_fingerprint"] = _sha256_json(normalized)
    return normalized


def _load_project_custom_fields(*, sb: Any, project_id: Any, project_uri: str) -> dict[str, Any]:
    enterprise_id = ""
    pid = _to_text(project_id).strip()
    p_uri = _to_text(project_uri).strip()
    try:
        q = sb.table("projects").select("enterprise_id")
        if pid:
            rows = q.eq("id", pid).limit(1).execute().data or []
        else:
            rows = q.eq("v_uri", p_uri).limit(1).execute().data or []
        if rows and isinstance(rows[0], dict):
            enterprise_id = _to_text(rows[0].get("enterprise_id") or "").strip()
    except Exception:
        enterprise_id = ""

    if not enterprise_id:
        return {}
    try:
        cfg_rows = (
            sb.table("enterprise_configs")
            .select("custom_fields")
            .eq("enterprise_id", enterprise_id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return {}
    if not cfg_rows or not isinstance(cfg_rows[0], dict):
        return {}
    return _as_dict(cfg_rows[0].get("custom_fields"))


def _resolve_project_boundary(*, sb: Any, project_id: Any, project_uri: str, override: Any = None) -> dict[str, Any]:
    override_payload = _as_dict(override)
    if override_payload:
        return _normalize_geo_fence_boundary(override_payload)

    custom = _load_project_custom_fields(sb=sb, project_id=project_id, project_uri=project_uri)
    candidates: list[Any] = []
    candidates.append(custom.get("site_boundary"))
    candidates.append(custom.get("geo_fence"))
    candidates.append(custom.get("project_site_boundary"))

    boundary_map = _as_dict(custom.get("project_site_boundaries"))
    if boundary_map:
        pid = _to_text(project_id).strip()
        if project_uri in boundary_map:
            candidates.insert(0, boundary_map.get(project_uri))
        if pid and pid in boundary_map:
            candidates.insert(0, boundary_map.get(pid))

    boundary_list = _as_list(custom.get("project_site_boundaries"))
    pid = _to_text(project_id).strip()
    for item in boundary_list:
        if not isinstance(item, dict):
            continue
        item_uri = _to_text(item.get("project_uri") or "").strip()
        item_pid = _to_text(item.get("project_id") or "").strip()
        if (item_uri and item_uri == project_uri) or (pid and item_pid == pid):
            candidates.insert(0, item.get("boundary") or item)

    env_boundary = _safe_json_loads(os.getenv("QCSPEC_SITE_BOUNDARY") or "")
    if env_boundary:
        candidates.append(env_boundary)

    for candidate in candidates:
        normalized = _normalize_geo_fence_boundary(candidate)
        if normalized.get("enforced"):
            return normalized
    return {"enforced": False, "type": "none"}


def check_location_compliance(current_gps: dict[str, Any], project_boundary: dict[str, Any]) -> dict[str, Any]:
    gps = _normalize_geo_location(current_gps)
    boundary = _normalize_geo_fence_boundary(project_boundary)
    if not boundary.get("enforced"):
        return {
            "enforced": False,
            "inside": True,
            "outside": False,
            "trust_level": "UNKNOWN",
            "warning": "",
            "gps": gps,
            "boundary_type": "none",
            "boundary_fingerprint": "",
        }

    lat = float(gps.get("lat"))
    lng = float(gps.get("lng"))
    inside = True
    distance_m: float | None = None
    boundary_type = _to_text(boundary.get("type") or "").strip().lower()

    if boundary_type == "circle":
        center = _as_dict(boundary.get("center"))
        center_lat = float(_to_float(center.get("lat")) or 0.0)
        center_lng = float(_to_float(center.get("lng")) or 0.0)
        radius = float(_to_float(boundary.get("radius_m")) or 0.0)
        distance_m = _haversine_distance_m(lat, lng, center_lat, center_lng)
        allowed = radius + float(_to_float(boundary.get("allowed_deviation_m")) or 0.0)
        inside = distance_m <= allowed
    elif boundary_type == "bbox":
        min_lat = float(_to_float(boundary.get("min_lat")) or -90.0)
        max_lat = float(_to_float(boundary.get("max_lat")) or 90.0)
        min_lng = float(_to_float(boundary.get("min_lng")) or -180.0)
        max_lng = float(_to_float(boundary.get("max_lng")) or 180.0)
        inside = (min_lat <= lat <= max_lat) and (min_lng <= lng <= max_lng)
    else:
        polygon = [
            {"lat": float(_to_float(x.get("lat")) or 0.0), "lng": float(_to_float(x.get("lng")) or 0.0)}
            for x in _as_list(boundary.get("polygon"))
            if isinstance(x, dict)
        ]
        inside = _point_in_polygon(lat=lat, lng=lng, polygon=polygon)

    outside = not inside
    warning = ""
    if outside:
        warning = "场外录入：当前位置超出项目电子围栏，Proof 标记为低信任等级。"
    return {
        "enforced": True,
        "inside": inside,
        "outside": outside,
        "distance_m": round(float(distance_m), 3) if distance_m is not None else None,
        "trust_level": "LOW" if outside else "HIGH",
        "warning": warning,
        "strict_mode": bool(boundary.get("strict_mode")),
        "gps": gps,
        "boundary_type": boundary_type or "polygon",
        "boundary_fingerprint": _to_text(boundary.get("boundary_fingerprint") or "").strip(),
    }


def _extract_values(payload: dict[str, Any]) -> list[float]:
    raw_vals = payload.get("values")
    out: list[float] = []
    if isinstance(raw_vals, list):
        for item in raw_vals:
            num = _to_float(item)
            if num is not None:
                out.append(float(num))
        return out

    if isinstance(raw_vals, str):
        parts = re.split(r"[,，;\s\n]+", raw_vals)
        for part in parts:
            num = _to_float(part)
            if num is not None:
                out.append(float(num))
        if out:
            return out

    single = _to_float(payload.get("value"))
    if single is not None:
        return [float(single)]
    return out


def _looks_like_sig_hash(value: Any) -> bool:
    text = _to_text(value).strip().lower()
    return bool(re.fullmatch(r"[a-f0-9]{64}", text))


def _normalize_consensus_signatures(raw: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return normalized
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = _normalize_role(item.get("role"))
        did = _to_text(item.get("did") or "").strip()
        sig = _to_text(item.get("signature_hash") or item.get("signature") or "").strip().lower()
        if not role:
            continue
        normalized.append(
            {
                "role": role,
                "did": did,
                "signature_hash": sig,
                "signed_at": _to_text(item.get("signed_at") or _utc_iso()).strip(),
            }
        )
    return normalized


def _validate_consensus_signatures(
    signatures: list[dict[str, Any]],
    *,
    required_roles: tuple[str, ...] = CONSENSUS_REQUIRED_ROLES,
) -> dict[str, Any]:
    by_role: dict[str, dict[str, Any]] = {}
    for sig in signatures:
        role = _normalize_role(sig.get("role"))
        if not role:
            continue
        by_role[role] = sig

    missing = [r for r in required_roles if r not in by_role]
    invalid: list[str] = []
    for role, sig in by_role.items():
        did = _to_text(sig.get("did") or "").strip()
        sig_hash = _to_text(sig.get("signature_hash") or "").strip()
        if not did.startswith("did:"):
            invalid.append(f"{role}:did_invalid")
        if not _looks_like_sig_hash(sig_hash):
            invalid.append(f"{role}:signature_hash_invalid")

    ok = (not missing) and (not invalid)
    consensus_payload = {
        "required_roles": list(required_roles),
        "signatures": [by_role[r] for r in required_roles if r in by_role],
    }
    return {
        "ok": ok,
        "missing_roles": missing,
        "invalid": invalid,
        "consensus_hash": _sha256_json(consensus_payload) if ok else "",
        "consensus_payload": consensus_payload,
    }


def _normalize_signer_metadata(raw: Any) -> dict[str, Any]:
    payload = _as_dict(raw)
    signers_raw = payload.get("signers")
    if not isinstance(signers_raw, list):
        if isinstance(raw, list):
            signers_raw = raw
        elif payload:
            signers_raw = [payload]
        else:
            signers_raw = []

    signers: list[dict[str, Any]] = []
    for item in signers_raw:
        if not isinstance(item, dict):
            continue
        did = _to_text(item.get("did") or item.get("signer_did") or "").strip()
        role = _normalize_role(item.get("role") or item.get("signer_role"))
        biometric_passed = _to_bool(
            item.get("biometric_passed")
            if "biometric_passed" in item
            else (
                item.get("verified")
                if "verified" in item
                else (
                    item.get("liveness_passed")
                    if "liveness_passed" in item
                    else item.get("fingerprint_passed")
                )
            )
        )
        verified_at = _to_text(item.get("verified_at") or item.get("timestamp") or item.get("checked_at") or "").strip()
        signers.append(
            {
                "did": did,
                "role": role,
                "biometric_passed": bool(biometric_passed),
                "verified_at": verified_at,
                "method": _to_text(item.get("method") or item.get("biometric_type") or "").strip().lower(),
                "provider": _to_text(item.get("provider") or "").strip(),
                "confidence": _to_float(item.get("confidence")),
                "device_id": _to_text(item.get("device_id") or "").strip(),
            }
        )

    normalized = {
        "signers": signers,
        "captured_at": _to_text(payload.get("captured_at") or "").strip(),
        "metadata_hash": _sha256_json(signers),
    }
    return normalized


def _extract_consensus_values(raw: Any, payload: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []

    def _push(item: dict[str, Any], source: str) -> None:
        if not isinstance(item, dict):
            return
        role = _normalize_role(item.get("role") or item.get("signer_role"))
        did = _to_text(item.get("did") or item.get("signer_did") or "").strip()
        for key in ("measured_value", "value", "quantity", "amount", "measured", "reported_value"):
            val = _to_float(item.get(key))
            if val is not None:
                values.append(
                    {
                        "role": role,
                        "did": did,
                        "value": float(val),
                        "source": source,
                        "field": key,
                    }
                )
                return

    consensus_values = payload.get("consensus_values")
    if isinstance(consensus_values, list):
        for item in consensus_values:
            if isinstance(item, dict):
                _push(item, "payload.consensus_values")

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                _push(item, "signer_metadata")
    elif isinstance(raw, dict):
        signers = raw.get("signers")
        if isinstance(signers, list):
            for item in signers:
                if isinstance(item, dict):
                    _push(item, "signer_metadata.signers")
        else:
            _push(raw, "signer_metadata")

    return values


def detect_consensus_deviation(
    *,
    signer_metadata_raw: Any,
    payload: dict[str, Any],
    input_sd: dict[str, Any],
) -> dict[str, Any]:
    values = _extract_consensus_values(signer_metadata_raw, payload)
    if len(values) < 2:
        return {"ok": True, "conflict": False, "reason": "insufficient_values", "values": values}

    raw_allowed = (
        payload.get("allowed_deviation")
        or payload.get("tolerance")
        or payload.get("deviation_limit")
        or _as_dict(input_sd.get("norm_evaluation")).get("tolerance")
    )
    allowed_abs = _to_float(raw_allowed)
    allowed_pct = _to_float(
        payload.get("allowed_deviation_percent")
        or payload.get("deviation_percent")
        or payload.get("tolerance_percent")
    )

    series = [v.get("value") for v in values if isinstance(v.get("value"), (int, float))]
    if not series:
        return {"ok": True, "conflict": False, "reason": "no_numeric_values", "values": values}

    min_v = min(series)
    max_v = max(series)
    diff = max_v - min_v
    avg = (max_v + min_v) / 2 if (max_v + min_v) != 0 else max_v
    pct = (diff / avg * 100.0) if avg else 0.0

    conflict = False
    if allowed_abs is not None and diff > float(allowed_abs):
        conflict = True
    if allowed_pct is not None and pct > float(allowed_pct):
        conflict = True

    if allowed_abs is None and allowed_pct is None:
        # Default: allow small numeric jitter up to 0.5% if no threshold is configured.
        conflict = pct > 0.5 if avg else diff > 0

    return {
        "ok": True,
        "conflict": conflict,
        "min_value": min_v,
        "max_value": max_v,
        "deviation": diff,
        "deviation_percent": round(pct, 4),
        "allowed_deviation": allowed_abs,
        "allowed_deviation_percent": allowed_pct,
        "values": values,
    }


def _create_consensus_dispute(
    *,
    sb: Any,
    input_row: dict[str, Any],
    project_uri: str,
    boq_item_uri: str,
    executor_uri: str,
    conflict: dict[str, Any],
    consensus_signatures: list[dict[str, Any]],
    signer_metadata: dict[str, Any],
) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    input_id = _to_text(input_row.get("proof_id") or "").strip()
    now_iso = _utc_iso()
    state_data = {
        "doc_type": "consensus_dispute",
        "status": "DISPUTE",
        "lifecycle_stage": "DISPUTE",
        "trip_action": "consensus.dispute",
        "boq_item_uri": boq_item_uri,
        "project_uri": project_uri,
        "source_proof_id": input_id,
        "conflict": conflict,
        "consensus_signatures": consensus_signatures,
        "signer_metadata": signer_metadata,
        "locked": True,
        "created_at": now_iso,
    }
    proof_id = f"GP-DSPT-{_sha256_json(state_data)[:16].upper()}"
    try:
        row = engine.create(
            proof_id=proof_id,
            owner_uri=_to_text(executor_uri).strip() or "v://executor/system/",
            project_uri=project_uri,
            project_id=_to_text(input_row.get("project_id") or "").strip() or None,
            segment_uri=boq_item_uri,
            proof_type="dispute",
            result="FAIL",
            state_data=state_data,
            conditions=[],
            parent_proof_id=input_id or None,
            norm_uri="v://norm/CoordOS/Consensus/1.0#dispute",
            signer_uri=_to_text(executor_uri).strip() or "v://executor/system/",
            signer_role="ARBITER",
        )
        return {"ok": True, "proof_id": _to_text(row.get("proof_id") or proof_id).strip()}
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}


def verify_biometric_status(
    *,
    signer_metadata: dict[str, Any] | list[dict[str, Any]] | None,
    consensus_signatures: list[dict[str, Any]],
    required_roles: tuple[str, ...] = CONSENSUS_REQUIRED_ROLES,
) -> dict[str, Any]:
    normalized = _normalize_signer_metadata(signer_metadata or {})
    signers = _as_list(normalized.get("signers"))
    by_did: dict[str, dict[str, Any]] = {}
    by_role: dict[str, dict[str, Any]] = {}
    for item in signers:
        if not isinstance(item, dict):
            continue
        did = _to_text(item.get("did") or "").strip()
        role = _normalize_role(item.get("role"))
        if did:
            by_did[did] = item
        if role and role not in by_role:
            by_role[role] = item

    required = [
        sig
        for sig in consensus_signatures
        if _normalize_role(sig.get("role")) in required_roles
    ]
    missing: list[str] = []
    failed: list[str] = []
    passed: list[str] = []

    for sig in required:
        role = _normalize_role(sig.get("role"))
        did = _to_text(sig.get("did") or "").strip()
        ref = by_did.get(did) or by_role.get(role)
        tag = f"{role}:{did or '-'}"
        if not isinstance(ref, dict):
            missing.append(tag)
            continue
        if not _to_bool(ref.get("biometric_passed")):
            failed.append(f"{tag}:biometric_failed")
            continue
        if not _to_text(ref.get("verified_at") or "").strip():
            failed.append(f"{tag}:missing_timestamp")
            continue
        passed.append(tag)

    ok = (not missing) and (not failed)
    return {
        "ok": ok,
        "required_count": len(required),
        "verified_count": len(passed),
        "missing": missing,
        "failed": failed,
        "passed": passed,
        "metadata_hash": _to_text(normalized.get("metadata_hash") or "").strip(),
        "signers": signers,
    }


def _collect_norm_refs_from_row(row: dict[str, Any]) -> list[str]:
    refs: set[str] = set()
    sd = _as_dict(row.get("state_data"))
    norm_eval = _as_dict(sd.get("norm_evaluation"))
    threshold = _as_dict(norm_eval.get("threshold"))
    for candidate in (
        row.get("norm_uri"),
        sd.get("norm_uri"),
        sd.get("spec_uri"),
        sd.get("spec_snapshot_uri"),
        threshold.get("effective_spec_uri"),
        threshold.get("spec_uri"),
    ):
        uri = _to_text(candidate).strip()
        if uri.startswith("v://norm"):
            refs.add(uri)
    return sorted(refs)


def _collect_evidence_hashes_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    sd = _as_dict(row.get("state_data"))
    evidence = _as_list(sd.get("evidence"))
    out: list[dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        url = _to_text(item.get("url") or "").strip()
        hash_value = _to_text(
            item.get("sha256")
            or item.get("hash")
            or item.get("photo_hash")
            or item.get("fingerprint")
            or ""
        ).strip()
        if not hash_value and url:
            hash_value = hashlib.sha256(url.encode("utf-8")).hexdigest()
        if not hash_value:
            continue
        out.append(
            {
                "evidence_id": _to_text(item.get("id") or "").strip(),
                "file_name": _to_text(item.get("file_name") or "").strip(),
                "source_url": url,
                "hash": hash_value,
                "proof_id": _to_text(row.get("proof_id") or "").strip(),
                "geo_location": _as_dict(item.get("geo_location")),
                "server_timestamp_proof": _as_dict(item.get("server_timestamp_proof")),
            }
        )
    return out


def _extract_qc_conclusion(row: dict[str, Any]) -> dict[str, Any]:
    sd = _as_dict(row.get("state_data"))
    norm_eval = _as_dict(sd.get("norm_evaluation"))
    stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper() or _stage_from_row(row)
    conclusion = _to_text(norm_eval.get("result") or row.get("result") or "").strip().upper()
    return {
        "proof_id": _to_text(row.get("proof_id") or "").strip(),
        "stage": stage,
        "action": _to_text(sd.get("trip_action") or "").strip().lower(),
        "result": _to_text(row.get("result") or "").strip().upper(),
        "qc_conclusion": conclusion,
        "deviation_percent": norm_eval.get("deviation_percent"),
        "spec_uri": _to_text(sd.get("spec_uri") or "").strip(),
        "spec_snapshot": _to_text(sd.get("spec_snapshot") or "").strip(),
        "created_at": _to_text(row.get("created_at") or "").strip(),
    }


def _boq_item_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    uri = _to_text(sd.get("boq_item_uri") or sd.get("item_uri") or sd.get("boq_uri") or "").strip()
    if uri.startswith("v://"):
        return uri
    seg = _to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in seg:
        return seg
    return ""


def _is_leaf_boq_row(row: dict[str, Any]) -> bool:
    sd = _as_dict(row.get("state_data"))
    if "is_leaf" in sd:
        return bool(sd.get("is_leaf"))
    tree = _as_dict(sd.get("hierarchy_tree"))
    if "is_leaf" in tree:
        return bool(tree.get("is_leaf"))
    children = _as_list(tree.get("children")) or _as_list(tree.get("children_codes"))
    if children:
        return False
    return True


def _item_no_from_boq_uri(boq_item_uri: str) -> str:
    uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not uri:
        return ""
    return uri.split("/")[-1]


def _smu_id_from_item_no(item_no: str) -> str:
    token = _to_text(item_no).strip().rstrip("/").split("/")[-1]
    if "-" in token:
        return token.split("-")[0]
    return token or "misc"


def _resolve_subitem_gate_binding(
    *,
    sb: Any,
    input_row: dict[str, Any],
    boq_item_uri: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    sd = _as_dict(input_row.get("state_data"))
    item_code = _to_text(sd.get("item_no") or _item_no_from_boq_uri(boq_item_uri)).strip()
    fallback_spec_uri = _to_text(
        sd.get("linked_spec_uri")
        or sd.get("spec_uri")
        or payload.get("spec_uri")
        or payload.get("norm_uri")
        or input_row.get("norm_uri")
        or ""
    ).strip()
    binding = resolve_linked_gates(
        item_code=item_code,
        fallback_spec_uri=fallback_spec_uri,
        sb=sb,
    )
    linked_gate_ids = _as_list(sd.get("linked_gate_ids"))
    linked_gate_rules = _as_list(sd.get("linked_gate_rules"))
    linked_gate_id = _to_text(sd.get("linked_gate_id") or "").strip()
    linked_spec_uri = _to_text(sd.get("linked_spec_uri") or "").strip()
    spec_dict_key = _to_text(sd.get("spec_dict_key") or "").strip()
    spec_item = _to_text(sd.get("spec_item") or "").strip()

    if linked_gate_id and linked_gate_ids:
        binding["linked_gate_id"] = linked_gate_id
        binding["linked_gate_ids"] = linked_gate_ids
        if linked_gate_rules:
            binding["linked_gate_rules"] = linked_gate_rules
    if linked_spec_uri:
        binding["linked_spec_uri"] = linked_spec_uri
    if spec_dict_key:
        binding["spec_dict_key"] = spec_dict_key
    if spec_item:
        binding["spec_item"] = spec_item
    if sd.get("gate_template_lock") is not None:
        binding["gate_template_lock"] = bool(sd.get("gate_template_lock"))
    return binding


def _extract_settled_quantity(row: dict[str, Any], *, fallback_design: float | None = None) -> float:
    sd = _as_dict(row.get("state_data"))
    settlement = _as_dict(sd.get("settlement"))
    measurement = _as_dict(sd.get("measurement"))

    for path in (
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        settlement.get("confirmed_quantity"),
        sd.get("settled_quantity"),
        measurement.get("quantity"),
        measurement.get("used_quantity"),
        sd.get("quantity"),
    ):
        q = _to_float(path)
        if q is not None:
            return max(0.0, float(q))

    values = _as_list(measurement.get("values"))
    nums = [x for x in (_to_float(v) for v in values) if x is not None]
    if nums:
        return max(0.0, float(sum(nums) / len(nums)))

    if fallback_design is not None:
        return max(0.0, float(fallback_design))
    return 0.0


def _effective_design_quantity(genesis_row: dict[str, Any], bucket: list[dict[str, Any]]) -> float:
    gsd = _as_dict(genesis_row.get("state_data"))
    base_design = _to_float(gsd.get("contract_quantity"))
    if base_design is None:
        base_design = _to_float(gsd.get("approved_quantity"))
    if base_design is None:
        base_design = _to_float(gsd.get("design_quantity"))
    if base_design is None:
        base_design = _to_float(_as_dict(gsd.get("ledger")).get("initial_balance"))
    if base_design is None:
        base_design = 0.0

    latest_merged_total: float | None = None
    latest_delta_total: float | None = None
    for row in sorted(bucket, key=lambda r: _to_text(r.get("created_at") or "")):
        sd = _as_dict(row.get("state_data"))
        ledger = _as_dict(sd.get("ledger"))
        merged_total = _to_float(ledger.get("merged_total"))
        if merged_total is not None:
            latest_merged_total = float(merged_total)
        delta_total = _to_float(ledger.get("delta_total"))
        if delta_total is not None:
            latest_delta_total = float(delta_total)

    if latest_merged_total is not None:
        return max(0.0, latest_merged_total)
    if latest_delta_total is not None:
        return max(0.0, float(base_design + latest_delta_total))
    return max(0.0, float(base_design))


def _stage_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    if stage in {"INITIAL", "ENTRY", "INSTALLATION", "VARIATION", "SETTLEMENT"}:
        return stage
    if _to_text(row.get("proof_type")).lower() == "zero_ledger":
        return "INITIAL"
    return "UNKNOWN"


def _resolve_boq_item_uri(row: dict[str, Any], override: Any = None) -> str:
    if _to_text(override).strip().startswith("v://"):
        return _to_text(override).strip()
    sd = _as_dict(row.get("state_data"))
    for key in ("boq_item_uri", "item_uri", "boq_uri"):
        uri = _to_text(sd.get(key)).strip()
        if uri.startswith("v://"):
            return uri
    segment_uri = _to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in segment_uri:
        return segment_uri
    return ""


def _resolve_segment_uri(row: dict[str, Any], payload: dict[str, Any], override: Any = None) -> str:
    if _to_text(override).strip().startswith("v://"):
        return _to_text(override).strip()
    incoming = _to_text(payload.get("segment_uri") or payload.get("location_uri") or "").strip()
    if incoming.startswith("v://"):
        return incoming
    existing = _to_text(row.get("segment_uri") or "").strip()
    if existing:
        return existing

    project_uri = _to_text(row.get("project_uri") or "").strip().rstrip("/")
    stake = _to_text(payload.get("stake") or payload.get("location") or payload.get("station") or "").strip()
    part = _to_text(payload.get("part") or payload.get("position") or "").strip()
    if project_uri and stake:
        suffix = f"/{_safe_path_token(part)}" if part else ""
        return f"{project_uri}/segment/{_safe_path_token(stake)}{suffix}"
    return existing


def _build_variation_compensates(payload: dict[str, Any], input_proof_id: str) -> list[str]:
    vals = payload.get("compensates")
    if isinstance(vals, list):
        out = [_to_text(x).strip() for x in vals if _to_text(x).strip()]
        if out:
            return out
    direct = _to_text(payload.get("source_fail_proof_id") or "").strip()
    if direct:
        return [direct]
    return [input_proof_id]


def _build_provenance_nodes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        pid = _to_text(row.get("proof_id")).strip()
        if pid:
            by_id[pid] = row

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        pid = _to_text(row.get("proof_id") or "").strip()
        parent_id = _to_text(row.get("parent_proof_id") or "").strip()

        parent_hash = _to_text(sd.get("parent_hash") or "").strip()
        if not parent_hash and parent_id and parent_id in by_id:
            parent_hash = _to_text(by_id[parent_id].get("proof_hash") or "").strip()

        stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper() or _stage_from_row(row)

        out.append(
            {
                "proof_id": pid,
                "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                "parent_proof_id": parent_id,
                "parent_hash": parent_hash,
                "proof_type": _to_text(row.get("proof_type") or "").strip().lower(),
                "result": _to_text(row.get("result") or "").strip().upper(),
                "lifecycle_stage": stage,
                "trip_action": _to_text(sd.get("trip_action") or "").strip().lower(),
                "segment_uri": _to_text(row.get("segment_uri") or "").strip(),
                "boq_item_uri": _to_text(sd.get("boq_item_uri") or sd.get("item_uri") or "").strip(),
                "norm_uri": _to_text(row.get("norm_uri") or sd.get("norm_uri") or "").strip(),
                "gitpeg_anchor": _to_text(row.get("gitpeg_anchor") or "").strip(),
                "created_at": _to_text(row.get("created_at") or "").strip(),
                "geo_location": _as_dict(sd.get("geo_location")),
                "server_timestamp_proof": _as_dict(sd.get("server_timestamp_proof")),
                "spatiotemporal_anchor_hash": _to_text(sd.get("spatiotemporal_anchor_hash") or "").strip(),
                "compensates": [
                    _to_text(x).strip()
                    for x in (_as_list(sd.get("compensates")))
                    if _to_text(x).strip()
                ],
            }
        )

    return out


def _gate_lock(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    fail_ids = [
        _to_text(node.get("proof_id") or "").strip()
        for node in nodes
        if _to_text(node.get("result") or "").strip().upper() == "FAIL"
    ]
    fail_ids = [x for x in fail_ids if x]

    variation_nodes = [
        node
        for node in nodes
        if _to_text(node.get("lifecycle_stage") or "").strip().upper() == "VARIATION"
    ]

    compensated: set[str] = set()
    compensation_links: list[dict[str, Any]] = []
    for node in variation_nodes:
        variation_id = _to_text(node.get("proof_id") or "").strip()
        targets = set(_as_list(node.get("compensates")))
        parent_id = _to_text(node.get("parent_proof_id") or "").strip()
        if parent_id:
            targets.add(parent_id)

        matched = sorted(
            {
                _to_text(t).strip()
                for t in targets
                if _to_text(t).strip() and _to_text(t).strip() in fail_ids
            }
        )
        for proof_id in matched:
            compensated.add(proof_id)
        compensation_links.append(
            {
                "variation_proof_id": variation_id,
                "compensates": matched,
            }
        )

    uncompensated = sorted([proof_id for proof_id in fail_ids if proof_id not in compensated])
    blocked = bool(uncompensated)

    return {
        "blocked": blocked,
        "reason": "fail_without_variation" if blocked else "clear",
        "fail_proof_ids": sorted(set(fail_ids)),
        "variation_count": len(variation_nodes),
        "variation_compensations": compensation_links,
        "uncompensated_fail_proof_ids": uncompensated,
    }


def aggregate_provenance_chain(utxo_id: str, sb: Any, *, max_depth: int = 256) -> dict[str, Any]:
    """
    Recursively aggregate lineage from root -> current UTXO and compute Total Proof Hash.
    """
    normalized = _to_text(utxo_id).strip()
    if not normalized:
        raise HTTPException(400, "utxo_id is required")

    engine = ProofUTXOEngine(sb)
    chain_rows = engine.get_chain(normalized, max_depth=max_depth)
    if not chain_rows:
        raise HTTPException(404, "proof chain not found")

    nodes = _build_provenance_nodes(chain_rows)
    total_proof_hash = _sha256_json(
        [
            {
                "proof_id": node.get("proof_id"),
                "proof_hash": node.get("proof_hash"),
                "parent_proof_id": node.get("parent_proof_id"),
                "parent_hash": node.get("parent_hash"),
                "lifecycle_stage": node.get("lifecycle_stage"),
                "trip_action": node.get("trip_action"),
                "result": node.get("result"),
            }
            for node in nodes
        ]
    )

    latest = chain_rows[-1]
    latest_sd = _as_dict(latest.get("state_data"))
    gate = _gate_lock(nodes)

    return {
        "ok": True,
        "utxo_id": normalized,
        "root_proof_id": _to_text(chain_rows[0].get("proof_id") or "").strip(),
        "latest_proof_id": _to_text(latest.get("proof_id") or "").strip(),
        "project_uri": _to_text(latest.get("project_uri") or "").strip(),
        "segment_uri": _to_text(latest.get("segment_uri") or "").strip(),
        "boq_item_uri": _resolve_boq_item_uri(latest),
        "artifact_uri": _to_text(latest_sd.get("artifact_uri") or "").strip(),
        "chain_depth": len(nodes),
        "total_proof_hash": total_proof_hash,
        "nodes": nodes,
        "gate": gate,
    }


def aggregate_chain(utxo_id: str, sb: Any, *, max_depth: int = 256) -> dict[str, Any]:
    """
    Backward-compatible alias for aggregate_provenance_chain.
    """
    return aggregate_provenance_chain(utxo_id=utxo_id, sb=sb, max_depth=max_depth)


def get_full_lineage(utxo_id: str, sb: Any, *, max_depth: int = 256) -> dict[str, Any]:
    """
    Pull the full lineage payload for one BOQ asset branch:
    - all v://norm references
    - evidence photo hashes
    - QC conclusions by stage
    """
    agg = aggregate_provenance_chain(utxo_id=utxo_id, sb=sb, max_depth=max_depth)
    boq_item_uri = _to_text(agg.get("boq_item_uri") or "").strip()

    rows = []
    if boq_item_uri.startswith("v://"):
        rows = get_proof_chain(boq_item_uri, sb)
    if not rows:
        rows = ProofUTXOEngine(sb).get_chain(_to_text(utxo_id).strip(), max_depth=max_depth)

    project_uri = _to_text(agg.get("project_uri") or "").strip()
    if project_uri:
        scoped_rows = [row for row in rows if _to_text((row or {}).get("project_uri") or "").strip() == project_uri]
        if scoped_rows:
            rows = scoped_rows

    norm_refs: set[str] = set()
    evidence_hashes: list[dict[str, Any]] = []
    qc_conclusions: list[dict[str, Any]] = []
    signatures: list[dict[str, Any]] = []
    spatiotemporal_anchors: list[dict[str, Any]] = []
    seen_anchor_hash: set[str] = set()
    seen_signature_hash: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        for uri in _collect_norm_refs_from_row(row):
            norm_refs.add(uri)
        evidence_hashes.extend(_collect_evidence_hashes_from_row(row))
        qc_conclusions.append(_extract_qc_conclusion(row))
        anchor_hash = _to_text(sd.get("spatiotemporal_anchor_hash") or "").strip()
        if anchor_hash and anchor_hash not in seen_anchor_hash:
            seen_anchor_hash.add(anchor_hash)
            spatiotemporal_anchors.append(
                {
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "spatiotemporal_anchor_hash": anchor_hash,
                    "geo_location": _as_dict(sd.get("geo_location")),
                    "server_timestamp_proof": _as_dict(sd.get("server_timestamp_proof")),
                    "trip_action": _to_text(sd.get("trip_action") or "").strip().lower(),
                    "created_at": _to_text(row.get("created_at") or "").strip(),
                }
            )
        consensus = _as_dict(sd.get("consensus"))
        for item in _as_list(consensus.get("signatures")):
            if not isinstance(item, dict):
                continue
            sig_hash = _to_text(item.get("signature_hash") or "").strip().lower()
            if not sig_hash or sig_hash in seen_signature_hash:
                continue
            seen_signature_hash.add(sig_hash)
            signatures.append(item)

    qc_conclusions.sort(key=lambda x: _to_text(x.get("created_at") or ""))
    evidence_hashes.sort(key=lambda x: (_to_text(x.get("proof_id") or ""), _to_text(x.get("hash") or "")))

    return {
        **agg,
        "norm_refs": sorted(norm_refs),
        "evidence_hashes": evidence_hashes,
        "qc_conclusions": qc_conclusions,
        "consensus_signatures": signatures,
        "spatiotemporal_anchors": spatiotemporal_anchors,
    }


def _resolve_contract_quantity_from_row(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    ledger = _as_dict(sd.get("ledger"))
    for candidate in (
        sd.get("contract_quantity"),
        sd.get("approved_quantity"),
        sd.get("design_quantity"),
        _as_dict(sd.get("genesis_proof")).get("contract_quantity"),
        _as_dict(sd.get("genesis_proof")).get("initial_quantity"),
        ledger.get("initial_balance"),
    ):
        num = _to_float(candidate)
        if num is not None:
            return float(num)
    return 0.0


def _variation_delta_from_row(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    variation = _as_dict(sd.get("variation"))
    delta_utxo = _as_dict(sd.get("delta_utxo"))
    ledger = _as_dict(sd.get("ledger"))
    for candidate in (
        variation.get("delta_amount"),
        variation.get("delta_quantity"),
        variation.get("change_amount"),
        delta_utxo.get("delta_amount"),
        ledger.get("last_delta_amount"),
    ):
        num = _to_float(candidate)
        if num is not None:
            return float(num)
    return 0.0


def _variation_reference_from_row(row: dict[str, Any]) -> dict[str, Any]:
    sd = _as_dict(row.get("state_data"))
    variation = _as_dict(sd.get("variation"))
    meta = _as_dict(variation.get("metadata"))

    def _pick(*keys: str) -> str:
        for key in keys:
            text = _to_text(variation.get(key) or meta.get(key) or sd.get(key) or "").strip()
            if text:
                return text
        return ""

    ref_no = _pick(
        "design_change_no",
        "change_order_no",
        "change_no",
        "variation_order_no",
        "document_no",
        "reference_no",
    )
    ref_date = _pick(
        "design_change_date",
        "change_date",
        "approved_at",
        "verified_at",
    ) or _to_text(row.get("created_at") or "").strip()
    reason = _pick("reason", "description", "change_reason")
    return {
        "reference_no": ref_no,
        "reference_date": ref_date,
        "reason": reason,
    }


def _format_qty(value: float) -> str:
    text = f"{float(value):.4f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def trace_asset_origin(
    *,
    sb: Any,
    utxo_id: str = "",
    boq_item_uri: str = "",
    project_uri: str = "",
    max_depth: int = 512,
) -> dict[str, Any]:
    """
    Trace quantity origin:
    contract(genesis) -> variation deltas -> measured(settlement)
    """
    normalized_utxo = _to_text(utxo_id).strip()
    normalized_boq = _to_text(boq_item_uri).strip()
    normalized_project = _to_text(project_uri).strip()
    if not normalized_utxo and not normalized_boq:
        raise HTTPException(400, "utxo_id or boq_item_uri is required")

    engine = ProofUTXOEngine(sb)
    latest: dict[str, Any] | None = None
    if normalized_utxo:
        latest = engine.get_by_id(normalized_utxo)
    if latest and not normalized_boq:
        normalized_boq = _resolve_boq_item_uri(latest)
    if not latest and normalized_boq:
        latest = _resolve_latest_boq_row(sb=sb, boq_item_uri=normalized_boq, project_uri=normalized_project)
    if not latest:
        raise HTTPException(404, "asset origin trace target not found")
    if not normalized_boq:
        normalized_boq = _resolve_boq_item_uri(latest)
    if not normalized_boq:
        raise HTTPException(404, "boq_item_uri cannot be resolved for lineage trace")

    chain_rows = get_proof_chain(normalized_boq, sb, max_depth=max_depth)
    if normalized_project:
        scoped = [x for x in chain_rows if _to_text((x or {}).get("project_uri") or "").strip() == normalized_project]
        if scoped:
            chain_rows = scoped
    if not chain_rows and normalized_utxo:
        chain_rows = engine.get_chain(normalized_utxo, max_depth=max_depth)
    if not chain_rows:
        raise HTTPException(404, "proof chain not found for asset origin trace")
    chain_rows.sort(key=lambda row: _to_text((row or {}).get("created_at") or ""))

    genesis = next(
        (
            row
            for row in chain_rows
            if _to_text((row or {}).get("proof_type") or "").strip().lower() == "zero_ledger"
            or _to_text(_as_dict((row or {}).get("state_data")).get("lifecycle_stage") or "").strip().upper() == "INITIAL"
        ),
        chain_rows[0],
    )
    genesis_id = _to_text(genesis.get("proof_id") or "").strip()
    contract_qty = _resolve_contract_quantity_from_row(genesis)
    if contract_qty <= 1e-12:
        scoped_project_for_baseline = _to_text(latest.get("project_uri") or normalized_project).strip()
        if scoped_project_for_baseline:
            try:
                status = get_boq_realtime_status(
                    sb=sb,
                    project_uri=scoped_project_for_baseline,
                    limit=10000,
                )
                matched = next(
                    (
                        _as_dict(x)
                        for x in _as_list(status.get("items"))
                        if _to_text(_as_dict(x).get("boq_item_uri") or "").strip() == normalized_boq
                    ),
                    {},
                )
                contract_qty = (
                    _to_float(matched.get("contract_quantity"))
                    or _to_float(matched.get("approved_quantity"))
                    or _to_float(matched.get("design_quantity"))
                    or contract_qty
                )
                contract_qty = float(contract_qty or 0.0)
            except Exception:
                contract_qty = float(contract_qty or 0.0)

    variation_sources: list[dict[str, Any]] = []
    total_variation_delta = 0.0
    for row in chain_rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
        action = _to_text(sd.get("trip_action") or "").strip().lower()
        if stage != "VARIATION" and action not in {"variation.record", "variation.delta.apply"}:
            continue
        delta = _variation_delta_from_row(row)
        if abs(delta) <= 1e-12:
            continue
        total_variation_delta += float(delta)
        ref = _variation_reference_from_row(row)
        variation_sources.append(
            {
                "proof_id": _to_text(row.get("proof_id") or "").strip(),
                "delta_quantity": round(float(delta), 6),
                "reference_no": _to_text(ref.get("reference_no") or "").strip(),
                "reference_date": _to_text(ref.get("reference_date") or "").strip(),
                "reason": _to_text(ref.get("reason") or "").strip(),
                "verified": _to_text(row.get("result") or "").strip().upper() == "PASS",
                "created_at": _to_text(row.get("created_at") or "").strip(),
            }
        )
    variation_sources.sort(key=lambda x: _to_text(x.get("created_at") or ""))

    settlement_rows = [
        row
        for row in chain_rows
        if _to_text(_as_dict((row or {}).get("state_data")).get("lifecycle_stage") or "").strip().upper() == "SETTLEMENT"
        and _to_text((row or {}).get("result") or "").strip().upper() == "PASS"
    ]
    measured_qty = 0.0
    if settlement_rows:
        for row in settlement_rows:
            measured_qty += _extract_settled_quantity(row, fallback_design=None)
    if measured_qty <= 1e-12:
        measured_qty = _extract_settled_quantity(chain_rows[-1], fallback_design=contract_qty)
    if measured_qty <= 1e-12:
        scoped_project_for_settled = _to_text(latest.get("project_uri") or normalized_project).strip()
        if scoped_project_for_settled:
            try:
                status = get_boq_realtime_status(
                    sb=sb,
                    project_uri=scoped_project_for_settled,
                    limit=10000,
                )
                matched = next(
                    (
                        _as_dict(x)
                        for x in _as_list(status.get("items"))
                        if _to_text(_as_dict(x).get("boq_item_uri") or "").strip() == normalized_boq
                    ),
                    {},
                )
                measured_qty = float(_to_float(matched.get("settled_quantity")) or measured_qty)
            except Exception:
                pass

    delta_vs_contract = float(measured_qty - contract_qty)
    unexplained_delta = float(delta_vs_contract - total_variation_delta)

    item_no = _item_no_from_boq_uri(normalized_boq)
    smu_id = _smu_id_from_item_no(item_no)
    scoped_project = _to_text(latest.get("project_uri") or normalized_project).strip()
    lineage_base = scoped_project.rstrip("/") if scoped_project.startswith("v://") else "v://lineage"
    lineage_path: list[dict[str, Any]] = []
    for idx, row in enumerate(chain_rows, start=1):
        sd = _as_dict(row.get("state_data"))
        stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
        proof_id = _to_text(row.get("proof_id") or "").strip()
        lineage_path.append(
            {
                "index": idx,
                "proof_id": proof_id,
                "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                "stage": stage or _to_text(row.get("proof_type") or "").strip().upper(),
                "action": _to_text(sd.get("trip_action") or "").strip().lower(),
                "result": _to_text(row.get("result") or "").strip().upper(),
                "created_at": _to_text(row.get("created_at") or "").strip(),
                "lineage_uri": f"{lineage_base}/lineage/{_safe_path_token(item_no or 'item', fallback='item')}/{idx:03d}",
            }
        )

    highlighted = None
    if variation_sources:
        highlighted = max(variation_sources, key=lambda x: abs(float(x.get("delta_quantity") or 0.0)))

    statement = (
        f"本表实测量为 {_format_qty(measured_qty)}，合同量 {_format_qty(contract_qty)}，差异 {_format_qty(delta_vs_contract)}。"
    )
    if highlighted:
        ref_no = _to_text(highlighted.get("reference_no") or "设计变更单").strip()
        ref_date = _to_text(highlighted.get("reference_date") or "").strip()
        ver = "已验真" if bool(highlighted.get("verified")) else "待复核"
        statement += (
            f" 其中 {_format_qty(float(highlighted.get('delta_quantity') or 0.0))} "
            f"来自于 {ref_date or '-'} 的 {ref_no}（{ver}）。"
        )

    payload = {
        "ok": True,
        "project_uri": scoped_project,
        "smu_id": smu_id,
        "boq_item_uri": normalized_boq,
        "item_no": item_no,
        "latest_proof_id": _to_text(chain_rows[-1].get("proof_id") or "").strip(),
        "genesis_utxo_id": genesis_id,
        "contract_quantity": round(contract_qty, 6),
        "measured_quantity": round(float(measured_qty), 6),
        "delta_vs_contract": round(delta_vs_contract, 6),
        "variation_total_delta": round(total_variation_delta, 6),
        "unexplained_delta": round(unexplained_delta, 6),
        "variation_sources": variation_sources,
        "lineage_path": lineage_path,
        "lineage_uri": f"{lineage_base}/lineage/{_safe_path_token(item_no or 'item', fallback='item')}/",
        "statement": statement,
    }
    payload["lineage_proof_hash"] = _sha256_json(
        {
            "project_uri": payload["project_uri"],
            "boq_item_uri": payload["boq_item_uri"],
            "latest_proof_id": payload["latest_proof_id"],
            "genesis_utxo_id": payload["genesis_utxo_id"],
            "contract_quantity": payload["contract_quantity"],
            "measured_quantity": payload["measured_quantity"],
            "delta_vs_contract": payload["delta_vs_contract"],
            "variation_sources": payload["variation_sources"],
        }
    )
    return payload


def _resolve_latest_boq_row(
    *,
    sb: Any,
    boq_item_uri: str,
    project_uri: str | None = None,
) -> dict[str, Any] | None:
    normalized = _to_text(boq_item_uri).strip()
    if not normalized:
        return None
    scoped_project_uri = _to_text(project_uri or "").strip()
    try:
        q = sb.table("proof_utxo").select("*").filter("state_data->>boq_item_uri", "eq", normalized)
        if scoped_project_uri:
            q = q.eq("project_uri", scoped_project_uri)
        rows = q.order("created_at", desc=True).limit(1).execute().data or []
        if rows:
            return rows[0]
    except Exception:
        pass
    try:
        q = sb.table("proof_utxo").select("*").eq("segment_uri", normalized)
        if scoped_project_uri:
            q = q.eq("project_uri", scoped_project_uri)
        rows = q.order("created_at", desc=True).limit(1).execute().data or []
        if rows:
            return rows[0]
    except Exception:
        pass
    return None


def _resolve_transfer_input_row(*, sb: Any, item_id: str, project_uri: str | None = None) -> dict[str, Any] | None:
    normalized = _to_text(item_id).strip()
    if not normalized:
        return None
    scoped_project_uri = _to_text(project_uri or "").strip()

    engine = ProofUTXOEngine(sb)
    if normalized.upper().startswith("GP-"):
        row = engine.get_by_id(normalized)
        if row and scoped_project_uri and _to_text(row.get("project_uri") or "").strip() != scoped_project_uri:
            return None
        return row

    try:
        q = sb.table("proof_utxo").select("*").eq("spent", False).filter("state_data->>boq_item_uri", "eq", normalized)
        if scoped_project_uri:
            q = q.eq("project_uri", scoped_project_uri)
        rows = q.order("created_at", desc=True).limit(1).execute().data or []
        if rows:
            return rows[0]
    except Exception:
        pass

    # fallback scan for old records without JSON index
    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("spent", False)
            .order("created_at", desc=True)
            .limit(5000)
            .execute()
            .data
            or []
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            if scoped_project_uri and _to_text(row.get("project_uri") or "").strip() != scoped_project_uri:
                continue
            sd = _as_dict(row.get("state_data"))
            if _to_text(sd.get("boq_item_uri") or sd.get("item_uri") or sd.get("boq_uri") or "").strip() == normalized:
                return row
    except Exception:
        return None
    return None


def _resolve_ledger_balance(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    ledger = _as_dict(sd.get("ledger"))
    for candidate in (
        ledger.get("current_balance"),
        ledger.get("remaining_balance"),
        ledger.get("balance"),
        sd.get("remaining_quantity"),
        sd.get("available_quantity"),
        sd.get("design_quantity"),
        ledger.get("initial_balance"),
    ):
        num = _to_float(candidate)
        if num is not None:
            return max(0.0, float(num))
    return 0.0


def _resolve_genesis_balance(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    ledger = _as_dict(sd.get("ledger"))
    for candidate in (
        ledger.get("initial_balance"),
        sd.get("design_quantity"),
        _as_dict(sd.get("genesis_proof")).get("initial_quantity"),
        _resolve_ledger_balance(row),
    ):
        num = _to_float(candidate)
        if num is not None:
            return float(num)
    return 0.0


def _extract_variation_delta_amount(payload: dict[str, Any]) -> float | None:
    for key in ("delta_amount", "delta_quantity", "quantity_delta", "change_amount"):
        val = _to_float(payload.get(key))
        if val is not None:
            return float(val)
    return None


def _compute_delta_merge(
    *,
    input_row: dict[str, Any],
    delta_amount: float,
) -> dict[str, Any]:
    if abs(float(delta_amount)) <= 1e-9:
        raise HTTPException(400, "delta_amount must not be zero")

    sd = _as_dict(input_row.get("state_data"))
    ledger = _as_dict(sd.get("ledger"))
    current_balance = _resolve_ledger_balance(input_row)
    initial_balance = _resolve_genesis_balance(input_row)
    delta_total_prev = _to_float(ledger.get("delta_total")) or 0.0
    merged_total_prev = _to_float(ledger.get("merged_total"))
    if merged_total_prev is None:
        merged_total_prev = float(initial_balance + delta_total_prev)

    transferred_total = _to_float(ledger.get("transferred_total"))
    if transferred_total is None:
        transferred_total = max(0.0, float(merged_total_prev - current_balance))

    merged_total = float(merged_total_prev + delta_amount)
    balance_after = float(merged_total - transferred_total)
    if balance_after < -1e-9:
        raise HTTPException(
            409,
            f"delta underflow: balance_after={balance_after:.6f}; delta_amount={delta_amount:.6f}",
        )
    delta_total_after = float(delta_total_prev + delta_amount)

    return {
        "delta_amount": round(float(delta_amount), 6),
        "previous_balance": round(float(current_balance), 6),
        "balance_after": round(max(0.0, balance_after), 6),
        "initial_balance": round(float(initial_balance), 6),
        "transferred_total": round(float(transferred_total), 6),
        "delta_total_before": round(float(delta_total_prev), 6),
        "delta_total_after": round(float(delta_total_after), 6),
        "merged_total_before": round(float(merged_total_prev), 6),
        "merged_total_after": round(float(merged_total), 6),
    }


def _resolve_existing_offline_result(*, sb: Any, offline_packet_id: str) -> dict[str, Any] | None:
    packet_id = _to_text(offline_packet_id).strip()
    if not packet_id:
        return None
    try:
        tx_rows = (
            sb.table("proof_transaction")
            .select("*")
            .filter("trigger_data->>offline_packet_id", "eq", packet_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return None
    if not tx_rows:
        return None
    tx_row = tx_rows[0] if isinstance(tx_rows[0], dict) else {}
    output_ids = [_to_text(x).strip() for x in _as_list(tx_row.get("output_proofs")) if _to_text(x).strip()]
    output_id = output_ids[0] if output_ids else ""
    output_row = ProofUTXOEngine(sb).get_by_id(output_id) if output_id else None
    state_data = _as_dict((output_row or {}).get("state_data"))
    return {
        "offline_packet_id": packet_id,
        "tx_id": _to_text(tx_row.get("tx_id") or "").strip(),
        "tx_type": _to_text(tx_row.get("tx_type") or "").strip(),
        "tx_status": _to_text(tx_row.get("status") or "").strip(),
        "trigger_action": _to_text(tx_row.get("trigger_action") or "").strip(),
        "trigger_data": _as_dict(tx_row.get("trigger_data")),
        "output_proof_id": output_id,
        "proof_hash": _to_text((output_row or {}).get("proof_hash") or "").strip(),
        "result": _to_text((output_row or {}).get("result") or "").strip(),
        "proof_type": _to_text((output_row or {}).get("proof_type") or "").strip(),
        "boq_item_uri": _resolve_boq_item_uri(output_row) if isinstance(output_row, dict) else "",
        "spatiotemporal_anchor_hash": _to_text(state_data.get("spatiotemporal_anchor_hash") or "").strip(),
        "did_gate": _as_dict(state_data.get("did_gate")),
        "credit_endorsement": _as_dict(state_data.get("credit_endorsement")),
        "mirror_sync": _as_dict(state_data.get("shadow_mirror_sync")),
        "available_balance": _to_float(state_data.get("available_quantity")),
    }


def _offline_replay_sort_key(packet: dict[str, Any]) -> tuple[int, int, str]:
    st = _as_dict(packet.get("server_timestamp_proof"))
    ntp_client_ts = _to_text(st.get("client_timestamp") or st.get("captured_at") or "").strip()
    ntp_epoch = _parse_iso_epoch_ms(ntp_client_ts)
    if ntp_epoch is None:
        ntp_epoch = DEFAULT_OFFLINE_PACKET_SORT_EPOCH
    local_created = _parse_iso_epoch_ms(packet.get("local_created_at"))
    if local_created is None:
        local_created = DEFAULT_OFFLINE_PACKET_SORT_EPOCH
    packet_id = _to_text(packet.get("offline_packet_id") or "").strip()
    return (int(ntp_epoch), int(local_created), packet_id)


def _patch_state_data_fields(*, sb: Any, proof_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    normalized_proof_id = _to_text(proof_id).strip()
    if not normalized_proof_id:
        return {}
    engine = ProofUTXOEngine(sb)
    row = engine.get_by_id(normalized_proof_id)
    if not isinstance(row, dict):
        return {}
    state_data = dict(_as_dict(row.get("state_data")))
    state_data.update(_as_dict(patch))
    try:
        sb.table("proof_utxo").update({"state_data": state_data}).eq("proof_id", normalized_proof_id).execute()
    except Exception:
        return state_data
    return state_data


def update_chain_with_result(*, sb: Any, gate_output: dict[str, Any]) -> dict[str, Any]:
    payload = _as_dict(gate_output)
    output_proof_id = _to_text(payload.get("output_proof_id") or payload.get("proof_id") or "").strip()
    if not output_proof_id:
        raise HTTPException(400, "update_chain_with_result requires output_proof_id")

    engine = ProofUTXOEngine(sb)
    output_row = engine.get_by_id(output_proof_id)
    if not isinstance(output_row, dict):
        raise HTTPException(404, "output proof_utxo not found")

    state_data = _as_dict(output_row.get("state_data"))
    input_proof_id = _to_text(payload.get("input_proof_id") or "").strip()
    parent_proof_id = _to_text(state_data.get("parent_proof_id") or output_row.get("parent_proof_id") or "").strip()
    if input_proof_id and parent_proof_id and input_proof_id != parent_proof_id:
        raise HTTPException(
            409,
            f"write-back chain mismatch: input={input_proof_id} parent={parent_proof_id}",
        )

    gate_result = dict(_as_dict(state_data.get("qc_gate_result")))
    gate_result.update(
        {
            "gate_id": _to_text(
                payload.get("gate_id")
                or payload.get("linked_gate_id")
                or gate_result.get("gate_id")
                or state_data.get("linked_gate_id")
                or ""
            ).strip(),
            "linked_gate_id": _to_text(
                payload.get("linked_gate_id")
                or gate_result.get("linked_gate_id")
                or state_data.get("linked_gate_id")
                or ""
            ).strip(),
            "linked_gate_ids": _as_list(
                payload.get("linked_gate_ids")
                or gate_result.get("linked_gate_ids")
                or state_data.get("linked_gate_ids")
            ),
            "linked_gate_rules": _as_list(
                payload.get("linked_gate_rules")
                or gate_result.get("linked_gate_rules")
                or state_data.get("linked_gate_rules")
            ),
            "spec_dict_key": _to_text(
                payload.get("spec_dict_key")
                or gate_result.get("spec_dict_key")
                or state_data.get("spec_dict_key")
                or ""
            ).strip(),
            "spec_item": _to_text(
                payload.get("spec_item")
                or gate_result.get("spec_item")
                or state_data.get("spec_item")
                or ""
            ).strip(),
            "context_key": _to_text(
                payload.get("context_key")
                or gate_result.get("context_key")
                or ""
            ).strip(),
            "result": _normalize_result(
                _to_text(payload.get("result") or gate_result.get("result") or output_row.get("result") or "PENDING")
            ),
            "result_source": _to_text(
                payload.get("result_source")
                or gate_result.get("result_source")
                or state_data.get("result_source")
                or ""
            ).strip(),
            "spec_uri": _to_text(
                payload.get("spec_uri")
                or gate_result.get("spec_uri")
                or state_data.get("spec_uri")
                or ""
            ).strip(),
            "spec_snapshot": _to_text(
                payload.get("spec_snapshot")
                or gate_result.get("spec_snapshot")
                or state_data.get("spec_snapshot")
                or ""
            ).strip(),
            "quality_hash": _to_text(
                payload.get("quality_hash")
                or gate_result.get("quality_hash")
                or state_data.get("quality_hash")
                or ""
            ).strip(),
            "input_proof_id": input_proof_id or parent_proof_id,
            "output_proof_id": output_proof_id,
            "boq_item_uri": _to_text(
                payload.get("boq_item_uri")
                or gate_result.get("boq_item_uri")
                or state_data.get("boq_item_uri")
                or _resolve_boq_item_uri(output_row)
            ).strip(),
            "evaluated_at": _to_text(
                payload.get("evaluated_at")
                or gate_result.get("evaluated_at")
                or state_data.get("trip_executed_at")
                or output_row.get("created_at")
                or _utc_iso()
            ).strip(),
            "write_back_at": _utc_iso(),
            "write_back_chain": "same_parent_link",
        }
    )
    gate_result_hash = _sha256_json(gate_result)
    history = _as_list(state_data.get("qc_gate_history"))
    history.append(
        {
            "output_proof_id": output_proof_id,
            "result": gate_result.get("result"),
            "gate_id": gate_result.get("gate_id"),
            "quality_hash": gate_result.get("quality_hash"),
            "gate_result_hash": gate_result_hash,
            "write_back_at": gate_result.get("write_back_at"),
        }
    )
    if len(history) > 120:
        history = history[-120:]

    patched_state = _patch_state_data_fields(
        sb=sb,
        proof_id=output_proof_id,
        patch={
            "qc_gate_result": gate_result,
            "qc_gate_status": _to_text(gate_result.get("result") or "").strip().upper(),
            "qc_gate_result_hash": gate_result_hash,
            "qc_gate_history": history,
            "quality_status_on_chain": _to_text(gate_result.get("result") or "").strip().upper(),
        },
    )
    return {
        "ok": True,
        "input_proof_id": input_proof_id or parent_proof_id,
        "output_proof_id": output_proof_id,
        "qc_gate_result_hash": gate_result_hash,
        "state_data": patched_state,
    }


def _build_shadow_packet(
    *,
    output_row: dict[str, Any],
    tx: dict[str, Any],
    action: str,
    did_gate: dict[str, Any] | None = None,
    credit_endorsement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state_data = _as_dict(output_row.get("state_data"))
    return {
        "proof_id": _to_text(output_row.get("proof_id") or "").strip(),
        "proof_hash": _to_text(output_row.get("proof_hash") or "").strip(),
        "project_id": _to_text(output_row.get("project_id") or "").strip(),
        "project_uri": _to_text(output_row.get("project_uri") or "").strip(),
        "segment_uri": _to_text(output_row.get("segment_uri") or "").strip(),
        "proof_type": _to_text(output_row.get("proof_type") or "").strip(),
        "result": _to_text(output_row.get("result") or "").strip(),
        "trip_action": _to_text(state_data.get("trip_action") or action).strip(),
        "spatiotemporal_anchor_hash": _to_text(state_data.get("spatiotemporal_anchor_hash") or "").strip(),
        "did_gate": _as_dict(did_gate) if did_gate else _as_dict(state_data.get("did_gate")),
        "credit_endorsement": _as_dict(credit_endorsement) if credit_endorsement else _as_dict(state_data.get("credit_endorsement")),
        "tx": {
            "tx_id": _to_text(tx.get("tx_id") or "").strip(),
            "tx_type": _to_text(tx.get("tx_type") or "").strip(),
            "trigger_action": _to_text(tx.get("trigger_action") or "").strip(),
            "created_at": _to_text(tx.get("created_at") or "").strip(),
        },
        "created_at": _to_text(output_row.get("created_at") or "").strip(),
    }


def transfer_asset(
    *,
    sb: Any,
    item_id: str,
    amount: float,
    executor_uri: str = "v://executor/system/",
    executor_role: str = "DOCPEG",
    docpeg_proof_id: str = "",
    docpeg_hash: str = "",
    metadata: dict[str, Any] | None = None,
    project_uri: str | None = None,
) -> dict[str, Any]:
    """
    Consume one BOQ-related UTXO and mint next UTXO with debited ledger balance.
    `item_id` can be a proof_id or boq_item_uri.
    """
    transfer_amount = _to_float(amount)
    if transfer_amount is None or transfer_amount <= 0:
        raise HTTPException(400, "amount must be > 0")

    input_row = _resolve_transfer_input_row(sb=sb, item_id=item_id, project_uri=project_uri)
    if not input_row:
        raise HTTPException(404, "transfer input item not found")
    if bool(input_row.get("spent")):
        raise HTTPException(409, "transfer input already spent")

    balance = _resolve_ledger_balance(input_row)
    if transfer_amount > balance + 1e-9:
        raise HTTPException(409, f"insufficient_balance: balance={balance}, amount={transfer_amount}")
    remaining = max(0.0, float(balance - transfer_amount))

    engine = ProofUTXOEngine(sb)
    input_proof_id = _to_text(input_row.get("proof_id") or "").strip()
    sd = _as_dict(input_row.get("state_data"))
    ledger = dict(_as_dict(sd.get("ledger")))
    prev_transferred = _to_float(ledger.get("transferred_total")) or 0.0
    ledger.update(
        {
            "previous_balance": round(balance, 6),
            "current_balance": round(remaining, 6),
            "balance": round(remaining, 6),
            "transferred_total": round(prev_transferred + transfer_amount, 6),
            "last_transfer_at": _utc_iso(),
            "last_transfer_amount": round(float(transfer_amount), 6),
            "last_transfer_docpeg_proof_id": _to_text(docpeg_proof_id).strip(),
            "last_transfer_docpeg_hash": _to_text(docpeg_hash).strip(),
        }
    )

    history = _as_list(sd.get("transfer_history"))
    history.append(
        {
            "amount": round(float(transfer_amount), 6),
            "balance_after": round(remaining, 6),
            "executor_uri": _to_text(executor_uri).strip(),
            "docpeg_proof_id": _to_text(docpeg_proof_id).strip(),
            "docpeg_hash": _to_text(docpeg_hash).strip(),
            "at": _utc_iso(),
            "metadata": _as_dict(metadata),
        }
    )
    if len(history) > 30:
        history = history[-30:]

    next_state = dict(sd)
    next_state.update(
        {
            "lifecycle_stage": "ASSET_TRANSFER",
            "status": "ASSET_TRANSFER",
            "ledger": ledger,
            "transfer_history": history,
            "transfer_hash": _sha256_json(
                {
                    "input_proof_id": input_proof_id,
                    "amount": round(float(transfer_amount), 6),
                    "remaining": round(remaining, 6),
                    "docpeg_proof_id": _to_text(docpeg_proof_id).strip(),
                    "docpeg_hash": _to_text(docpeg_hash).strip(),
                }
            ),
        }
    )

    tx = engine.consume(
        input_proof_ids=[input_proof_id],
        output_states=[
            {
                "owner_uri": _to_text(input_row.get("owner_uri") or executor_uri).strip(),
                "project_id": input_row.get("project_id"),
                "project_uri": _to_text(input_row.get("project_uri") or "").strip(),
                "segment_uri": _to_text(input_row.get("segment_uri") or "").strip(),
                "proof_type": _to_text(input_row.get("proof_type") or "zero_ledger").strip() or "zero_ledger",
                "result": _normalize_result(_to_text(input_row.get("result") or "PASS")),
                "state_data": next_state,
                "conditions": _as_list(input_row.get("conditions")),
                "parent_proof_id": input_proof_id,
                "norm_uri": _to_text(input_row.get("norm_uri") or sd.get("norm_uri") or None) or None,
            }
        ],
        executor_uri=executor_uri,
        executor_role=executor_role,
        trigger_action="DocPeg.transfer_asset",
        trigger_data={
            "item_id": _to_text(item_id).strip(),
            "input_proof_id": input_proof_id,
            "amount": round(float(transfer_amount), 6),
            "docpeg_proof_id": _to_text(docpeg_proof_id).strip(),
            "docpeg_hash": _to_text(docpeg_hash).strip(),
        },
        tx_type="consume",
    )

    output_ids = [_to_text(x).strip() for x in _as_list(tx.get("output_proofs")) if _to_text(x).strip()]
    output_id = output_ids[0] if output_ids else ""
    output_row = engine.get_by_id(output_id) if output_id else None

    return {
        "ok": True,
        "item_id": _to_text(item_id).strip(),
        "input_proof_id": input_proof_id,
        "output_proof_id": output_id,
        "balance_before": round(balance, 6),
        "amount": round(float(transfer_amount), 6),
        "balance_after": round(remaining, 6),
        "transfer_hash": _to_text(_as_dict(output_row.get("state_data") if isinstance(output_row, dict) else {}).get("transfer_hash") or "").strip(),
        "tx": tx,
    }


def ingest_sensor_data(
    *,
    sb: Any,
    device_id: str,
    raw_payload: Any,
    boq_item_uri: str,
    project_uri: str | None = None,
    executor_uri: str = "v://executor/system/",
    executor_did: str = "",
    executor_role: str = "TRIPROLE",
    metadata: dict[str, Any] | None = None,
    credentials_vc: list[dict[str, Any]] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_device_id = _to_text(device_id).strip()
    if not normalized_device_id:
        raise HTTPException(400, "device_id is required")
    normalized_boq_item_uri = _to_text(boq_item_uri).strip()
    if not normalized_boq_item_uri.startswith("v://"):
        raise HTTPException(400, "boq_item_uri is required and must start with v://")

    parsed_payload, raw_payload_hash = _decode_sensor_payload(raw_payload)
    sensor_data = _normalize_sensor_payload(normalized_device_id, parsed_payload)
    if not sensor_data["boq_item_uri"]:
        sensor_data["boq_item_uri"] = normalized_boq_item_uri
    if sensor_data["boq_item_uri"] != normalized_boq_item_uri:
        raise HTTPException(409, "sensor payload boq_item_uri mismatch")

    expected_hash = _to_text(
        parsed_payload.get("payload_hash")
        or parsed_payload.get("packet_hash")
        or parsed_payload.get("raw_payload_hash")
        or ""
    ).strip().lower()
    if expected_hash and expected_hash not in {
        _to_text(sensor_data.get("sensor_payload_hash") or "").strip().lower(),
        _to_text(raw_payload_hash).strip().lower(),
    }:
        raise HTTPException(409, "sensor payload hash mismatch")

    latest_row = _resolve_latest_boq_row(sb=sb, boq_item_uri=normalized_boq_item_uri, project_uri=project_uri)
    if isinstance(latest_row, dict) and (not _is_leaf_boq_row(latest_row)):
        raise HTTPException(409, "sensor ingest is only allowed for leaf BOQ nodes")
    resolved_project_uri = _to_text(
        project_uri
        or (latest_row or {}).get("project_uri")
        or parsed_payload.get("project_uri")
        or ""
    ).strip()
    if not resolved_project_uri.startswith("v://"):
        raise HTTPException(400, "project_uri is required for sensor ingest")
    resolved_project_id = (latest_row or {}).get("project_id")
    resolved_owner_uri = _to_text((latest_row or {}).get("owner_uri") or executor_uri).strip() or executor_uri
    resolved_segment_uri = _to_text((latest_row or {}).get("segment_uri") or normalized_boq_item_uri).strip()
    parent_proof_id = _to_text((latest_row or {}).get("proof_id") or "").strip() or None

    required_credential = resolve_required_credential(
        action="measure.record",
        boq_item_uri=normalized_boq_item_uri,
        payload=parsed_payload,
    )
    did_gate = verify_credential(
        sb=sb,
        user_did=_to_text(executor_did).strip(),
        required_credential=required_credential,
        project_uri=resolved_project_uri,
        boq_item_uri=normalized_boq_item_uri,
        payload_credentials=credentials_vc,
    )
    if not bool(did_gate.get("ok")):
        raise HTTPException(
            403,
            f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
        )

    now_iso = _utc_iso()
    anchor = _build_spatiotemporal_anchor(
        action="sensor.ingest",
        input_proof_id=parent_proof_id or normalized_boq_item_uri,
        executor_uri=_to_text(executor_uri).strip(),
        now_iso=now_iso,
        geo_location_raw=geo_location if geo_location else parsed_payload.get("geo_location"),
        server_timestamp_raw=(
            server_timestamp_proof
            if server_timestamp_proof
            else parsed_payload.get("server_timestamp_proof")
        ),
    )

    state_data = {
        "trip_action": "sensor.ingest",
        "trip_executor": _to_text(executor_uri).strip(),
        "executor_did": _to_text(executor_did).strip(),
        "trip_executed_at": now_iso,
        "lifecycle_stage": "PRECHECK",
        "status": "PRECHECK",
        "boq_item_uri": normalized_boq_item_uri,
        "measurement": {
            "value": sensor_data.get("value"),
            "values": sensor_data.get("values"),
            "unit": sensor_data.get("unit"),
            "measured_at": sensor_data.get("measured_at"),
            "source": "iot_direct",
        },
        "sensor_hardware": sensor_data.get("sensor_hardware"),
        "sensor_payload_hash": sensor_data.get("sensor_payload_hash"),
        "sensor_reading_hash": sensor_data.get("sensor_reading_hash"),
        "sensor_raw_payload_hash": raw_payload_hash,
        "did_gate": did_gate,
        "metadata": _as_dict(metadata),
        "parent_proof_id": parent_proof_id,
        **anchor,
    }

    seed = hashlib.sha256(
        f"{normalized_device_id}|{normalized_boq_item_uri}|{now_iso}|{sensor_data.get('sensor_reading_hash')}".encode(
            "utf-8"
        )
    ).hexdigest()[:16].upper()
    proof_id = f"GP-PROOF-{seed}"
    engine = ProofUTXOEngine(sb)
    created = engine.create(
        proof_id=proof_id,
        owner_uri=resolved_owner_uri,
        project_id=resolved_project_id,
        project_uri=resolved_project_uri,
        segment_uri=resolved_segment_uri,
        proof_type="inspection",
        result="PENDING",
        state_data=state_data,
        conditions=_as_list((latest_row or {}).get("conditions")),
        parent_proof_id=parent_proof_id,
        norm_uri=_to_text((latest_row or {}).get("norm_uri") or "").strip() or None,
        signer_uri=_to_text(executor_uri).strip(),
        signer_role=_to_text(executor_role).strip() or "TRIPROLE",
    )

    credit_endorsement: dict[str, Any] = {}
    if _to_text(executor_did).strip().startswith("did:"):
        try:
            credit_endorsement = calculate_sovereign_credit(
                sb=sb,
                project_uri=resolved_project_uri,
                participant_did=_to_text(executor_did).strip(),
            )
        except Exception:
            credit_endorsement = {}
    try:
        mirror_sync = sync_to_mirrors(
            proof_packet=_build_shadow_packet(
                output_row=created,
                tx={"tx_id": "", "tx_type": "create", "trigger_action": "TripRole(sensor.ingest)", "created_at": now_iso},
                action="sensor.ingest",
                did_gate=did_gate,
                credit_endorsement=credit_endorsement,
            ),
            sb=sb,
            project_id=_to_text(created.get("project_id") or "").strip(),
            project_uri=_to_text(created.get("project_uri") or "").strip(),
        )
    except Exception:
        mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}
    patched_state = _patch_state_data_fields(
        sb=sb,
        proof_id=_to_text(created.get("proof_id") or "").strip(),
        patch={
            "credit_endorsement": credit_endorsement,
            "shadow_mirror_sync": mirror_sync,
        },
    )
    if patched_state:
        created["state_data"] = patched_state

    return {
        "ok": True,
        "action": "sensor.ingest",
        "proof_id": _to_text(created.get("proof_id") or "").strip(),
        "proof_hash": _to_text(created.get("proof_hash") or "").strip(),
        "project_uri": resolved_project_uri,
        "boq_item_uri": normalized_boq_item_uri,
        "sensor_hardware": sensor_data.get("sensor_hardware"),
        "measurement": state_data.get("measurement"),
        "did_gate": did_gate,
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "spatiotemporal_anchor_hash": _to_text(anchor.get("spatiotemporal_anchor_hash") or "").strip(),
    }


def apply_variation(
    *,
    sb: Any,
    boq_item_uri: str,
    delta_amount: float,
    reason: str = "",
    project_uri: str | None = None,
    executor_uri: str = "v://executor/system/",
    executor_did: str = "",
    executor_role: str = "TRIPROLE",
    offline_packet_id: str = "",
    metadata: dict[str, Any] | None = None,
    credentials_vc: list[dict[str, Any]] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_boq_item_uri = _to_text(boq_item_uri).strip()
    if not normalized_boq_item_uri.startswith("v://"):
        raise HTTPException(400, "boq_item_uri is required and must start with v://")
    normalized_offline_packet_id = _to_text(offline_packet_id).strip()
    if normalized_offline_packet_id:
        reused = _resolve_existing_offline_result(sb=sb, offline_packet_id=normalized_offline_packet_id)
        if reused:
            return {
                "ok": True,
                "replayed": True,
                "boq_item_uri": reused.get("boq_item_uri") or normalized_boq_item_uri,
                "output_proof_id": reused.get("output_proof_id") or "",
                "proof_hash": reused.get("proof_hash") or "",
                "did_gate": reused.get("did_gate") or {},
                "credit_endorsement": reused.get("credit_endorsement") or {},
                "mirror_sync": reused.get("mirror_sync") or {},
                "spatiotemporal_anchor_hash": reused.get("spatiotemporal_anchor_hash") or "",
                "available_balance": reused.get("available_balance"),
                "offline_packet_id": normalized_offline_packet_id,
                "tx": {
                    "tx_id": reused.get("tx_id") or "",
                    "tx_type": reused.get("tx_type") or "",
                    "status": reused.get("tx_status") or "success",
                    "reused": True,
                },
            }

    input_row = _resolve_transfer_input_row(sb=sb, item_id=normalized_boq_item_uri, project_uri=project_uri)
    if not input_row:
        raise HTTPException(404, "no unspent UTXO found for boq_item_uri")
    if bool(input_row.get("spent")):
        raise HTTPException(409, "input_proof already spent")
    if not _is_leaf_boq_row(input_row):
        raise HTTPException(409, "apply_variation is only allowed for leaf BOQ nodes")

    input_proof_id = _to_text(input_row.get("proof_id") or "").strip()
    if not input_proof_id:
        raise HTTPException(500, "invalid input proof row")
    normalized_project_uri = _to_text(input_row.get("project_uri") or project_uri or "").strip()
    normalized_executor_did = _to_text(executor_did).strip()
    required_credential = resolve_required_credential(
        action="variation.delta.apply",
        boq_item_uri=normalized_boq_item_uri,
        payload=_as_dict(metadata),
    )
    did_gate = verify_credential(
        sb=sb,
        user_did=normalized_executor_did,
        required_credential=required_credential,
        project_uri=normalized_project_uri,
        boq_item_uri=normalized_boq_item_uri,
        payload_credentials=credentials_vc,
    )
    if not bool(did_gate.get("ok")):
        raise HTTPException(
            403,
            f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
        )

    now_iso = _utc_iso()
    anchor = _build_spatiotemporal_anchor(
        action="variation.delta.apply",
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        now_iso=now_iso,
        geo_location_raw=geo_location,
        server_timestamp_raw=server_timestamp_proof,
    )
    merge = _compute_delta_merge(input_row=input_row, delta_amount=float(delta_amount))

    input_sd = _as_dict(input_row.get("state_data"))
    base_ledger = dict(_as_dict(input_sd.get("ledger")))
    base_ledger.update(
        {
            "initial_balance": merge["initial_balance"],
            "delta_total": merge["delta_total_after"],
            "merged_total": merge["merged_total_after"],
            "transferred_total": merge["transferred_total"],
            "previous_balance": merge["previous_balance"],
            "current_balance": merge["balance_after"],
            "remaining_balance": merge["balance_after"],
            "balance": merge["balance_after"],
            "last_delta_amount": merge["delta_amount"],
            "last_delta_reason": _to_text(reason).strip(),
            "last_delta_at": now_iso,
            "last_delta_executor_uri": _to_text(executor_uri).strip(),
        }
    )

    variation_entry = {
        "delta_amount": merge["delta_amount"],
        "reason": _to_text(reason).strip() or "variation_instruction",
        "mode": "delta_utxo_merge",
        "applied_at": now_iso,
        "executor_uri": _to_text(executor_uri).strip(),
        "source_input_proof_id": input_proof_id,
        "merged_total_after": merge["merged_total_after"],
        "balance_after": merge["balance_after"],
        "metadata": _as_dict(metadata),
    }
    variation_history = _as_list(input_sd.get("variation_history"))
    variation_history.append(variation_entry)
    if len(variation_history) > 50:
        variation_history = variation_history[-50:]

    next_state = dict(input_sd)
    next_state.update(
        {
            "trip_action": "variation.delta.apply",
            "trip_executor": _to_text(executor_uri).strip(),
            "executor_did": normalized_executor_did,
            "trip_executed_at": now_iso,
            "parent_proof_id": input_proof_id,
            "parent_hash": _to_text(input_row.get("proof_hash") or "").strip(),
            "lifecycle_stage": "VARIATION",
            "status": "VARIATION",
            "boq_item_uri": normalized_boq_item_uri,
            "variation": variation_entry,
            "delta_utxo": {
                "delta_amount": merge["delta_amount"],
                "reason": variation_entry["reason"],
                "merge_strategy": "genesis_plus_delta_minus_transferred",
                "merged_total_before": merge["merged_total_before"],
                "merged_total_after": merge["merged_total_after"],
                "previous_balance": merge["previous_balance"],
                "balance_after": merge["balance_after"],
            },
            "variation_history": variation_history,
            "did_gate": did_gate,
            "available_quantity": merge["balance_after"],
            "remaining_quantity": merge["balance_after"],
            "ledger": base_ledger,
            "compensates": [input_proof_id],
            "source_fail_proof_id": input_proof_id if _to_text(input_row.get("result") or "").strip().upper() == "FAIL" else "",
            "variation_hash": _sha256_json(
                {
                    "input_proof_id": input_proof_id,
                    "delta_amount": merge["delta_amount"],
                    "reason": variation_entry["reason"],
                    "anchor": anchor,
                    "metadata": _as_dict(metadata),
                }
            ),
            **anchor,
        }
    )

    engine = ProofUTXOEngine(sb)
    tx = engine.consume(
        input_proof_ids=[input_proof_id],
        output_states=[
            {
                "owner_uri": _to_text(input_row.get("owner_uri") or executor_uri).strip(),
                "project_id": input_row.get("project_id"),
                "project_uri": _to_text(input_row.get("project_uri") or "").strip(),
                "segment_uri": _to_text(input_row.get("segment_uri") or normalized_boq_item_uri).strip(),
                "proof_type": "archive",
                "result": "PASS",
                "state_data": next_state,
                "conditions": _as_list(input_row.get("conditions")),
                "parent_proof_id": input_proof_id,
                "norm_uri": _to_text(input_row.get("norm_uri") or input_sd.get("norm_uri") or None) or None,
            }
        ],
        executor_uri=_to_text(executor_uri).strip(),
        executor_role=_to_text(executor_role).strip() or "TRIPROLE",
        trigger_action="TripRole.apply_variation",
        trigger_data={
            "boq_item_uri": normalized_boq_item_uri,
            "delta_amount": merge["delta_amount"],
            "reason": variation_entry["reason"],
            "source_input_proof_id": input_proof_id,
            "executor_did": normalized_executor_did,
            "did_gate_hash": _to_text(did_gate.get("did_gate_hash") or "").strip(),
            "required_credential": _to_text(did_gate.get("required_credential") or "").strip(),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "offline_packet_id": normalized_offline_packet_id,
        },
        tx_type="merge",
    )

    output_ids = [_to_text(x).strip() for x in _as_list(tx.get("output_proofs")) if _to_text(x).strip()]
    output_id = output_ids[0] if output_ids else ""
    output_row = engine.get_by_id(output_id) if output_id else None
    credit_endorsement: dict[str, Any] = {}
    mirror_sync: dict[str, Any] = {}
    if isinstance(output_row, dict):
        try:
            credit_endorsement = calculate_sovereign_credit(
                sb=sb,
                project_uri=normalized_project_uri,
                participant_did=normalized_executor_did,
            )
        except Exception:
            credit_endorsement = {}
        try:
            shadow_packet = _build_shadow_packet(
                output_row=output_row,
                tx=tx,
                action="variation.delta.apply",
                did_gate=did_gate,
                credit_endorsement=credit_endorsement,
            )
            mirror_sync = sync_to_mirrors(
                proof_packet=shadow_packet,
                sb=sb,
                project_id=_to_text(output_row.get("project_id") or "").strip(),
                project_uri=_to_text(output_row.get("project_uri") or "").strip(),
            )
        except Exception:
            mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}
        patched_state = _patch_state_data_fields(
            sb=sb,
            proof_id=output_id,
            patch={
                "credit_endorsement": credit_endorsement,
                "shadow_mirror_sync": mirror_sync,
            },
        )
        output_row["state_data"] = patched_state

    return {
        "ok": True,
        "boq_item_uri": normalized_boq_item_uri,
        "input_proof_id": input_proof_id,
        "output_proof_id": output_id,
        "delta_amount": merge["delta_amount"],
        "merged_total_after": merge["merged_total_after"],
        "available_balance": merge["balance_after"],
        "did_gate": did_gate,
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
        "offline_packet_id": normalized_offline_packet_id,
        "proof_hash": _to_text((output_row or {}).get("proof_hash") or "").strip(),
        "tx": tx,
    }


def _validate_transition(action: str, input_row: dict[str, Any]) -> None:
    if bool(input_row.get("spent")):
        raise HTTPException(409, "input_proof already spent")

    stage = _stage_from_row(input_row)
    result = _to_text(input_row.get("result") or "").strip().upper()

    if action == "quality.check" and stage not in {"INITIAL", "UNKNOWN"}:
        raise HTTPException(409, f"quality.check expects INITIAL input, got {stage}")

    if action == "measure.record" and stage not in {"ENTRY", "VARIATION"}:
        raise HTTPException(409, f"measure.record expects ENTRY/VARIATION input, got {stage}")
    if action == "measure.record" and stage == "ENTRY" and result != "PASS":
        raise HTTPException(409, "measure.record requires quality.check PASS or variation compensation")

    if action == "variation.record" and result != "FAIL":
        raise HTTPException(409, "variation.record requires FAIL input")

    if action == "settlement.confirm" and stage not in {"INSTALLATION", "VARIATION"}:
        raise HTTPException(409, f"settlement.confirm expects INSTALLATION/VARIATION input, got {stage}")
    if action == "dispute.resolve":
        ptype = _to_text(input_row.get("proof_type") or "").strip().lower()
        if ptype != "dispute":
            raise HTTPException(409, f"dispute.resolve expects dispute input, got {ptype or '-'}")


def execute_triprole_action(*, sb: Any, body: Any) -> dict[str, Any]:
    """Execute a TripRole action over one input UTXO and create next-state UTXO."""
    action = _normalize_action(getattr(body, "action", None) if not isinstance(body, dict) else body.get("action"))
    if action not in VALID_TRIPROLE_ACTIONS:
        raise HTTPException(400, f"unsupported action: {action}")

    input_proof_id = _to_text(
        getattr(body, "input_proof_id", None) if not isinstance(body, dict) else body.get("input_proof_id")
    ).strip()
    if not input_proof_id:
        raise HTTPException(400, "input_proof_id is required")

    executor_uri = _to_text(
        getattr(body, "executor_uri", None) if not isinstance(body, dict) else body.get("executor_uri")
    ).strip()
    if not executor_uri:
        raise HTTPException(400, "executor_uri is required")

    executor_role = _to_text(
        getattr(body, "executor_role", None) if not isinstance(body, dict) else body.get("executor_role")
    ).strip() or "TRIPROLE"
    executor_did = _to_text(
        getattr(body, "executor_did", None) if not isinstance(body, dict) else body.get("executor_did")
    ).strip()

    override_result = _to_text(
        getattr(body, "result", None) if not isinstance(body, dict) else body.get("result")
    ).strip()
    offline_packet_id = _to_text(
        getattr(body, "offline_packet_id", None) if not isinstance(body, dict) else body.get("offline_packet_id")
    ).strip()
    payload_raw = getattr(body, "payload", None) if not isinstance(body, dict) else body.get("payload")
    payload = _as_dict(payload_raw)
    credentials_vc_raw = (
        getattr(body, "credentials_vc", None) if not isinstance(body, dict) else body.get("credentials_vc")
    )
    signer_metadata_raw = (
        getattr(body, "signer_metadata", None) if not isinstance(body, dict) else body.get("signer_metadata")
    )
    if executor_did == "":
        executor_did = _to_text(
            payload.get("executor_did")
            or payload.get("operator_did")
            or payload.get("actor_did")
            or ""
        ).strip()
    if credentials_vc_raw is None:
        credentials_vc_raw = payload.get("credentials_vc")
    if signer_metadata_raw is None:
        signer_metadata_raw = payload.get("signer_metadata")
    body_geo_location_raw = getattr(body, "geo_location", None) if not isinstance(body, dict) else body.get("geo_location")
    body_server_timestamp_raw = (
        getattr(body, "server_timestamp_proof", None)
        if not isinstance(body, dict)
        else body.get("server_timestamp_proof")
    )

    boq_item_uri_override = _to_text(
        getattr(body, "boq_item_uri", None) if not isinstance(body, dict) else body.get("boq_item_uri")
    ).strip()
    segment_uri_override = _to_text(
        getattr(body, "segment_uri", None) if not isinstance(body, dict) else body.get("segment_uri")
    ).strip()

    engine = ProofUTXOEngine(sb)
    if offline_packet_id:
        reused = _resolve_existing_offline_result(sb=sb, offline_packet_id=offline_packet_id)
        if reused:
            return {
                "ok": True,
                "replayed": True,
                "action": action,
                "input_proof_id": _to_text(reused.get("trigger_data", {}).get("input_proof_id") or "").strip(),
                "output_proof_id": reused.get("output_proof_id") or "",
                "proof_hash": reused.get("proof_hash") or "",
                "proof_type": reused.get("proof_type") or "",
                "result": reused.get("result") or "",
                "boq_item_uri": reused.get("boq_item_uri") or "",
                "did_gate": reused.get("did_gate") or {},
                "credit_endorsement": reused.get("credit_endorsement") or {},
                "mirror_sync": reused.get("mirror_sync") or {},
                "spatiotemporal_anchor_hash": reused.get("spatiotemporal_anchor_hash") or "",
                "available_balance": reused.get("available_balance"),
                "offline_packet_id": offline_packet_id,
                "tx": {
                    "tx_id": reused.get("tx_id") or "",
                    "tx_type": reused.get("tx_type") or "",
                    "status": reused.get("tx_status") or "success",
                    "reused": True,
                },
            }
    input_row = engine.get_by_id(input_proof_id)
    if not input_row:
        raise HTTPException(404, "input proof_utxo not found")
    if not _is_leaf_boq_row(input_row):
        raise HTTPException(409, f"{action} is only allowed for leaf BOQ nodes")

    if action == "scan.entry":
        input_sd = _as_dict(input_row.get("state_data"))
        project_uri = _to_text(input_row.get("project_uri") or "").strip()
        project_id = input_row.get("project_id")
        owner_uri = _to_text(input_row.get("owner_uri") or "").strip() or executor_uri
        segment_uri = _resolve_segment_uri(input_row, payload, segment_uri_override)
        boq_item_uri = _resolve_boq_item_uri(input_row, boq_item_uri_override)
        required_credential = resolve_required_credential(
            action=action,
            boq_item_uri=boq_item_uri,
            payload=payload,
        )
        did_gate = verify_credential(
            sb=sb,
            user_did=executor_did,
            required_credential=required_credential,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
            payload_credentials=credentials_vc_raw,
        )
        if not bool(did_gate.get("ok")):
            raise HTTPException(
                403,
                f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
            )
        parent_hash = _to_text(input_row.get("proof_hash") or "").strip()
        now_iso = _utc_iso()
        anchor = _build_spatiotemporal_anchor(
            action=action,
            input_proof_id=input_proof_id,
            executor_uri=executor_uri,
            now_iso=now_iso,
            geo_location_raw=body_geo_location_raw if body_geo_location_raw is not None else payload.get("geo_location"),
            server_timestamp_raw=(
                body_server_timestamp_raw if body_server_timestamp_raw is not None else payload.get("server_timestamp_proof")
            ),
        )
        project_boundary = _resolve_project_boundary(
            sb=sb,
            project_id=project_id,
            project_uri=project_uri,
            override=payload.get("project_boundary") or payload.get("site_boundary"),
        )
        geo_compliance = check_location_compliance(
            _as_dict(anchor.get("geo_location")),
            project_boundary,
        )
        scan_status = _to_text(payload.get("status") or "ok").strip().lower()
        scan_result = "PASS" if scan_status in {"ok", "pass", "success"} else "FAIL"
        scan_entry = dict(payload)
        if not scan_entry.get("scan_entry_at"):
            scan_entry["scan_entry_at"] = now_iso
        scan_entry["geo_compliance"] = geo_compliance
        state_data = dict(input_sd)
        state_data.update(
            {
                "trip_action": action,
                "trip_executor": executor_uri,
                "executor_did": executor_did,
                "trip_executed_at": now_iso,
                "lifecycle_stage": "SCAN_ENTRY",
                "status": "SCAN_ENTRY",
                "parent_proof_id": input_proof_id,
                "parent_hash": parent_hash,
                "boq_item_uri": boq_item_uri or _to_text(input_sd.get("boq_item_uri") or "").strip(),
                "scan_entry": scan_entry,
                "scan_entry_hash": _sha256_json(scan_entry),
                "did_gate": did_gate,
                "geo_location": anchor.get("geo_location"),
                "server_timestamp_proof": anchor.get("server_timestamp_proof"),
                "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
                "geo_compliance": geo_compliance,
                "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
            }
        )
        proof_id_seed = hashlib.sha256(f"{input_proof_id}|scan.entry|{now_iso}".encode("utf-8")).hexdigest()[:16].upper()
        proof_id = f"GP-SCAN-{proof_id_seed}"
        created = engine.create(
            proof_id=proof_id,
            owner_uri=owner_uri,
            project_id=project_id,
            project_uri=project_uri,
            segment_uri=segment_uri or boq_item_uri,
            proof_type="scan_entry",
            result=scan_result,
            state_data=state_data,
            conditions=_as_list(input_row.get("conditions")),
            parent_proof_id=input_proof_id,
            norm_uri="v://norm/CoordOS/ScanEntry/1.0",
            signer_uri=_to_text(executor_uri).strip(),
            signer_role=_to_text(executor_role).strip() or "TRIPROLE",
        )
        return {
            "ok": True,
            "action": action,
            "input_proof_id": input_proof_id,
            "output_proof_id": _to_text(created.get("proof_id") or "").strip(),
            "proof_hash": _to_text(created.get("proof_hash") or "").strip(),
            "proof_type": "scan_entry",
            "result": scan_result,
            "boq_item_uri": boq_item_uri,
            "did_gate": did_gate,
            "geo_compliance": geo_compliance,
            "spatiotemporal_anchor_hash": _to_text(anchor.get("spatiotemporal_anchor_hash") or "").strip(),
        }

    if action in {"meshpeg.verify", "formula.price", "gateway.sync"}:
        input_sd = _as_dict(input_row.get("state_data"))
        project_uri = _to_text(input_row.get("project_uri") or "").strip()
        project_id = input_row.get("project_id")
        owner_uri = _to_text(input_row.get("owner_uri") or "").strip() or executor_uri
        segment_uri = _resolve_segment_uri(input_row, payload, segment_uri_override)
        boq_item_uri = _resolve_boq_item_uri(input_row, boq_item_uri_override)
        required_credential = resolve_required_credential(
            action=action,
            boq_item_uri=boq_item_uri,
            payload=payload,
        )
        did_gate = verify_credential(
            sb=sb,
            user_did=executor_did,
            required_credential=required_credential,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
            payload_credentials=credentials_vc_raw,
        )
        if not bool(did_gate.get("ok")):
            raise HTTPException(
                403,
                f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
            )
        parent_hash = _to_text(input_row.get("proof_hash") or "").strip()
        now_iso = _utc_iso()
        anchor = _build_spatiotemporal_anchor(
            action=action,
            input_proof_id=input_proof_id,
            executor_uri=executor_uri,
            now_iso=now_iso,
            geo_location_raw=body_geo_location_raw if body_geo_location_raw is not None else payload.get("geo_location"),
            server_timestamp_raw=(
                body_server_timestamp_raw if body_server_timestamp_raw is not None else payload.get("server_timestamp_proof")
            ),
        )
        project_boundary = _resolve_project_boundary(
            sb=sb,
            project_id=project_id,
            project_uri=project_uri,
            override=payload.get("project_boundary") or payload.get("site_boundary"),
        )
        geo_compliance = check_location_compliance(
            _as_dict(anchor.get("geo_location")),
            project_boundary,
        )
        status = _to_text(payload.get("status") or payload.get("result") or "PASS").strip().upper()
        result = "PASS" if status in {"PASS", "OK", "SUCCESS"} else "FAIL"
        if action == "meshpeg.verify":
            lifecycle = "MESHPEG"
            proof_type = "meshpeg"
            norm_uri = "v://norm/CoordOS/MeshPeg/1.0"
            record_key = "meshpeg"
        elif action == "formula.price":
            lifecycle = "PRICING"
            proof_type = "railpact"
            norm_uri = "v://norm/CoordOS/FormulaPeg/1.0"
            record_key = "railpact"
        else:
            lifecycle = "GATEWAY_SYNC"
            proof_type = "gateway_sync"
            norm_uri = "v://norm/CoordOS/Gateway/1.0"
            record_key = "gateway_sync"

        record = dict(payload)
        record.setdefault("created_at", now_iso)
        state_data = dict(input_sd)
        state_data.update(
            {
                "trip_action": action,
                "trip_executor": executor_uri,
                "executor_did": executor_did,
                "trip_executed_at": now_iso,
                "lifecycle_stage": lifecycle,
                "status": lifecycle,
                "parent_proof_id": input_proof_id,
                "parent_hash": parent_hash,
                "boq_item_uri": boq_item_uri or _to_text(input_sd.get("boq_item_uri") or "").strip(),
                record_key: record,
                f"{record_key}_hash": _sha256_json(record),
                "did_gate": did_gate,
                "geo_location": anchor.get("geo_location"),
                "server_timestamp_proof": anchor.get("server_timestamp_proof"),
                "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
                "geo_compliance": geo_compliance,
                "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
            }
        )
        proof_id_seed = hashlib.sha256(f"{input_proof_id}|{action}|{now_iso}".encode("utf-8")).hexdigest()[:16].upper()
        proof_id = f"GP-{record_key.upper()}-{proof_id_seed}"
        created = engine.create(
            proof_id=proof_id,
            owner_uri=owner_uri,
            project_id=project_id,
            project_uri=project_uri,
            segment_uri=segment_uri or boq_item_uri,
            proof_type=proof_type,
            result=result,
            state_data=state_data,
            conditions=_as_list(input_row.get("conditions")),
            parent_proof_id=input_proof_id,
            norm_uri=norm_uri,
            signer_uri=_to_text(executor_uri).strip(),
            signer_role=_to_text(executor_role).strip() or "TRIPROLE",
        )
        return {
            "ok": True,
            "action": action,
            "input_proof_id": input_proof_id,
            "output_proof_id": _to_text(created.get("proof_id") or "").strip(),
            "proof_hash": _to_text(created.get("proof_hash") or "").strip(),
            "proof_type": proof_type,
            "result": result,
            "boq_item_uri": boq_item_uri,
            "did_gate": did_gate,
            "geo_compliance": geo_compliance,
            "spatiotemporal_anchor_hash": _to_text(anchor.get("spatiotemporal_anchor_hash") or "").strip(),
        }

    _validate_transition(action, input_row)

    input_sd = _as_dict(input_row.get("state_data"))
    project_uri = _to_text(input_row.get("project_uri") or "").strip()
    project_id = input_row.get("project_id")
    owner_uri = _to_text(input_row.get("owner_uri") or "").strip() or executor_uri
    segment_uri = _resolve_segment_uri(input_row, payload, segment_uri_override)
    boq_item_uri = _resolve_boq_item_uri(input_row, boq_item_uri_override)
    required_credential = resolve_required_credential(
        action=action,
        boq_item_uri=boq_item_uri,
        payload=payload,
    )
    did_gate = verify_credential(
        sb=sb,
        user_did=executor_did,
        required_credential=required_credential,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
        payload_credentials=credentials_vc_raw,
    )
    if not bool(did_gate.get("ok")):
        raise HTTPException(
            403,
            f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
        )
    gate_binding = _resolve_subitem_gate_binding(
        sb=sb,
        input_row=input_row,
        boq_item_uri=boq_item_uri,
        payload=payload,
    )

    parent_hash = _to_text(input_row.get("proof_hash") or "").strip()
    now_iso = _utc_iso()
    anchor = _build_spatiotemporal_anchor(
        action=action,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        now_iso=now_iso,
        geo_location_raw=body_geo_location_raw if body_geo_location_raw is not None else payload.get("geo_location"),
        server_timestamp_raw=(
            body_server_timestamp_raw if body_server_timestamp_raw is not None else payload.get("server_timestamp_proof")
        ),
    )
    normalized_signer_metadata = _normalize_signer_metadata(signer_metadata_raw)
    project_boundary = _resolve_project_boundary(
        sb=sb,
        project_id=project_id,
        project_uri=project_uri,
        override=payload.get("project_boundary") or payload.get("site_boundary"),
    )
    geo_compliance = check_location_compliance(
        _as_dict(anchor.get("geo_location")),
        project_boundary,
    )

    next_proof_type = "inspection"
    next_result = _normalize_result(override_result or _to_text(payload.get("result") or "PASS"))
    tx_type = "consume"
    biometric_check: dict[str, Any] = {}

    next_state: dict[str, Any] = dict(input_sd)
    next_state.update(
        {
            "trip_action": action,
            "trip_executor": executor_uri,
            "executor_did": executor_did,
            "trip_executed_at": now_iso,
            "offline_packet_id": offline_packet_id,
            "parent_proof_id": input_proof_id,
            "parent_hash": parent_hash,
            "boq_item_uri": boq_item_uri or _to_text(input_sd.get("boq_item_uri") or "").strip(),
            "did_gate": did_gate,
            "geo_location": anchor.get("geo_location"),
            "server_timestamp_proof": anchor.get("server_timestamp_proof"),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "geo_compliance": geo_compliance,
            "trust_level": _to_text(geo_compliance.get("trust_level") or "").strip() or _to_text(input_sd.get("trust_level") or "").strip(),
            "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
            "linked_gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
            "linked_gate_ids": _as_list(gate_binding.get("linked_gate_ids")),
            "linked_gate_rules": _as_list(gate_binding.get("linked_gate_rules")),
            "linked_spec_uri": _to_text(gate_binding.get("linked_spec_uri") or "").strip(),
            "spec_dict_key": _to_text(gate_binding.get("spec_dict_key") or "").strip(),
            "spec_item": _to_text(gate_binding.get("spec_item") or "").strip(),
            "gate_template_lock": bool(gate_binding.get("gate_template_lock")),
            "gate_binding_hash": _to_text(gate_binding.get("gate_binding_hash") or "").strip(),
        }
    )
    if _as_list(normalized_signer_metadata.get("signers")):
        next_state["signer_metadata"] = normalized_signer_metadata

    if action == "quality.check":
        next_proof_type = "inspection"
        requested_spec_uri = _to_text(payload.get("spec_uri") or payload.get("norm_uri") or "").strip()
        bound_spec_uri = _to_text(
            gate_binding.get("linked_spec_uri")
            or input_sd.get("linked_spec_uri")
            or input_sd.get("spec_uri")
            or ""
        ).strip()
        if bool(gate_binding.get("gate_template_lock")) and bound_spec_uri:
            if requested_spec_uri and requested_spec_uri != bound_spec_uri:
                raise HTTPException(
                    409,
                    f"spec_template_locked: {boq_item_uri} is bound to {bound_spec_uri}",
                )
            spec_uri = bound_spec_uri
        else:
            spec_uri = requested_spec_uri or _to_text(input_sd.get("spec_uri") or "").strip()
        design_value = _to_float(payload.get("design"))
        if design_value is None:
            design_value = _to_float(payload.get("standard"))
        values_for_eval = _extract_values(payload)
        norm_eval: dict[str, Any] = {}
        threshold_pack: dict[str, Any] = {}
        context_payload = {
            "context": payload.get("context") or payload.get("component_type") or payload.get("part"),
            "component_type": payload.get("component_type") or payload.get("part"),
            "structure_type": payload.get("structure_type"),
            "stake": payload.get("stake") or payload.get("location"),
        }
        dynamic_pack = resolve_dynamic_threshold(
            sb=sb,
            gate_id=_to_text(gate_binding.get("linked_gate_id") or "").strip(),
            context=context_payload,
        )
        if bool(dynamic_pack.get("found")):
            threshold_pack = dynamic_pack
            norm_eval = evaluate_with_threshold_pack(
                threshold_pack=threshold_pack,
                values=values_for_eval,
                design_value=design_value,
            )
        elif spec_uri:
            norm_eval = resolve_normpeg_eval(
                spec_uri=spec_uri,
                context=context_payload,
                values=values_for_eval,
                design_value=design_value,
                sb=sb,
            )
            threshold_pack = _as_dict(norm_eval.get("threshold"))

        auto_result = _to_text(norm_eval.get("result") or "").strip().upper()
        if override_result:
            next_result = _normalize_result(override_result)
        elif auto_result in {"PASS", "FAIL", "OBSERVE", "PENDING"}:
            next_result = _normalize_result(auto_result)
        else:
            next_result = _normalize_result(_to_text(payload.get("result") or "PASS"))

        next_state.update(
            {
                "lifecycle_stage": "ENTRY",
                "status": "ENTRY",
                "quality_payload": payload,
                "result_source": "normpeg_dynamic" if threshold_pack.get("found") else "manual",
                "spec_uri": _to_text(
                    threshold_pack.get("effective_spec_uri")
                    or threshold_pack.get("spec_uri")
                    or spec_uri
                    or input_sd.get("spec_uri")
                    or ""
                ).strip(),
                "spec_snapshot": _to_text(
                    threshold_pack.get("spec_excerpt") or input_sd.get("spec_snapshot") or ""
                ).strip(),
                "qc_gate_binding": {
                    "linked_gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
                    "linked_gate_ids": _as_list(gate_binding.get("linked_gate_ids")),
                    "linked_gate_rules": _as_list(gate_binding.get("linked_gate_rules")),
                    "linked_spec_uri": _to_text(gate_binding.get("linked_spec_uri") or "").strip(),
                    "spec_dict_key": _to_text(gate_binding.get("spec_dict_key") or "").strip(),
                    "spec_item": _to_text(gate_binding.get("spec_item") or "").strip(),
                    "gate_template_lock": bool(gate_binding.get("gate_template_lock")),
                    "gate_binding_hash": _to_text(gate_binding.get("gate_binding_hash") or "").strip(),
                },
                "norm_evaluation": {
                    "matched": bool(norm_eval.get("matched")) if norm_eval else False,
                    "result": _to_text(norm_eval.get("result") or "").strip().upper() if norm_eval else "",
                    "deviation_percent": norm_eval.get("deviation_percent") if norm_eval else None,
                    "values_for_eval": norm_eval.get("values_for_eval") if norm_eval else values_for_eval,
                    "design_value": norm_eval.get("design_value") if norm_eval else design_value,
                    "lower": norm_eval.get("lower") if norm_eval else None,
                    "upper": norm_eval.get("upper") if norm_eval else None,
                    "center": norm_eval.get("center") if norm_eval else None,
                    "tolerance": norm_eval.get("tolerance") if norm_eval else None,
                    "threshold": threshold_pack,
                },
                "quality_hash": _sha256_json(
                    {
                        "input_proof_id": input_proof_id,
                        "payload": payload,
                        "boq_item_uri": boq_item_uri,
                        "segment_uri": segment_uri,
                        "spec_uri": _to_text(
                            threshold_pack.get("effective_spec_uri")
                            or threshold_pack.get("spec_uri")
                            or spec_uri
                        ).strip(),
                        "spec_snapshot": _to_text(threshold_pack.get("spec_excerpt") or "").strip(),
                        "result": next_result,
                        "values_for_eval": values_for_eval,
                    }
                ),
            }
        )
        gate_result_payload = {
            "gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
            "linked_gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
            "linked_gate_ids": _as_list(gate_binding.get("linked_gate_ids")),
            "linked_gate_rules": _as_list(gate_binding.get("linked_gate_rules")),
            "spec_dict_key": _to_text(gate_binding.get("spec_dict_key") or "").strip(),
            "spec_item": _to_text(gate_binding.get("spec_item") or "").strip(),
            "context_key": _to_text(threshold_pack.get("context_key") or "").strip(),
            "result": _to_text(next_result or "").strip().upper(),
            "result_source": _to_text(next_state.get("result_source") or "").strip(),
            "spec_uri": _to_text(next_state.get("spec_uri") or "").strip(),
            "spec_snapshot": _to_text(next_state.get("spec_snapshot") or "").strip(),
            "quality_hash": _to_text(next_state.get("quality_hash") or "").strip(),
            "input_proof_id": input_proof_id,
            "boq_item_uri": boq_item_uri,
            "item_code": _to_text(input_sd.get("item_no") or _item_no_from_boq_uri(boq_item_uri)).strip(),
            "evaluated_at": now_iso,
        }
        next_state["qc_gate_result"] = gate_result_payload
        next_state["qc_gate_status"] = _to_text(next_result or "").strip().upper()
        next_state["qc_gate_result_hash"] = _sha256_json(gate_result_payload)

    elif action == "measure.record":
        next_proof_type = "approval"
        outside_fence = bool(geo_compliance.get("outside"))
        next_state.update(
            {
                "lifecycle_stage": "INSTALLATION",
                "status": "INSTALLATION",
                "measurement": payload,
                "measurement_hash": _sha256_json(
                    {
                        "input_proof_id": input_proof_id,
                        "payload": payload,
                        "segment_uri": segment_uri,
                        "boq_item_uri": boq_item_uri,
                    }
                ),
                "trust_level": "LOW" if outside_fence else "HIGH",
                "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
            }
        )
        sensor_hardware = _as_dict(payload.get("sensor_hardware"))
        if sensor_hardware:
            next_state["sensor_hardware"] = sensor_hardware
            next_state["sensor_hardware_fingerprint"] = _sha256_json(sensor_hardware)
        if outside_fence and bool(geo_compliance.get("strict_mode")):
            raise HTTPException(409, "geo-fence violation: measure.record blocked by strict_mode")

    elif action == "variation.record":
        next_proof_type = "archive"
        next_result = _normalize_result(override_result or _to_text(payload.get("result") or "PASS"))
        delta_amount = _extract_variation_delta_amount(payload)
        compensates = _build_variation_compensates(payload, input_proof_id)
        variation_payload = dict(payload)
        if delta_amount is not None:
            variation_payload["delta_amount"] = round(float(delta_amount), 6)
        next_state.update(
            {
                "lifecycle_stage": "VARIATION",
                "status": "VARIATION",
                "variation": variation_payload,
                "compensates": compensates,
                "source_fail_proof_id": input_proof_id,
                "variation_hash": _sha256_json(
                    {
                        "input_proof_id": input_proof_id,
                        "payload": variation_payload,
                        "compensates": compensates,
                    }
                ),
            }
        )
        if delta_amount is not None and abs(float(delta_amount)) > 1e-9:
            merge = _compute_delta_merge(input_row=input_row, delta_amount=float(delta_amount))
            ledger = dict(_as_dict(next_state.get("ledger")))
            ledger.update(
                {
                    "initial_balance": merge["initial_balance"],
                    "delta_total": merge["delta_total_after"],
                    "merged_total": merge["merged_total_after"],
                    "transferred_total": merge["transferred_total"],
                    "previous_balance": merge["previous_balance"],
                    "current_balance": merge["balance_after"],
                    "remaining_balance": merge["balance_after"],
                    "balance": merge["balance_after"],
                    "last_delta_amount": merge["delta_amount"],
                    "last_delta_reason": _to_text(payload.get("reason") or "").strip() or "variation.record",
                    "last_delta_at": now_iso,
                    "last_delta_executor_uri": executor_uri,
                }
            )
            next_state.update(
                {
                    "ledger": ledger,
                    "available_quantity": merge["balance_after"],
                    "remaining_quantity": merge["balance_after"],
                    "delta_utxo": {
                        "delta_amount": merge["delta_amount"],
                        "merge_strategy": "genesis_plus_delta_minus_transferred",
                        "merged_total_before": merge["merged_total_before"],
                        "merged_total_after": merge["merged_total_after"],
                        "previous_balance": merge["previous_balance"],
                        "balance_after": merge["balance_after"],
                    },
                }
            )

    elif action == "dispute.resolve":
        next_proof_type = "dispute_resolution"
        next_result = _normalize_result(override_result or _to_text(payload.get("result") or "PASS"))
        resolution_payload = dict(payload)
        resolution_payload["resolved_at"] = now_iso
        next_state.update(
            {
                "lifecycle_stage": "DISPUTE_RESOLUTION",
                "status": "RESOLVED" if next_result == "PASS" else "REJECTED",
                "resolution": resolution_payload,
                "resolution_hash": _sha256_json(resolution_payload),
            }
        )

    elif action == "settlement.confirm":
        next_proof_type = "payment"
        tx_type = "settle"

        # Block if any unresolved dispute exists.
        try:
            open_dispute = (
                sb.table("proof_utxo")
                .select("proof_id")
                .eq("segment_uri", boq_item_uri)
                .eq("proof_type", "dispute")
                .eq("spent", False)
                .limit(1)
                .execute()
                .data
                or []
            )
            if open_dispute:
                raise HTTPException(409, f"consensus_dispute_open: {open_dispute[0].get('proof_id')}")
        except HTTPException:
            raise
        except Exception:
            pass

        agg_before = aggregate_provenance_chain(input_proof_id, sb)
        gate = _as_dict(agg_before.get("gate"))
        if bool(gate.get("blocked")):
            raise HTTPException(
                409,
                f"QCGate locked: {gate.get('reason')}; uncompensated={','.join(gate.get('uncompensated_fail_proof_ids') or [])}",
            )
        dual_gate = resolve_dual_pass_gate(
            sb=sb,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
        )
        if not bool(dual_gate.get("ok")):
            raise HTTPException(
                409,
                f"dual_pass_gate_failed: qc_pass={dual_gate.get('qc_pass_count')} lab_pass={dual_gate.get('lab_pass_count')}",
            )

        signatures_raw = payload.get("signatures")
        if signatures_raw is None:
            signatures_raw = payload.get("consensus_signatures")
        if signatures_raw is None and not isinstance(body, dict):
            signatures_raw = getattr(body, "signatures", None)
        if signatures_raw is None and not isinstance(body, dict):
            signatures_raw = getattr(body, "consensus_signatures", None)
        elif signatures_raw is None and isinstance(body, dict):
            signatures_raw = body.get("signatures")
        if signatures_raw is None and isinstance(body, dict):
            signatures_raw = body.get("consensus_signatures")
        consensus_signatures = _normalize_consensus_signatures(signatures_raw)
        consensus_check = _validate_consensus_signatures(consensus_signatures)
        if not consensus_check.get("ok"):
            missing = ",".join(consensus_check.get("missing_roles") or [])
            invalid = ",".join(consensus_check.get("invalid") or [])
            raise HTTPException(
                409,
                f"consensus_signatures_incomplete; missing={missing or '-'}; invalid={invalid or '-'}",
            )
        biometric_check = verify_biometric_status(
            signer_metadata=normalized_signer_metadata,
            consensus_signatures=consensus_signatures,
            required_roles=CONSENSUS_REQUIRED_ROLES,
        )
        if not bool(biometric_check.get("ok")):
            missing = ",".join(_as_list(biometric_check.get("missing")))
            failed = ",".join(_as_list(biometric_check.get("failed")))
            raise HTTPException(
                409,
                f"biometric_verification_incomplete; missing={missing or '-'}; failed={failed or '-'}",
            )

        conflict = detect_consensus_deviation(
            signer_metadata_raw=signer_metadata_raw,
            payload=payload,
            input_sd=input_sd,
        )
        if conflict.get("conflict"):
            dispute = _create_consensus_dispute(
                sb=sb,
                input_row=input_row,
                project_uri=project_uri,
                boq_item_uri=boq_item_uri,
                executor_uri=executor_uri,
                conflict=conflict,
                consensus_signatures=consensus_signatures,
                signer_metadata=normalized_signer_metadata,
            )
            dispute_id = _to_text(dispute.get("proof_id") or "").strip()
            raise HTTPException(
                409,
                f"consensus_conflict_detected; dispute_proof_id={dispute_id or '-'}",
            )

        artifact_seed = hashlib.sha256(f"{input_proof_id}|{now_iso}|{project_uri}".encode("utf-8")).hexdigest()[:16]
        artifact_uri = _to_text(payload.get("artifact_uri") or "").strip()
        if not artifact_uri:
            base = project_uri.rstrip("/") if project_uri else "v://project"
            artifact_token = _safe_path_token(boq_item_uri or segment_uri or "settlement", fallback="settlement")
            artifact_uri = f"{base}/artifact/{artifact_token}/{artifact_seed}"

        next_state.update(
            {
                "lifecycle_stage": "SETTLEMENT",
                "status": "SETTLEMENT",
                "settlement": payload,
                "settlement_confirmed_at": now_iso,
                "pre_settlement_total_hash": _to_text(agg_before.get("total_proof_hash") or "").strip(),
                "artifact_uri": artifact_uri,
                "consensus": {
                    "required_roles": list(CONSENSUS_REQUIRED_ROLES),
                    "signatures": consensus_check.get("consensus_payload", {}).get("signatures") or [],
                    "consensus_hash": _to_text(consensus_check.get("consensus_hash") or ""),
                    "consensus_complete": True,
                },
                "signatures": consensus_check.get("consensus_payload", {}).get("signatures") or [],
                "biometric_verification": biometric_check,
                "dual_pass_gate": dual_gate,
            }
        )

    tx = engine.consume(
        input_proof_ids=[input_proof_id],
        output_states=[
            {
                "owner_uri": owner_uri,
                "project_id": project_id,
                "project_uri": project_uri,
                "segment_uri": segment_uri,
                "proof_type": next_proof_type,
                "result": next_result,
                "state_data": next_state,
                "conditions": _as_list(input_row.get("conditions")),
                "parent_proof_id": input_proof_id,
                "norm_uri": _to_text(input_row.get("norm_uri") or input_sd.get("norm_uri") or None) or None,
            }
        ],
        executor_uri=executor_uri,
        executor_role=executor_role,
        trigger_action=f"TripRole({action})",
        trigger_data={
            "action": action,
            "input_proof_id": input_proof_id,
            "boq_item_uri": boq_item_uri,
            "executor_did": executor_did,
            "did_gate_hash": _to_text(did_gate.get("did_gate_hash") or "").strip(),
            "required_credential": _to_text(did_gate.get("required_credential") or "").strip(),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "geo_compliance_trust_level": _to_text(geo_compliance.get("trust_level") or "").strip(),
            "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
            "biometric_metadata_hash": _to_text(biometric_check.get("metadata_hash") or "").strip(),
            "offline_packet_id": offline_packet_id,
        },
        tx_type=tx_type,
    )

    output_ids = [_to_text(x).strip() for x in _as_list(tx.get("output_proofs")) if _to_text(x).strip()]
    if not output_ids:
        raise HTTPException(500, "triprole execution produced no outputs")

    output_proof_id = output_ids[0]
    output_row = engine.get_by_id(output_proof_id)
    if not output_row:
        raise HTTPException(500, "output proof_utxo not found after execution")
    quality_chain_writeback: dict[str, Any] = {}
    remediation: dict[str, Any] = {}
    if action == "quality.check":
        quality_chain_writeback = update_chain_with_result(
            sb=sb,
            gate_output={
                **_as_dict(next_state.get("qc_gate_result")),
                "input_proof_id": input_proof_id,
                "output_proof_id": output_proof_id,
                "result": _to_text(next_result or "").strip().upper(),
                "result_source": _to_text(next_state.get("result_source") or "").strip(),
                "spec_uri": _to_text(next_state.get("spec_uri") or "").strip(),
                "spec_snapshot": _to_text(next_state.get("spec_snapshot") or "").strip(),
                "quality_hash": _to_text(next_state.get("quality_hash") or "").strip(),
                "boq_item_uri": boq_item_uri,
                "linked_gate_id": _to_text(next_state.get("linked_gate_id") or "").strip(),
                "linked_gate_ids": _as_list(next_state.get("linked_gate_ids")),
                "linked_gate_rules": _as_list(next_state.get("linked_gate_rules")),
                "evaluated_at": now_iso,
            },
        )
        if _as_dict(quality_chain_writeback.get("state_data")):
            output_row["state_data"] = _as_dict(quality_chain_writeback.get("state_data"))
        if _to_text(output_row.get("result") or "").strip().upper() == "FAIL":
            try:
                remediation = open_remediation_trip(
                    sb=sb,
                    fail_proof_id=output_proof_id,
                    notice=_to_text(payload.get("remediation_notice") or "Auto remediation notice").strip(),
                    executor_uri=executor_uri,
                    due_date=_to_text(payload.get("remediation_due_date") or "").strip(),
                    assignees=[_to_text(x).strip() for x in _as_list(payload.get("remediation_assignees")) if _to_text(x).strip()],
                )
            except Exception as exc:
                remediation = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    credit_endorsement: dict[str, Any] = {}
    mirror_sync: dict[str, Any] = {}
    try:
        credit_endorsement = calculate_sovereign_credit(
            sb=sb,
            project_uri=project_uri,
            participant_did=executor_did,
        )
    except Exception:
        credit_endorsement = {}
    try:
        mirror_sync = sync_to_mirrors(
            proof_packet=_build_shadow_packet(
                output_row=output_row,
                tx=tx,
                action=action,
                did_gate=did_gate,
                credit_endorsement=credit_endorsement,
            ),
            sb=sb,
            project_id=_to_text(output_row.get("project_id") or "").strip(),
            project_uri=_to_text(output_row.get("project_uri") or "").strip(),
        )
    except Exception:
        mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}
    patched_state = _patch_state_data_fields(
        sb=sb,
        proof_id=output_proof_id,
        patch={
            "credit_endorsement": credit_endorsement,
            "shadow_mirror_sync": mirror_sync,
        },
    )
    if patched_state:
        output_row["state_data"] = patched_state

    agg_after = aggregate_provenance_chain(output_proof_id, sb)

    return {
        "ok": True,
        "action": action,
        "input_proof_id": input_proof_id,
        "output_proof_id": output_proof_id,
        "parent_hash": parent_hash,
        "proof_hash": _to_text(output_row.get("proof_hash") or "").strip(),
        "proof_type": _to_text(output_row.get("proof_type") or "").strip(),
        "result": _to_text(output_row.get("result") or "").strip(),
        "segment_uri": _to_text(output_row.get("segment_uri") or "").strip(),
        "boq_item_uri": _resolve_boq_item_uri(output_row),
        "did_gate": did_gate,
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "quality_chain_writeback": quality_chain_writeback,
        "remediation": remediation,
        "spatiotemporal_anchor_hash": _to_text(_as_dict(output_row.get("state_data")).get("spatiotemporal_anchor_hash") or "").strip(),
        "geo_compliance": _as_dict(_as_dict(output_row.get("state_data")).get("geo_compliance")),
        "biometric_verification": _as_dict(_as_dict(output_row.get("state_data")).get("biometric_verification")),
        "offline_packet_id": offline_packet_id,
        "available_balance": _to_float(_as_dict(output_row.get("state_data")).get("available_quantity")),
        "artifact_uri": _to_text(_as_dict(output_row.get("state_data")).get("artifact_uri") or "").strip(),
        "gitpeg_anchor": _to_text(output_row.get("gitpeg_anchor") or "").strip(),
        "tx": tx,
        "provenance": agg_after,
    }


def replay_offline_packets(
    *,
    sb: Any,
    packets: list[dict[str, Any]],
    stop_on_error: bool = False,
    default_executor_uri: str = "v://executor/system/",
    default_executor_role: str = "TRIPROLE",
) -> dict[str, Any]:
    normalized_packets = [x for x in packets if isinstance(x, dict)]
    normalized_packets.sort(key=_offline_replay_sort_key)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, packet in enumerate(normalized_packets, start=1):
        offline_packet_id = _to_text(packet.get("offline_packet_id") or "").strip()
        if not offline_packet_id:
            offline_packet_id = hashlib.sha256(
                json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()

        packet_type = _to_text(packet.get("packet_type") or packet.get("type") or "triprole.execute").strip().lower()
        executor_uri = _to_text(packet.get("executor_uri") or default_executor_uri).strip() or default_executor_uri
        executor_did = _to_text(packet.get("executor_did") or "").strip()
        executor_role = _to_text(packet.get("executor_role") or default_executor_role).strip() or default_executor_role
        geo_location = _as_dict(packet.get("geo_location"))
        server_timestamp_proof = _as_dict(packet.get("server_timestamp_proof"))

        try:
            if packet_type in {"variation.apply", "variation", "delta.apply", "variation.apply.delta"}:
                result = apply_variation(
                    sb=sb,
                    boq_item_uri=_to_text(packet.get("boq_item_uri") or "").strip(),
                    delta_amount=float(packet.get("delta_amount")),
                    reason=_to_text(packet.get("reason") or "").strip(),
                    project_uri=_to_text(packet.get("project_uri") or "").strip() or None,
                    executor_uri=executor_uri,
                    executor_did=executor_did,
                    executor_role=executor_role,
                    offline_packet_id=offline_packet_id,
                    metadata=_as_dict(packet.get("metadata")),
                    credentials_vc=[_as_dict(x) for x in _as_list(packet.get("credentials_vc"))],
                    geo_location=geo_location,
                    server_timestamp_proof=server_timestamp_proof,
                )
            else:
                result = execute_triprole_action(
                    sb=sb,
                    body={
                        "action": _to_text(packet.get("action") or "").strip(),
                        "input_proof_id": _to_text(packet.get("input_proof_id") or "").strip(),
                        "executor_uri": executor_uri,
                        "executor_did": executor_did,
                        "executor_role": executor_role,
                        "result": _to_text(packet.get("result") or "").strip() or None,
                        "segment_uri": _to_text(packet.get("segment_uri") or "").strip() or None,
                        "boq_item_uri": _to_text(packet.get("boq_item_uri") or "").strip() or None,
                        "signatures": _as_list(packet.get("signatures")),
                        "consensus_signatures": _as_list(packet.get("consensus_signatures")),
                        "signer_metadata": _as_dict(packet.get("signer_metadata")),
                        "payload": _as_dict(packet.get("payload")),
                        "credentials_vc": [_as_dict(x) for x in _as_list(packet.get("credentials_vc"))],
                        "geo_location": geo_location,
                        "server_timestamp_proof": server_timestamp_proof,
                        "offline_packet_id": offline_packet_id,
                    },
                )

            results.append(
                {
                    "offline_packet_id": offline_packet_id,
                    "packet_index": idx,
                    "packet_type": packet_type,
                    "ok": True,
                    "result": result,
                }
            )
        except HTTPException as exc:
            errors.append(
                {
                    "offline_packet_id": offline_packet_id,
                    "packet_index": idx,
                    "packet_type": packet_type,
                    "status_code": exc.status_code,
                    "detail": _to_text(exc.detail).strip(),
                }
            )
            if stop_on_error:
                break
        except Exception as exc:  # pragma: no cover
            errors.append(
                {
                    "offline_packet_id": offline_packet_id,
                    "packet_index": idx,
                    "packet_type": packet_type,
                    "status_code": 500,
                    "detail": _to_text(exc).strip() or "offline replay failed",
                }
            )
            if stop_on_error:
                break

    return {
        "ok": len(errors) == 0,
        "replayed_count": len(results),
        "error_count": len(errors),
        "stop_on_error": bool(stop_on_error),
        "results": results,
        "errors": errors,
    }


def scan_to_confirm_signature(
    *,
    sb: Any,
    input_proof_id: str,
    scan_payload: Any,
    scanner_did: str,
    scanner_role: str,
    executor_uri: str = "v://executor/system/",
    executor_role: str = "SUPERVISOR",
    signature_hash: str = "",
    signer_metadata: dict[str, Any] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proof_id = _to_text(input_proof_id).strip()
    if not proof_id:
        raise HTTPException(400, "input_proof_id is required")
    normalized_scanner_did = _to_text(scanner_did).strip()
    if not normalized_scanner_did.startswith("did:"):
        raise HTTPException(400, "scanner_did must start with did:")
    normalized_scanner_role = _normalize_role(scanner_role) or _to_text(scanner_role).strip().lower()
    if not normalized_scanner_role:
        raise HTTPException(400, "scanner_role is required")

    payload = _validate_scan_confirm_payload(scan_payload)
    if _to_text(payload.get("proof_id") or "").strip() != proof_id:
        raise HTTPException(409, "scan payload proof_id mismatch")

    engine = ProofUTXOEngine(sb)
    input_row = engine.get_by_id(proof_id)
    if not input_row:
        raise HTTPException(404, "input proof_utxo not found")
    if bool(input_row.get("spent")):
        raise HTTPException(409, "input_proof already spent")

    now_iso = _utc_iso()
    anchor = _build_spatiotemporal_anchor(
        action="scan.confirm",
        input_proof_id=proof_id,
        executor_uri=executor_uri,
        now_iso=now_iso,
        geo_location_raw=geo_location,
        server_timestamp_raw=server_timestamp_proof,
    )

    input_sd = _as_dict(input_row.get("state_data"))
    signatures = _normalize_consensus_signatures(_as_list(_as_dict(input_sd.get("consensus")).get("signatures")))
    if not signatures:
        signatures = _normalize_consensus_signatures(input_sd.get("signatures"))

    if not _looks_like_sig_hash(signature_hash):
        signature_hash = hashlib.sha256(
            f"{proof_id}|{normalized_scanner_did}|{normalized_scanner_role}|{payload.get('token_hash')}|{now_iso}".encode(
                "utf-8"
            )
        ).hexdigest()

    by_role: dict[str, dict[str, Any]] = {}
    for sig in signatures:
        role = _normalize_role(sig.get("role"))
        if role:
            by_role[role] = sig
    by_role[normalized_scanner_role] = {
        "role": normalized_scanner_role,
        "did": normalized_scanner_did,
        "signature_hash": signature_hash,
        "signed_at": now_iso,
        "mode": "scan_confirm",
    }
    next_signatures = [by_role[r] for r in sorted(by_role.keys())]
    consensus_check = _validate_consensus_signatures(next_signatures)

    scan_record = {
        "scan_at": now_iso,
        "input_proof_id": proof_id,
        "scanner_role": normalized_scanner_role,
        "scanner_did": normalized_scanner_did,
        "scanned_signer_role": _to_text(payload.get("signer_role") or "").strip(),
        "scanned_signer_did": _to_text(payload.get("signer_did") or "").strip(),
        "token_hash": _to_text(payload.get("token_hash") or "").strip(),
        "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
    }
    scan_history = _as_list(input_sd.get("scan_confirmations"))
    scan_history.append(scan_record)
    if len(scan_history) > 50:
        scan_history = scan_history[-50:]
    normalized_signer_metadata = _normalize_signer_metadata(signer_metadata or {})

    next_state = dict(input_sd)
    next_state.update(
        {
            "trip_action": "scan.confirm",
            "trip_executor": _to_text(executor_uri).strip(),
            "trip_executed_at": now_iso,
            "parent_proof_id": proof_id,
            "parent_hash": _to_text(input_row.get("proof_hash") or "").strip(),
            "scan_confirmation": scan_record,
            "scan_confirmations": scan_history,
            "consensus": {
                "required_roles": list(CONSENSUS_REQUIRED_ROLES),
                "signatures": next_signatures,
                "consensus_hash": _to_text(consensus_check.get("consensus_hash") or ""),
                "consensus_complete": bool(consensus_check.get("ok")),
                "missing_roles": consensus_check.get("missing_roles") or [],
                "invalid": consensus_check.get("invalid") or [],
            },
            "signatures": next_signatures,
            **anchor,
        }
    )
    if _as_list(normalized_signer_metadata.get("signers")):
        next_state["signer_metadata"] = normalized_signer_metadata

    tx = engine.consume(
        input_proof_ids=[proof_id],
        output_states=[
            {
                "owner_uri": _to_text(input_row.get("owner_uri") or executor_uri).strip(),
                "project_id": input_row.get("project_id"),
                "project_uri": _to_text(input_row.get("project_uri") or "").strip(),
                "segment_uri": _to_text(input_row.get("segment_uri") or "").strip(),
                "proof_type": _to_text(input_row.get("proof_type") or "approval").strip() or "approval",
                "result": _normalize_result(_to_text(input_row.get("result") or "PENDING")),
                "state_data": next_state,
                "conditions": _as_list(input_row.get("conditions")),
                "parent_proof_id": proof_id,
                "norm_uri": _to_text(input_row.get("norm_uri") or input_sd.get("norm_uri") or None) or None,
            }
        ],
        executor_uri=_to_text(executor_uri).strip() or "v://executor/system/",
        executor_role=_to_text(executor_role).strip() or "SUPERVISOR",
        trigger_action="TripRole.scan_confirm",
        trigger_data={
            "input_proof_id": proof_id,
            "scanner_role": normalized_scanner_role,
            "scanner_did": normalized_scanner_did,
            "scanned_signer_role": _to_text(payload.get("signer_role") or "").strip(),
            "scanned_signer_did": _to_text(payload.get("signer_did") or "").strip(),
            "scan_token_hash": _to_text(payload.get("token_hash") or "").strip(),
            "biometric_metadata_hash": _to_text(normalized_signer_metadata.get("metadata_hash") or "").strip(),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
        },
        tx_type="consume",
    )

    output_ids = [_to_text(x).strip() for x in _as_list(tx.get("output_proofs")) if _to_text(x).strip()]
    output_id = output_ids[0] if output_ids else ""
    output_row = engine.get_by_id(output_id) if output_id else None
    credit_endorsement: dict[str, Any] = {}
    mirror_sync: dict[str, Any] = {}
    if isinstance(output_row, dict):
        try:
            credit_endorsement = calculate_sovereign_credit(
                sb=sb,
                project_uri=_to_text(output_row.get("project_uri") or "").strip(),
                participant_did=normalized_scanner_did,
            )
        except Exception:
            credit_endorsement = {}
        try:
            mirror_sync = sync_to_mirrors(
                proof_packet=_build_shadow_packet(
                    output_row=output_row,
                    tx=tx,
                    action="scan.confirm",
                    did_gate={
                        "ok": True,
                        "user_did": normalized_scanner_did,
                        "required_credential": "scan_confirm_signatory",
                        "source": "scan_confirm",
                    },
                    credit_endorsement=credit_endorsement,
                ),
                sb=sb,
                project_id=_to_text(output_row.get("project_id") or "").strip(),
                project_uri=_to_text(output_row.get("project_uri") or "").strip(),
            )
        except Exception:
            mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}
        patched_state = _patch_state_data_fields(
            sb=sb,
            proof_id=output_id,
            patch={
                "credit_endorsement": credit_endorsement,
                "shadow_mirror_sync": mirror_sync,
            },
        )
        output_row["state_data"] = patched_state
    return {
        "ok": True,
        "input_proof_id": proof_id,
        "output_proof_id": output_id,
        "proof_hash": _to_text((output_row or {}).get("proof_hash") or "").strip(),
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "consensus_complete": bool(consensus_check.get("ok")),
        "missing_roles": consensus_check.get("missing_roles") or [],
        "invalid": consensus_check.get("invalid") or [],
        "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
        "tx": tx,
    }


def _compute_docfinal_risk_audit(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    chain_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(chain_rows)
    issues: list[dict[str, Any]] = []
    did_reputation: dict[str, Any] = {}

    dual_gate: dict[str, Any] = {}
    try:
        dual_gate = resolve_dual_pass_gate(
            sb=sb,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
            rows=chain_rows,
        )
    except Exception as exc:
        dual_gate = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    if not bool(dual_gate.get("ok")):
        issues.append({"severity": "high", "issue": "dual_pass_gate_missing"})

    by_id: dict[str, dict[str, Any]] = {}
    for row in chain_rows:
        pid = _to_text(row.get("proof_id") or "").strip()
        if pid:
            by_id[pid] = row

    stage_rank = {
        "INITIAL": 0,
        "GENESIS": 0,
        "ENTRY": 1,
        "INSPECTION": 1,
        "INSTALLATION": 2,
        "VARIATION": 2,
        "SETTLEMENT": 3,
    }
    max_seen_rank = -1
    stage_conflicts = 0
    for row in chain_rows:
        sd = _as_dict(row.get("state_data"))
        stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
        rank = stage_rank.get(stage, None)
        if rank is None:
            continue
        if rank < max_seen_rank:
            stage_conflicts += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "stage_order_conflict",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "stage": stage,
                    "max_seen_stage_rank": max_seen_rank,
                }
            )
        max_seen_rank = max(max_seen_rank, rank)

    timestamp_conflicts = 0
    for row in chain_rows:
        parent_id = _to_text(row.get("parent_proof_id") or "").strip()
        if not parent_id:
            continue
        parent = by_id.get(parent_id)
        if not parent:
            continue
        child_ms = _parse_iso_epoch_ms(row.get("created_at"))
        parent_ms = _parse_iso_epoch_ms(parent.get("created_at"))
        if child_ms is None or parent_ms is None:
            continue
        if child_ms < parent_ms:
            timestamp_conflicts += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "timestamp_conflict",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "parent_proof_id": parent_id,
                }
            )

    geo_outside = 0
    missing_geo = 0
    missing_ntp = 0
    for row in chain_rows:
        sd = _as_dict(row.get("state_data"))
        geo = _as_dict(sd.get("geo_compliance"))
        trust = _to_text(geo.get("trust_level") or sd.get("trust_level") or "").strip().upper()
        if trust in {"LOW", "OUTSIDE"}:
            geo_outside += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "geo_outside_boundary",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "trust_level": trust,
                }
            )
        geo_loc = _as_dict(sd.get("geo_location"))
        if not geo_loc or _to_float(geo_loc.get("lat")) is None or _to_float(geo_loc.get("lng")) is None:
            missing_geo += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "missing_geo_location",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                }
            )
        ntp = _as_dict(sd.get("server_timestamp_proof"))
        if not ntp or not _to_text(ntp.get("ntp_server") or ntp.get("proof_hash") or "").strip():
            missing_ntp += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "missing_ntp_proof",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                }
            )

    risk_score = 100.0
    if not bool(dual_gate.get("ok")):
        risk_score -= 40.0
    if timestamp_conflicts > 0:
        risk_score -= min(30.0, 30.0 * (timestamp_conflicts / max(1, total)))
    if stage_conflicts > 0:
        risk_score -= min(20.0, 20.0 * (stage_conflicts / max(1, total)))
    if missing_geo > 0:
        risk_score -= min(20.0, 20.0 * (missing_geo / max(1, total)))
    if missing_ntp > 0:
        risk_score -= min(20.0, 20.0 * (missing_ntp / max(1, total)))
    if geo_outside > 0:
        risk_score -= min(30.0, 30.0 * (geo_outside / max(1, total)))
    try:
        did_reputation = build_did_reputation_summary(
            sb=sb,
            project_uri=project_uri,
            chain_rows=chain_rows,
            window_days=90,
        )
    except Exception:
        did_reputation = {}
    if _as_dict(did_reputation).get("available"):
        rep_penalty = _to_float(_as_dict(did_reputation).get("risk_penalty")) or 0.0
        if rep_penalty > 0:
            risk_score -= min(25.0, rep_penalty)
        for item in _as_list(did_reputation.get("high_risk_dids")):
            r = _as_dict(item)
            issues.append(
                {
                    "severity": "medium",
                    "issue": "did_reputation_low",
                    "participant_did": _to_text(r.get("participant_did") or "").strip(),
                    "identity_uri": _to_text(r.get("identity_uri") or "").strip(),
                    "score": _to_float(r.get("score")),
                }
            )
    risk_score = max(0.0, min(100.0, round(risk_score, 2)))

    return {
        "ok": True,
        "total": total,
        "risk_score": risk_score,
        "timestamp_conflicts": timestamp_conflicts,
        "stage_conflicts": stage_conflicts,
        "geo_outside_count": geo_outside,
        "missing_geo": missing_geo,
        "missing_ntp": missing_ntp,
        "dual_gate": dual_gate,
        "did_reputation": did_reputation,
        "sampling_multiplier": _to_float(_as_dict(did_reputation).get("sampling_multiplier")) or 1.0,
        "issues": issues[:500],
    }


def build_docfinal_package_for_boq(
    *,
    boq_item_uri: str,
    sb: Any,
    project_meta: dict[str, Any] | None = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: str | Path | None = None,
    apply_asset_transfer: bool = False,
    transfer_amount: float | None = None,
    transfer_executor_uri: str = "v://executor/system/",
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
) -> dict[str, Any]:
    normalized_uri = _to_text(boq_item_uri).strip()
    if not normalized_uri:
        raise HTTPException(400, "boq_item_uri is required")

    chain = get_proof_chain(normalized_uri, sb)
    if not chain:
        raise HTTPException(404, "no proof chain found for boq_item_uri")

    scoped_project_uri = _to_text((project_meta or {}).get("project_uri") or "").strip()
    if scoped_project_uri:
        scoped_chain = [row for row in chain if _to_text((row or {}).get("project_uri") or "").strip() == scoped_project_uri]
        if scoped_chain:
            chain = scoped_chain

    latest = chain[-1]
    latest_sd = _as_dict(latest.get("state_data"))

    meta = dict(project_meta or {})
    if not _to_text(meta.get("project_uri") or "").strip():
        meta["project_uri"] = _to_text(latest.get("project_uri") or "").strip()

    project_id = _to_text(latest.get("project_id") or "").strip()
    if not _to_text(meta.get("project_name") or meta.get("name") or "").strip() and project_id:
        meta["project_name"] = get_project_name_by_id(sb, project_id, default="-")

    if not _to_text(meta.get("artifact_uri") or "").strip():
        project_uri = _to_text(meta.get("project_uri") or "").strip().rstrip("/")
        pid = _to_text(latest.get("proof_id") or "").strip()
        meta["artifact_uri"] = (
            _to_text(latest_sd.get("artifact_uri") or "").strip()
            or (f"{project_uri}/artifact/{pid}" if project_uri and pid else "")
        )

    if not _to_text(meta.get("gitpeg_anchor") or "").strip():
        meta["gitpeg_anchor"] = _to_text(latest.get("gitpeg_anchor") or "").strip()

    context = build_rebar_report_context(
        boq_item_uri=normalized_uri,
        chain_rows=chain,
        project_meta=meta,
        verify_base_url=verify_base_url,
    )
    context["timeline_rows"] = _as_list(context.get("timeline"))
    context["record_rows"] = _as_list(context.get("records"))

    risk_audit = _compute_docfinal_risk_audit(
        sb=sb,
        project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
        boq_item_uri=normalized_uri,
        chain_rows=chain,
    )
    if risk_audit:
        risk_audit["total_proof_hash"] = _to_text(
            context.get("total_proof_hash") or context.get("chain_root_hash") or ""
        ).strip()
        context["risk_audit"] = risk_audit
        context["risk_score"] = risk_audit.get("risk_score")
        context["risk_issue_count"] = len(risk_audit.get("issues") or [])

    status_snapshot = get_boq_realtime_status(
        sb=sb,
        project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
        limit=10000,
    )
    hierarchy_summary = _build_recursive_hierarchy_summary(
        items=_as_list(status_snapshot.get("items")),
        focus_item_no=_to_text(latest_sd.get("item_no") or "").strip(),
    )
    hierarchy_rows_all = _as_list(hierarchy_summary.get("rows"))
    hierarchy_filtered = _apply_hierarchy_asset_filter(
        rows=hierarchy_rows_all,
        focus_item_no=_to_text(latest_sd.get("item_no") or "").strip(),
        anchor_code=aggregate_anchor_code,
        direction=aggregate_direction,
        level=aggregate_level,
    )
    context["hierarchy_summary_rows_all"] = hierarchy_rows_all
    context["hierarchy_summary_rows"] = _as_list(hierarchy_filtered.get("rows"))
    context["hierarchy_root_hash"] = _to_text(hierarchy_summary.get("root_hash") or "").strip()
    context["hierarchy_filtered_root_hash"] = _to_text(hierarchy_filtered.get("filtered_root_hash") or "").strip()
    context["hierarchy_root_codes"] = _as_list(hierarchy_summary.get("root_codes"))
    context["chapter_progress"] = _as_dict(hierarchy_summary.get("chapter_progress"))
    context["chapter_progress_percent"] = _as_dict(hierarchy_summary.get("chapter_progress")).get("progress_percent")
    context["hierarchy_filter"] = _as_dict(hierarchy_filtered.get("filter"))

    credit_endorsement = _as_dict(latest_sd.get("credit_endorsement"))
    if not credit_endorsement:
        latest_did_gate = _as_dict(latest_sd.get("did_gate"))
        participant_did = _to_text(
            latest_did_gate.get("user_did")
            or latest_sd.get("executor_did")
            or latest_sd.get("operator_did")
            or ""
        ).strip()
        if participant_did.startswith("did:"):
            try:
                credit_endorsement = calculate_sovereign_credit(
                    sb=sb,
                    project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
                    participant_did=participant_did,
                )
            except Exception:
                credit_endorsement = {}
    if credit_endorsement:
        context["credit_endorsement"] = credit_endorsement
        context["credit_score"] = credit_endorsement.get("score")
        context["credit_grade"] = credit_endorsement.get("grade")
        context["credit_fast_track_eligible"] = bool(credit_endorsement.get("fast_track_eligible"))
        context["credit_sample_count"] = _as_dict(credit_endorsement.get("stats")).get("sample_count")

    sensor_hardware = _as_dict(latest_sd.get("sensor_hardware"))
    if not sensor_hardware:
        sensor_hardware = _as_dict(_as_dict(latest_sd.get("measurement")).get("sensor_hardware"))
    if sensor_hardware:
        context["sensor_hardware"] = sensor_hardware
        context["sensor_device_sn"] = _to_text(sensor_hardware.get("device_sn") or "").strip()
        context["sensor_calibration_valid_until"] = _to_text(sensor_hardware.get("calibration_valid_until") or "").strip()
        context["sensor_calibration_valid"] = bool(sensor_hardware.get("calibration_valid"))

    geo_compliance = _as_dict(latest_sd.get("geo_compliance"))
    if geo_compliance:
        context["geo_compliance"] = geo_compliance
        context["trust_level"] = _to_text(
            geo_compliance.get("trust_level")
            or latest_sd.get("trust_level")
            or ""
        ).strip()
        context["geo_fence_warning"] = _to_text(
            geo_compliance.get("warning")
            or latest_sd.get("geo_fence_warning")
            or ""
        ).strip()

    biometric_verification = _as_dict(latest_sd.get("biometric_verification"))
    if biometric_verification:
        context["biometric_verification"] = biometric_verification
        context["biometric_ok"] = bool(biometric_verification.get("ok"))
        context["biometric_verified_count"] = biometric_verification.get("verified_count")
        context["biometric_required_count"] = biometric_verification.get("required_count")
    signer_metadata = _as_dict(latest_sd.get("signer_metadata"))
    signer_list = _as_list(signer_metadata.get("signers"))
    if signer_list:
        context["signer_metadata"] = signer_metadata
        context["biometric_signer_count"] = len(signer_list)

    lineage_snapshot: dict[str, Any] | None = None
    asset_origin: dict[str, Any] | None = None
    latest_proof_id = _to_text(latest.get("proof_id") or "").strip()
    if latest_proof_id:
        try:
            lineage_snapshot = get_full_lineage(latest_proof_id, sb)
            context["lineage_total_hash"] = _to_text(lineage_snapshot.get("total_proof_hash") or "").strip()
            context["lineage_norm_ref_count"] = len(_as_list(lineage_snapshot.get("norm_refs")))
            context["lineage_evidence_hash_count"] = len(_as_list(lineage_snapshot.get("evidence_hashes")))
        except Exception:
            lineage_snapshot = None
        try:
            asset_origin = trace_asset_origin(
                sb=sb,
                utxo_id=latest_proof_id,
                boq_item_uri=normalized_uri,
                project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
            )
            context["asset_origin"] = asset_origin
            context["asset_origin_statement"] = _to_text(asset_origin.get("statement") or "").strip()
        except Exception:
            asset_origin = None

    total_proof_hash = _to_text(context.get("total_proof_hash") or context.get("chain_root_hash") or "").strip()
    if total_proof_hash:
        sealing_trip = build_sealing_trip(
            total_proof_hash=total_proof_hash,
            project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
            boq_item_uri=normalized_uri,
            smu_id=_smu_id_from_item_no(_to_text(latest_sd.get("item_no") or _item_no_from_boq_uri(normalized_uri)).strip()),
        )
        context["sealing_trip"] = sealing_trip
        context["sealing_pattern_id"] = _to_text(sealing_trip.get("pattern_id") or "").strip()
        context["sealing_margin_microtext"] = _as_list(sealing_trip.get("margin_microtext"))
        context["sealing_scan_hint"] = _to_text(sealing_trip.get("scan_hint") or "").strip()

    transfer_receipt: dict[str, Any] | None = None
    if apply_asset_transfer:
        resolved_amount = _to_float(transfer_amount)
        if resolved_amount is None or resolved_amount <= 0:
            resolved_amount = _extract_settled_quantity(latest, fallback_design=None)
        if resolved_amount is not None and resolved_amount > 0:
            try:
                transfer_receipt = transfer_asset(
                    sb=sb,
                    item_id=normalized_uri,
                    amount=float(resolved_amount),
                    executor_uri=transfer_executor_uri,
                    executor_role="DOCPEG",
                    docpeg_proof_id=_to_text(latest.get("proof_id") or "").strip(),
                    docpeg_hash=_to_text(latest.get("proof_hash") or "").strip(),
                    project_uri=_to_text(latest.get("project_uri") or "").strip(),
                    metadata={
                        "source": "docpeg_package",
                        "boq_item_uri": normalized_uri,
                        "verify_uri": _to_text(context.get("verify_uri") or "").strip(),
                    },
                )
            except Exception as exc:
                transfer_receipt = {
                    "ok": False,
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "item_id": normalized_uri,
                    "amount": float(resolved_amount),
                }
        else:
            transfer_receipt = {
                "ok": False,
                "error": "no_valid_transfer_amount",
                "item_id": normalized_uri,
                "amount": resolved_amount,
            }

    if not _to_text(context.get("artifact_uri") or "").strip():
        context["artifact_uri"] = _to_text(meta.get("artifact_uri") or "").strip()
    if not _to_text(context.get("gitpeg_anchor") or "").strip():
        context["gitpeg_anchor"] = _to_text(meta.get("gitpeg_anchor") or "").strip()
    if transfer_receipt is not None:
        context["asset_transfer"] = transfer_receipt

    resolved_template = Path(template_path).expanduser().resolve() if template_path else (
        Path(__file__).resolve().parent / "templates" / "rebar_inspection_table.docx"
    )

    docx_bytes = render_rebar_inspection_docx(template_path=resolved_template, context=context)
    pdf_bytes = render_rebar_inspection_pdf(docx_bytes=docx_bytes, context=context)
    evidence_items = None
    try:
        evidence_payload = get_all_evidence_for_item(sb=sb, boq_item_uri=normalized_uri)
        if isinstance(evidence_payload, dict) and isinstance(evidence_payload.get("evidence"), list):
            evidence_items = evidence_payload.get("evidence")
            context["evidence_count"] = len(evidence_items)
            context["evidence_source"] = "boq_chain"
    except Exception:
        evidence_items = None
    zip_bytes = build_dsp_zip_package(
        report_pdf_bytes=pdf_bytes,
        docx_bytes=docx_bytes,
        proof_chain=chain,
        context=context,
        evidence_items=evidence_items,
    )

    file_base = re.sub(r"[^\w\-]+", "_", normalized_uri, flags=re.ASCII)[:120] or "docfinal"
    return {
        "ok": True,
        "boq_item_uri": normalized_uri,
        "context": context,
        "proof_chain": chain,
        "docx_bytes": docx_bytes,
        "pdf_bytes": pdf_bytes,
        "zip_bytes": zip_bytes,
        "filename_base": file_base,
        "asset_transfer": transfer_receipt,
        "full_lineage": lineage_snapshot,
        "asset_origin": asset_origin,
    }


def get_boq_realtime_status(
    *,
    sb: Any,
    project_uri: str,
    limit: int = 2000,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .order("created_at", desc=False)
            .limit(max(1, min(limit, 10000)))
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to load proof_utxo: {exc}") from exc

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_leaf_boq_row(row):
            continue
        boq_item_uri = _boq_item_from_row(row)
        if not boq_item_uri.startswith("v://"):
            continue
        grouped.setdefault(boq_item_uri, []).append(row)

    items: list[dict[str, Any]] = []
    total_design = 0.0
    total_settled = 0.0
    total_consumed = 0.0
    total_approved = 0.0

    for boq_item_uri, bucket in grouped.items():
        bucket.sort(key=lambda r: _to_text(r.get("created_at") or ""))
        genesis_rows = []
        settlement_rows = []
        consume_rows = []
        candidate_rows = []
        for row in bucket:
            sd = _as_dict(row.get("state_data"))
            stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
            ptype = _to_text(row.get("proof_type") or "").strip().lower()
            if stage == "INITIAL" or ptype == "zero_ledger":
                genesis_rows.append(row)
            if stage == "SETTLEMENT" and _to_text(row.get("result") or "").strip().upper() == "PASS":
                settlement_rows.append(row)
            if stage == "INSTALLATION":
                consume_rows.append(row)
            if bool(row.get("spent")) is False and stage in {"INSTALLATION", "VARIATION"}:
                candidate_rows.append(row)

        genesis = genesis_rows[0] if genesis_rows else (bucket[0] if bucket else {})
        gsd = _as_dict(genesis.get("state_data"))
        design_qty = float(_effective_design_quantity(genesis, bucket))
        total_design += design_qty
        unit_price = _to_float(gsd.get("unit_price"))
        contract_qty = _to_float(gsd.get("contract_quantity"))
        if contract_qty is None:
            contract_qty = _to_float(gsd.get("approved_quantity"))
        approved_qty = _to_float(gsd.get("approved_quantity"))
        if approved_qty is not None:
            total_approved += approved_qty
        design_total = _to_float(gsd.get("design_total"))
        if design_total is None and unit_price is not None:
            design_total = float(unit_price) * float(_to_float(gsd.get("design_quantity")) or 0.0)
        contract_total = _to_float(gsd.get("contract_total"))
        if contract_total is None and unit_price is not None:
            contract_total = float(unit_price) * float(contract_qty or 0.0)

        settled_qty = 0.0
        if settlement_rows:
            for row in settlement_rows:
                settled_qty += _extract_settled_quantity(row, fallback_design=None)
            if settled_qty <= 0 and design_qty > 0:
                settled_qty = design_qty
        total_settled += settled_qty

        consumed_qty = 0.0
        if consume_rows:
            for row in consume_rows:
                consumed_qty += _extract_settled_quantity(row, fallback_design=None)
        total_consumed += consumed_qty

        latest_settlement = settlement_rows[-1] if settlement_rows else None
        latest_settlement_id = _to_text((latest_settlement or {}).get("proof_id") or "").strip()

        sign_candidate = candidate_rows[-1] if candidate_rows else None
        sign_ready = False
        sign_block_reason = "no_installation_candidate"
        sign_candidate_id = _to_text((sign_candidate or {}).get("proof_id") or "").strip()
        gate = {}
        if sign_candidate_id:
            try:
                agg = aggregate_provenance_chain(sign_candidate_id, sb)
                gate = _as_dict(agg.get("gate"))
                sign_ready = not bool(gate.get("blocked"))
                sign_block_reason = ""
                if not sign_ready:
                    sign_block_reason = f"gate_locked:{_to_text(gate.get('reason') or '')}"
            except Exception as exc:
                sign_ready = False
                sign_block_reason = f"gate_check_failed:{exc.__class__.__name__}"

        baseline_qty = approved_qty if (approved_qty is not None and approved_qty > 0) else (contract_qty or design_qty)
        progress = 0.0
        if baseline_qty > 1e-9:
            progress = max(0.0, min(1.0, settled_qty / baseline_qty))

        item_no = _item_no_from_boq_uri(boq_item_uri)
        unit_price_val = round(unit_price or 0.0, 4)
        design_total_val = round(design_total or 0.0, 4)
        contract_total_val = round(contract_total or 0.0, 4)
        contract_qty_val = contract_qty if contract_qty is not None else (approved_qty or 0.0)
        items.append(
            {
                "boq_item_uri": boq_item_uri,
                "item_no": item_no,
                "item_name": _to_text(gsd.get("item_name") or ""),
                "unit": _to_text(gsd.get("unit") or ""),
                "design_quantity": round(design_qty, 4),
                "approved_quantity": round(approved_qty or 0.0, 4),
                "contract_quantity": round(contract_qty_val, 4),
                "unit_price": unit_price_val,
                "design_total": design_total_val,
                "contract_total": contract_total_val,
                "settled_quantity": round(settled_qty, 4),
                "consumed_quantity": round(consumed_qty, 4),
                "remaining_quantity": round(max(0.0, design_qty - settled_qty), 4),
                "consumption_rate": round(progress, 6),
                "consumption_percent": round(progress * 100.0, 2),
                "progress_percent": round(progress * 100.0, 2),
                "settlement_count": len(settlement_rows),
                "latest_settlement_proof_id": latest_settlement_id,
                "latest_settlement_at": _to_text((latest_settlement or {}).get("created_at") or ""),
                "proof_chain_view": f"/v1/proof/docfinal/context?boq_item_uri={boq_item_uri}",
                "sign_ready": sign_ready,
                "sign_block_reason": sign_block_reason,
                "sign_candidate_proof_id": sign_candidate_id,
                "gate": gate,
            }
        )

    def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
        code = _to_text(item.get("item_no") or "")
        nums = [int(x) for x in re.findall(r"\d+", code)]
        return (nums[0] if nums else 9999, code)

    items.sort(key=_sort_key)

    project_progress = 0.0
    baseline_total = total_approved if total_approved > 1e-9 else total_design
    if baseline_total > 1e-9:
        project_progress = max(0.0, min(1.0, total_settled / baseline_total))

    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "summary": {
            "boq_item_count": len(items),
            "design_total": round(total_design, 6),
            "approved_total": round(total_approved, 6),
            "settled_total": round(total_settled, 6),
            "consumed_total": round(total_consumed, 6),
            "progress_percent": round(project_progress * 100.0, 2),
        },
        "items": items,
    }


def _boq_item_code_parts(item_no: str) -> list[str]:
    return [seg.strip() for seg in _to_text(item_no).split("-") if seg.strip()]


def _hierarchy_node_type(depth: int, max_depth: int) -> str:
    if depth <= 1:
        return "chapter"
    if depth == 2:
        return "section"
    if depth == 3:
        return "item"
    if depth >= max_depth:
        return "detail"
    return f"level_{depth}"


def _merkle_root_from_hashes(hashes: list[str]) -> str:
    layer = [_to_text(x).strip().lower() for x in hashes if _to_text(x).strip()]
    if not layer:
        return ""
    while len(layer) > 1:
        next_layer: list[str] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            next_layer.append(hashlib.sha256(f"{left}|{right}".encode("utf-8")).hexdigest())
        layer = next_layer
    return layer[0]


def _build_recursive_hierarchy_summary(
    *,
    items: list[dict[str, Any]],
    focus_item_no: str = "",
) -> dict[str, Any]:
    node_map: dict[str, dict[str, Any]] = {}
    children_map: dict[str, set[str]] = {}

    for leaf in items:
        if not isinstance(leaf, dict):
            continue
        item_no = _to_text(leaf.get("item_no") or "").strip()
        if not item_no:
            continue
        parts = _boq_item_code_parts(item_no)
        if not parts:
            continue
        design_qty = float(_to_float(leaf.get("design_quantity")) or 0.0)
        settled_qty = float(_to_float(leaf.get("settled_quantity")) or 0.0)
        item_name = _to_text(leaf.get("item_name") or "").strip()
        unit = _to_text(leaf.get("unit") or "").strip()
        max_depth = len(parts)

        for depth in range(1, max_depth + 1):
            code = "-".join(parts[:depth])
            parent_code = "-".join(parts[: depth - 1]) if depth > 1 else ""
            node = node_map.setdefault(
                code,
                {
                    "code": code,
                    "parent_code": parent_code,
                    "depth": depth,
                    "max_depth": max_depth,
                    "design_quantity": 0.0,
                    "settled_quantity": 0.0,
                    "leaf_count": 0,
                    "item_name": "",
                    "unit": "",
                },
            )
            node["max_depth"] = max(int(node.get("max_depth") or depth), max_depth)
            node["design_quantity"] = float(node.get("design_quantity") or 0.0) + design_qty
            node["settled_quantity"] = float(node.get("settled_quantity") or 0.0) + settled_qty
            node["leaf_count"] = int(node.get("leaf_count") or 0) + 1
            if depth == max_depth:
                node["item_name"] = item_name or _to_text(node.get("item_name") or "").strip()
                node["unit"] = unit or _to_text(node.get("unit") or "").strip()
            if parent_code:
                children_map.setdefault(parent_code, set()).add(code)
            children_map.setdefault(code, set())

    if not node_map:
        return {"rows": [], "root_hash": "", "chapter_progress": {}}

    subtree_hash: dict[str, str] = {}
    child_merkle: dict[str, str] = {}
    def _code_key(raw: str) -> tuple[int, list[int], str]:
        nums = [int(x) if x.isdigit() else 9999 for x in re.findall(r"\d+", raw)]
        return (len(nums), nums, raw)
    for code, node in sorted(
        node_map.items(),
        key=lambda kv: (int(kv[1].get("depth") or 0), kv[0]),
        reverse=True,
    ):
        child_codes = sorted(children_map.get(code) or set(), key=_code_key)
        child_hashes = [subtree_hash.get(c, "") for c in child_codes if subtree_hash.get(c, "")]
        merkle = _merkle_root_from_hashes(child_hashes)
        child_merkle[code] = merkle
        canonical = {
            "code": code,
            "depth": int(node.get("depth") or 0),
            "design_quantity": round(float(node.get("design_quantity") or 0.0), 6),
            "settled_quantity": round(float(node.get("settled_quantity") or 0.0), 6),
            "leaf_count": int(node.get("leaf_count") or 0),
            "children_merkle_root": merkle,
            "node_type": _hierarchy_node_type(int(node.get("depth") or 0), int(node.get("max_depth") or 0)),
        }
        subtree_hash[code] = hashlib.sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    rows: list[dict[str, Any]] = []
    for code, node in sorted(
        node_map.items(),
        key=lambda kv: (int(kv[1].get("depth") or 0), [int(x) if x.isdigit() else 9999 for x in re.findall(r"\d+", kv[0])], kv[0]),
    ):
        depth = int(node.get("depth") or 0)
        design_qty = float(node.get("design_quantity") or 0.0)
        settled_qty = float(node.get("settled_quantity") or 0.0)
        progress = 0.0 if design_qty <= 1e-9 else max(0.0, min(1.0, settled_qty / design_qty))
        rows.append(
            {
                "code": code,
                "depth": depth,
                "parent_code": _to_text(node.get("parent_code") or "").strip(),
                "node_type": _hierarchy_node_type(depth, int(node.get("max_depth") or depth)),
                "is_leaf": len(children_map.get(code) or set()) == 0,
                "item_name": _to_text(node.get("item_name") or "").strip(),
                "unit": _to_text(node.get("unit") or "").strip(),
                "design_quantity": round(design_qty, 6),
                "settled_quantity": round(settled_qty, 6),
                "remaining_quantity": round(max(0.0, design_qty - settled_qty), 6),
                "progress_percent": round(progress * 100.0, 2),
                "leaf_count": int(node.get("leaf_count") or 0),
                "children_count": len(children_map.get(code) or set()),
                "children_merkle_root": child_merkle.get(code, ""),
                "subtree_hash": subtree_hash.get(code, ""),
            }
        )

    root_codes = [row["code"] for row in rows if not _to_text(row.get("parent_code") or "").strip()]
    root_hash = _merkle_root_from_hashes([subtree_hash.get(code, "") for code in root_codes if subtree_hash.get(code, "")])

    focus_chapter = ""
    focus_parts = _boq_item_code_parts(focus_item_no)
    if focus_parts:
        focus_chapter = focus_parts[0]
    chapter_progress = {}
    if focus_chapter:
        chapter_row = next((row for row in rows if row["code"] == focus_chapter), {})
        if chapter_row:
            chapter_progress = {
                "chapter_code": focus_chapter,
                "progress_percent": chapter_row.get("progress_percent"),
                "design_quantity": chapter_row.get("design_quantity"),
                "settled_quantity": chapter_row.get("settled_quantity"),
                "remaining_quantity": chapter_row.get("remaining_quantity"),
                "leaf_count": chapter_row.get("leaf_count"),
            }

    return {
        "rows": rows,
        "root_hash": root_hash,
        "chapter_progress": chapter_progress,
        "root_codes": root_codes,
    }


def _normalize_aggregate_direction(raw: Any) -> str:
    text = _to_text(raw).strip().lower()
    alias = {
        "": "all",
        "all": "all",
        "full": "all",
        "up": "up",
        "ancestor": "up",
        "ancestors": "up",
        "down": "down",
        "descendant": "down",
        "descendants": "down",
        "both": "both",
        "lineage": "both",
    }
    return alias.get(text, "all")


def _normalize_aggregate_level(raw: Any) -> str:
    text = _to_text(raw).strip().lower()
    alias = {
        "": "all",
        "all": "all",
        "chapter": "chapter",
        "section": "section",
        "item": "item",
        "detail": "detail",
        "leaf": "leaf",
        "group": "group",
    }
    return alias.get(text, "all")


def _filtered_hierarchy_root_hash(rows: list[dict[str, Any]]) -> str:
    row_map = {
        _to_text(row.get("code") or "").strip(): row
        for row in rows
        if isinstance(row, dict) and _to_text(row.get("code") or "").strip()
    }
    if not row_map:
        return ""
    codes = set(row_map.keys())
    root_codes = [
        code
        for code, row in row_map.items()
        if not _to_text(row.get("parent_code") or "").strip() or _to_text(row.get("parent_code") or "").strip() not in codes
    ]
    root_hashes = [
        _to_text(row_map.get(code, {}).get("subtree_hash") or "").strip()
        for code in root_codes
        if _to_text(row_map.get(code, {}).get("subtree_hash") or "").strip()
    ]
    return _merkle_root_from_hashes(root_hashes)


def _apply_hierarchy_asset_filter(
    *,
    rows: list[dict[str, Any]],
    focus_item_no: str,
    anchor_code: str = "",
    direction: str = "all",
    level: str = "all",
) -> dict[str, Any]:
    normalized_direction = _normalize_aggregate_direction(direction)
    normalized_level = _normalize_aggregate_level(level)
    normalized_anchor = _to_text(anchor_code).strip() or _to_text(focus_item_no).strip()
    filtered = [row for row in rows if isinstance(row, dict)]

    if normalized_anchor and normalized_direction in {"up", "down", "both"}:
        selected_codes: set[str] = set()
        for row in filtered:
            code = _to_text(row.get("code") or "").strip()
            if not code:
                continue
            if normalized_direction in {"up", "both"}:
                if normalized_anchor == code or normalized_anchor.startswith(f"{code}-"):
                    selected_codes.add(code)
            if normalized_direction in {"down", "both"}:
                if code == normalized_anchor or code.startswith(f"{normalized_anchor}-"):
                    selected_codes.add(code)
        filtered = [row for row in filtered if _to_text(row.get("code") or "").strip() in selected_codes]

    if normalized_level != "all":
        if normalized_level == "leaf":
            filtered = [row for row in filtered if bool(row.get("is_leaf"))]
        elif normalized_level == "group":
            filtered = [row for row in filtered if not bool(row.get("is_leaf"))]
        else:
            filtered = [
                row
                for row in filtered
                if _to_text(row.get("node_type") or "").strip().lower() == normalized_level
            ]

    return {
        "rows": filtered,
        "filter": {
            "anchor_code": normalized_anchor,
            "direction": normalized_direction,
            "level": normalized_level,
            "source_row_count": len(rows),
            "filtered_row_count": len(filtered),
        },
        "filtered_root_hash": _filtered_hierarchy_root_hash(filtered),
    }


def _encrypt_aes256(payload_bytes: bytes, passphrase: str) -> dict[str, Any]:
    key = hashlib.sha256(_to_text(passphrase).encode("utf-8")).digest()
    nonce = os.urandom(12)
    aad = b"QCSpec-Master-DSP-v1"
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, payload_bytes, aad)
    return {
        "algorithm": "AES-256-GCM",
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "aad": aad.decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "cipher_hash": hashlib.sha256(ciphertext).hexdigest(),
    }


def export_doc_final(
    *,
    sb: Any,
    project_uri: str,
    project_name: str | None = None,
    passphrase: str = "",
    verify_base_url: str = "https://verify.qcspec.com",
    include_unsettled: bool = False,
) -> dict[str, Any]:
    status = get_boq_realtime_status(sb=sb, project_uri=project_uri, limit=10000)
    items = _as_list(status.get("items"))
    if include_unsettled:
        target_items = items
    else:
        target_items = [item for item in items if int(item.get("settlement_count") or 0) > 0]

    if not target_items:
        raise HTTPException(404, "no settled boq items found for project")

    master_buf = io.BytesIO()
    file_fingerprints: list[dict[str, Any]] = []
    item_errors: list[dict[str, Any]] = []
    exported_items: list[dict[str, Any]] = []
    lineage_snapshots: list[dict[str, Any]] = []

    with zipfile.ZipFile(master_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as master_zip:
        for item in target_items:
            boq_item_uri = _to_text(item.get("boq_item_uri") or "").strip()
            if not boq_item_uri:
                continue
            item_no = _to_text(item.get("item_no") or _item_no_from_boq_uri(boq_item_uri) or "unknown").strip()
            smu_id = _smu_id_from_item_no(item_no)
            base_dir = f"smu_archive/{smu_id}/{item_no or 'unknown'}"
            try:
                package = build_docfinal_package_for_boq(
                    boq_item_uri=boq_item_uri,
                    sb=sb,
                    project_meta={
                        "project_name": project_name or "",
                        "project_uri": project_uri,
                    },
                    verify_base_url=verify_base_url,
                    apply_asset_transfer=True,
                )
                package_zip = package.get("zip_bytes") or b""
                if not package_zip:
                    raise RuntimeError("empty docfinal package")

                with zipfile.ZipFile(io.BytesIO(package_zip), mode="r") as item_zip:
                    item_file_count = 0
                    for name in item_zip.namelist():
                        blob = item_zip.read(name)
                        target_name = f"{base_dir}/{name}"
                        master_zip.writestr(target_name, blob)
                        item_file_count += 1
                        file_fingerprints.append(
                            {
                                "path": target_name,
                                "sha256": hashlib.sha256(blob).hexdigest(),
                                "size": len(blob),
                            }
                        )

                exported_items.append(
                    {
                        "boq_item_uri": boq_item_uri,
                        "item_no": item_no,
                        "smu_id": smu_id,
                        "base_dir": base_dir,
                        "latest_settlement_proof_id": _to_text(item.get("latest_settlement_proof_id") or ""),
                        "file_count": item_file_count,
                        "asset_transfer": package.get("asset_transfer"),
                    }
                )

                lineage_proof_id = _to_text(item.get("latest_settlement_proof_id") or "").strip()
                if lineage_proof_id:
                    try:
                        lineage = get_full_lineage(lineage_proof_id, sb)
                        lineage_snapshots.append(
                            {
                                "boq_item_uri": boq_item_uri,
                                "item_no": item_no,
                                "proof_id": lineage_proof_id,
                                "total_proof_hash": _to_text(lineage.get("total_proof_hash") or "").strip(),
                                "norm_refs": lineage.get("norm_refs") or [],
                                "evidence_hashes": lineage.get("evidence_hashes") or [],
                                "qc_conclusions": lineage.get("qc_conclusions") or [],
                                "consensus_signatures": lineage.get("consensus_signatures") or [],
                            }
                        )
                    except Exception:
                        lineage_snapshots.append(
                            {
                                "boq_item_uri": boq_item_uri,
                                "item_no": item_no,
                                "proof_id": lineage_proof_id,
                                "error": "lineage_snapshot_failed",
                            }
                        )
            except Exception as exc:
                item_errors.append(
                    {
                        "boq_item_uri": boq_item_uri,
                        "item_no": item_no,
                        "error": f"{exc.__class__.__name__}: {exc}",
                    }
                )

        archive_volumes: list[dict[str, Any]] = []
        page_cursor = 1
        by_smu: dict[str, list[dict[str, Any]]] = {}
        for item in exported_items:
            smu_id = _to_text(item.get("smu_id") or "").strip() or _smu_id_from_item_no(
                _to_text(item.get("item_no") or "").strip()
            )
            by_smu.setdefault(smu_id, []).append(item)
        volume_no = 1
        for smu_id in sorted(by_smu.keys()):
            smu_items = sorted(
                by_smu.get(smu_id) or [],
                key=lambda row: _to_text(_as_dict(row).get("item_no") or "").strip(),
            )
            est_pages = 0
            entries: list[dict[str, Any]] = []
            for item in smu_items:
                item_pages = max(1, int(item.get("file_count") or 1) * 2)
                start_page = page_cursor
                end_page = page_cursor + item_pages - 1
                page_cursor = end_page + 1
                est_pages += item_pages
                entries.append(
                    {
                        "item_no": _to_text(item.get("item_no") or "").strip(),
                        "boq_item_uri": _to_text(item.get("boq_item_uri") or "").strip(),
                        "smu_id": smu_id,
                        "start_page": start_page,
                        "end_page": end_page,
                    }
                )
            archive_volumes.append(
                {
                    "volume_no": volume_no,
                    "title": f"JTG Archive Volume {volume_no} (SMU {smu_id})",
                    "smu_id": smu_id,
                    "chapter": smu_id,
                    "archive_scope": "smu",
                    "estimated_pages": est_pages,
                    "entries": entries,
                }
            )
            volume_no += 1

        index_payload = {
            "generated_at": _utc_iso(),
            "project_uri": _to_text(project_uri),
            "project_name": _to_text(project_name or ""),
            "items": exported_items,
            "archive_volumes": archive_volumes,
            "lineage_snapshots": lineage_snapshots,
            "errors": item_errors,
            "fingerprints": file_fingerprints,
        }
        index_json = json.dumps(index_payload, ensure_ascii=False, indent=2, sort_keys=True, default=str).encode("utf-8")
        master_zip.writestr("index.json", index_json)
        master_zip.writestr(
            "jtg_archive/catalog.json",
            json.dumps(archive_volumes, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        )
        for vol in archive_volumes:
            cover = (
                f"JTG Archive Cover\n"
                f"Project: {_to_text(project_name or '')}\n"
                f"Project URI: {_to_text(project_uri)}\n"
                f"Volume No: {vol.get('volume_no')}\n"
                f"Title: {_to_text(vol.get('title') or '')}\n"
                f"Estimated Pages: {int(vol.get('estimated_pages') or 0)}\n"
            )
            master_zip.writestr(
                f"jtg_archive/volume_{int(vol.get('volume_no') or 0):02d}_cover.txt",
                cover,
            )
            toc_lines = [
                "SMU Archive Catalog",
                f"SMU ID: {_to_text(vol.get('smu_id') or '').strip()}",
                f"Volume No: {int(vol.get('volume_no') or 0)}",
                f"Estimated Pages: {int(vol.get('estimated_pages') or 0)}",
                "",
                "Entries:",
            ]
            for entry in _as_list(vol.get("entries")):
                toc_lines.append(
                    f"- {_to_text(_as_dict(entry).get('item_no') or '').strip()}: "
                    f"p.{int(_as_dict(entry).get('start_page') or 0)}-"
                    f"{int(_as_dict(entry).get('end_page') or 0)}"
                )
            master_zip.writestr(
                f"jtg_archive/volume_{int(vol.get('volume_no') or 0):02d}_toc.txt",
                "\n".join(toc_lines),
            )

    master_bytes = master_buf.getvalue()
    if not master_bytes:
        raise HTTPException(500, "master docfinal package generation failed")

    root_hash = hashlib.sha256(master_bytes).hexdigest()
    encrypted = _encrypt_aes256(master_bytes, passphrase or root_hash)

    engine = ProofUTXOEngine(sb)
    proof_id = f"GP-DOCFINAL-{root_hash[:16].upper()}"
    owner_uri = f"{_to_text(project_uri).rstrip('/')}/executor/system/"
    birth_state = {
        "artifact_type": "docfinal_master_dsp",
        "project_uri": _to_text(project_uri),
        "project_name": _to_text(project_name or ""),
        "root_hash": root_hash,
        "encryption": {
            "algorithm": encrypted.get("algorithm"),
            "cipher_hash": encrypted.get("cipher_hash"),
        },
        "item_count": len(exported_items),
        "error_count": len(item_errors),
        "generated_at": _utc_iso(),
    }
    birth_row = engine.create(
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_uri=_to_text(project_uri),
        project_id=None,
        proof_type="archive",
        result="PASS",
        state_data=birth_state,
        conditions=[],
        parent_proof_id=None,
        norm_uri="v://norm/CoordOS/DocFinal/1.0#master_dsp",
        segment_uri=f"{_to_text(project_uri).rstrip('/')}/docfinal/master",
        signer_uri=owner_uri,
        signer_role="SYSTEM",
    )

    certificate = {
        "proof_id": _to_text(birth_row.get("proof_id") or ""),
        "proof_hash": _to_text(birth_row.get("proof_hash") or ""),
        "gitpeg_anchor": _to_text(birth_row.get("gitpeg_anchor") or ""),
        "project_uri": _to_text(project_uri),
        "root_hash": root_hash,
        "artifact_uri": f"{_to_text(project_uri).rstrip('/')}/docfinal/master/{root_hash[:16]}",
    }

    encrypted_blob = json.dumps(
        {
            "meta": {
                "format": "QCSpec-Master-DSP-Encrypted",
                "version": "1.0",
                "project_uri": _to_text(project_uri),
                "project_name": _to_text(project_name or ""),
                "root_hash": root_hash,
            },
            "encryption": encrypted,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    return {
        "ok": True,
        "project_uri": _to_text(project_uri),
        "root_hash": root_hash,
        "birth_certificate": certificate,
        "items_exported": exported_items,
        "errors": item_errors,
        "encrypted_bytes": encrypted_blob,
        "filename": f"MASTER-DSP-{root_hash[:16]}.qcdsp",
        "status_summary": status.get("summary") or {},
    }
