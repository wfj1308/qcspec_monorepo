"""Project boundary resolution helpers for TripRole execution."""

from __future__ import annotations

import os
from typing import Any

from services.api.domain.execution.triprole_common import as_dict, as_list, safe_json_loads, to_text
from services.api.domain.execution.triprole_geofence import normalize_geo_fence_boundary


def _load_project_custom_fields(*, sb: Any, project_id: Any, project_uri: str) -> dict[str, Any]:
    enterprise_id = ""
    pid = to_text(project_id).strip()
    p_uri = to_text(project_uri).strip()
    try:
        q = sb.table("projects").select("enterprise_id")
        if pid:
            rows = q.eq("id", pid).limit(1).execute().data or []
        else:
            rows = q.eq("v_uri", p_uri).limit(1).execute().data or []
        if rows and isinstance(rows[0], dict):
            enterprise_id = to_text(rows[0].get("enterprise_id") or "").strip()
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
    return as_dict(cfg_rows[0].get("custom_fields"))


def _resolve_project_boundary(*, sb: Any, project_id: Any, project_uri: str, override: Any = None) -> dict[str, Any]:
    override_payload = as_dict(override)
    if override_payload:
        return normalize_geo_fence_boundary(override_payload)

    custom = _load_project_custom_fields(sb=sb, project_id=project_id, project_uri=project_uri)
    candidates: list[Any] = []
    candidates.append(custom.get("site_boundary"))
    candidates.append(custom.get("geo_fence"))
    candidates.append(custom.get("project_site_boundary"))

    boundary_map = as_dict(custom.get("project_site_boundaries"))
    if boundary_map:
        pid = to_text(project_id).strip()
        if project_uri in boundary_map:
            candidates.insert(0, boundary_map.get(project_uri))
        if pid and pid in boundary_map:
            candidates.insert(0, boundary_map.get(pid))

    boundary_list = as_list(custom.get("project_site_boundaries"))
    pid = to_text(project_id).strip()
    for item in boundary_list:
        if not isinstance(item, dict):
            continue
        item_uri = to_text(item.get("project_uri") or "").strip()
        item_pid = to_text(item.get("project_id") or "").strip()
        if (item_uri and item_uri == project_uri) or (pid and item_pid == pid):
            candidates.insert(0, item.get("boundary") or item)

    env_boundary = safe_json_loads(os.getenv("QCSPEC_SITE_BOUNDARY") or "")
    if env_boundary:
        candidates.append(env_boundary)

    for candidate in candidates:
        normalized = normalize_geo_fence_boundary(candidate)
        if normalized.get("enforced"):
            return normalized
    return {"enforced": False, "type": "none"}


__all__ = [
    "_load_project_custom_fields",
    "_resolve_project_boundary",
]
