"""
AR anchoring overlay helpers.
services/api/ar_anchor_service.py
"""

from __future__ import annotations

import math
from typing import Any


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_ar_anchor_overlay(
    *,
    sb: Any,
    project_uri: str,
    lat: float,
    lng: float,
    radius_m: float = 80.0,
    limit: int = 50,
) -> dict[str, Any]:
    rows = (
        sb.table("proof_utxo")
        .select("proof_id,proof_hash,project_uri,segment_uri,proof_type,result,state_data,created_at")
        .eq("project_uri", project_uri)
        .order("created_at", desc=True)
        .limit(5000)
        .execute()
        .data
        or []
    )

    hits: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        geo = _as_dict(sd.get("geo_location"))
        glat = _to_float(geo.get("lat"))
        glng = _to_float(geo.get("lng"))
        if glat is None or glng is None:
            continue
        dist = _haversine_m(lat, lng, glat, glng)
        if dist > radius_m:
            continue
        boq_item_uri = _to_text(sd.get("boq_item_uri") or row.get("segment_uri") or "").strip()
        if not boq_item_uri:
            continue
        if boq_item_uri in hits:
            continue
        hits[boq_item_uri] = {
            "boq_item_uri": boq_item_uri,
            "proof_id": _to_text(row.get("proof_id") or "").strip(),
            "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
            "result": _to_text(row.get("result") or "").strip(),
            "proof_type": _to_text(row.get("proof_type") or "").strip(),
            "trip_action": _to_text(sd.get("trip_action") or "").strip(),
            "lifecycle_stage": _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip(),
            "item_no": _to_text(sd.get("item_no") or "").strip(),
            "item_name": _to_text(sd.get("item_name") or "").strip(),
            "created_at": _to_text(row.get("created_at") or "").strip(),
            "distance_m": round(dist, 2),
        }
        if len(hits) >= limit:
            break

    return {
        "ok": True,
        "project_uri": project_uri,
        "center": {"lat": lat, "lng": lng, "radius_m": radius_m},
        "items": list(hits.values()),
    }
