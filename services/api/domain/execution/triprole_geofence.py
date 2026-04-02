"""Geo-fence boundary helpers for TripRole execution."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any

from services.api.domain.execution.triprole_common import (
    as_dict,
    as_list,
    sha256_json,
    to_bool,
    to_float,
    to_text,
)
from services.api.domain.execution.triprole_geo_sensor import normalize_geo_location


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6371000.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    value = sin(d_lat / 2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2.0) ** 2
    angle = 2.0 * asin(min(1.0, sqrt(value)))
    return float(radius_m * angle)


def point_in_polygon(*, lat: float, lng: float, polygon: list[dict[str, float]]) -> bool:
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


def normalize_geo_fence_boundary(raw: Any) -> dict[str, Any]:
    payload = as_dict(raw)
    if not payload:
        return {"enforced": False, "type": "none"}

    boundary_type = to_text(payload.get("type") or payload.get("boundary_type") or "").strip().lower()
    if not boundary_type:
        if isinstance(payload.get("polygon"), list) or isinstance(payload.get("coordinates"), list):
            boundary_type = "polygon"
        elif isinstance(payload.get("center"), dict) or ("radius_m" in payload):
            boundary_type = "circle"
        elif all(k in payload for k in ("min_lat", "max_lat", "min_lng", "max_lng")):
            boundary_type = "bbox"

    strict_mode = to_bool(payload.get("strict_mode"))
    deviation_m = to_float(payload.get("allowed_deviation_m"))
    if deviation_m is None:
        deviation_m = 0.0

    if boundary_type == "circle":
        center = as_dict(payload.get("center"))
        center_lat = to_float(center.get("lat") if "lat" in center else center.get("latitude"))
        center_lng = to_float(center.get("lng") if "lng" in center else center.get("longitude"))
        radius = to_float(payload.get("radius_m"))
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
        normalized["boundary_fingerprint"] = sha256_json(normalized)
        return normalized

    if boundary_type == "bbox":
        min_lat = to_float(payload.get("min_lat"))
        max_lat = to_float(payload.get("max_lat"))
        min_lng = to_float(payload.get("min_lng"))
        max_lng = to_float(payload.get("max_lng"))
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
        normalized["boundary_fingerprint"] = sha256_json(normalized)
        return normalized

    points_raw = payload.get("polygon")
    if not isinstance(points_raw, list):
        points_raw = payload.get("coordinates")
    points: list[dict[str, float]] = []
    for item in as_list(points_raw):
        if isinstance(item, dict):
            lat = to_float(item.get("lat") if "lat" in item else item.get("latitude"))
            lng = to_float(item.get("lng") if "lng" in item else item.get("longitude"))
            if lat is not None and lng is not None:
                points.append({"lat": float(lat), "lng": float(lng)})
                continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            lng = to_float(item[0])
            lat = to_float(item[1])
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
    normalized["boundary_fingerprint"] = sha256_json(normalized)
    return normalized


def check_location_compliance(current_gps: dict[str, Any], project_boundary: dict[str, Any]) -> dict[str, Any]:
    gps = normalize_geo_location(current_gps)
    boundary = normalize_geo_fence_boundary(project_boundary)
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
    boundary_type = to_text(boundary.get("type") or "").strip().lower()

    if boundary_type == "circle":
        center = as_dict(boundary.get("center"))
        center_lat = float(to_float(center.get("lat")) or 0.0)
        center_lng = float(to_float(center.get("lng")) or 0.0)
        radius = float(to_float(boundary.get("radius_m")) or 0.0)
        distance_m = haversine_distance_m(lat, lng, center_lat, center_lng)
        allowed = radius + float(to_float(boundary.get("allowed_deviation_m")) or 0.0)
        inside = distance_m <= allowed
    elif boundary_type == "bbox":
        min_lat = float(to_float(boundary.get("min_lat")) or -90.0)
        max_lat = float(to_float(boundary.get("max_lat")) or 90.0)
        min_lng = float(to_float(boundary.get("min_lng")) or -180.0)
        max_lng = float(to_float(boundary.get("max_lng")) or 180.0)
        inside = (min_lat <= lat <= max_lat) and (min_lng <= lng <= max_lng)
    else:
        polygon = [
            {"lat": float(to_float(x.get("lat")) or 0.0), "lng": float(to_float(x.get("lng")) or 0.0)}
            for x in as_list(boundary.get("polygon"))
            if isinstance(x, dict)
        ]
        inside = point_in_polygon(lat=lat, lng=lng, polygon=polygon)

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
        "boundary_fingerprint": to_text(boundary.get("boundary_fingerprint") or "").strip(),
    }


__all__ = [
    "haversine_distance_m",
    "point_in_polygon",
    "normalize_geo_fence_boundary",
    "check_location_compliance",
]
