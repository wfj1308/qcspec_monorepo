"""Canonical projects profile normalization helpers."""

from __future__ import annotations

from typing import Any

VALID_SEG_TYPES = {"km", "contract", "structure"}
VALID_PERM_TEMPLATES = {"standard", "strict", "open", "custom"}
VALID_INSPECTION_TYPES = {"flatness", "crack", "rut", "compaction", "settlement"}
VALID_DTO_ROLES = {"OWNER", "SUPERVISOR", "AI", "PUBLIC"}
VALID_ZERO_SIGN_STATUS = {"pending", "approved", "rejected"}


def normalize_seg_type(value: Any) -> str:
    text = str(value or "km").strip().lower()
    return text if text in VALID_SEG_TYPES else "km"


def normalize_perm_template(value: Any) -> str:
    text = str(value or "standard").strip().lower()
    return text if text in VALID_PERM_TEMPLATES else "standard"


def normalize_km_interval(value: Any) -> int:
    try:
        interval = int(value)
    except Exception:
        interval = 20
    return max(1, min(interval, 500))


def normalize_inspection_types(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        key = str(item or "").strip()
        if key in VALID_INSPECTION_TYPES and key not in out:
            out.append(key)
    return out


def normalize_contract_segs(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        seg_range = str(item.get("range") or "").strip()
        if not name and not seg_range:
            continue
        out.append({"name": name, "range": seg_range})
        if len(out) >= 200:
            break
    return out


def normalize_structures(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        name = str(item.get("name") or "").strip()
        code = str(item.get("code") or "").strip()
        if not kind and not name and not code:
            continue
        out.append({"kind": kind, "name": name, "code": code})
        if len(out) >= 200:
            break
    return out


def normalize_zero_sign_status(value: Any) -> str:
    text = str(value or "pending").strip().lower()
    return text if text in VALID_ZERO_SIGN_STATUS else "pending"


def normalize_zero_personnel(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        title = str(item.get("title") or "").strip()
        dto_role = str(item.get("dto_role") or item.get("dtoRole") or "AI").strip().upper()
        if dto_role not in VALID_DTO_ROLES:
            dto_role = "AI"
        certificate = str(item.get("certificate") or "").strip()
        executor_uri = str(item.get("executor_uri") or item.get("executorUri") or "").strip()
        if not name and not title and not certificate:
            continue
        out.append({
            "name": name,
            "title": title,
            "dto_role": dto_role,
            "certificate": certificate,
            "executor_uri": executor_uri,
        })
        if len(out) >= 500:
            break
    return out


def normalize_zero_equipment(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        model_no = str(item.get("model_no") or item.get("modelNo") or "").strip()
        inspection_item = str(item.get("inspection_item") or item.get("inspectionItem") or "").strip()
        valid_until = str(item.get("valid_until") or item.get("validUntil") or "").strip()
        toolpeg_uri = str(item.get("toolpeg_uri") or item.get("toolpegUri") or "").strip()
        status = str(item.get("status") or "").strip()
        if not name and not model_no:
            continue
        out.append({
            "name": name,
            "model_no": model_no,
            "inspection_item": inspection_item,
            "valid_until": valid_until,
            "toolpeg_uri": toolpeg_uri,
            "status": status,
        })
        if len(out) >= 500:
            break
    return out


def normalize_zero_subcontracts(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        unit_name = str(item.get("unit_name") or item.get("unitName") or "").strip()
        content = str(item.get("content") or "").strip()
        seg_range = str(item.get("range") or "").strip()
        node_uri = str(item.get("node_uri") or item.get("nodeUri") or "").strip()
        if not unit_name and not content and not seg_range:
            continue
        out.append({
            "unit_name": unit_name,
            "content": content,
            "range": seg_range,
            "node_uri": node_uri,
        })
        if len(out) >= 500:
            break
    return out


def normalize_zero_materials(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        spec = str(item.get("spec") or "").strip()
        supplier = str(item.get("supplier") or "").strip()
        freq = str(item.get("freq") or "").strip()
        if not name and not spec and not supplier and not freq:
            continue
        out.append({
            "name": name,
            "spec": spec,
            "supplier": supplier,
            "freq": freq,
        })
        if len(out) >= 500:
            break
    return out


_normalize_seg_type = normalize_seg_type
_normalize_perm_template = normalize_perm_template
_normalize_km_interval = normalize_km_interval
_normalize_inspection_types = normalize_inspection_types
_normalize_contract_segs = normalize_contract_segs
_normalize_structures = normalize_structures
_normalize_zero_sign_status = normalize_zero_sign_status
_normalize_zero_personnel = normalize_zero_personnel
_normalize_zero_equipment = normalize_zero_equipment
_normalize_zero_subcontracts = normalize_zero_subcontracts
_normalize_zero_materials = normalize_zero_materials


__all__ = [
    "VALID_SEG_TYPES",
    "VALID_PERM_TEMPLATES",
    "VALID_INSPECTION_TYPES",
    "VALID_DTO_ROLES",
    "VALID_ZERO_SIGN_STATUS",
    "normalize_seg_type",
    "normalize_perm_template",
    "normalize_km_interval",
    "normalize_inspection_types",
    "normalize_contract_segs",
    "normalize_structures",
    "normalize_zero_sign_status",
    "normalize_zero_personnel",
    "normalize_zero_equipment",
    "normalize_zero_subcontracts",
    "normalize_zero_materials",
    "_normalize_seg_type",
    "_normalize_perm_template",
    "_normalize_km_interval",
    "_normalize_inspection_types",
    "_normalize_contract_segs",
    "_normalize_structures",
    "_normalize_zero_sign_status",
    "_normalize_zero_personnel",
    "_normalize_zero_equipment",
    "_normalize_zero_subcontracts",
    "_normalize_zero_materials",
]
