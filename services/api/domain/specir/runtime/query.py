"""Query helpers for SpecIR standard library browsing."""

from __future__ import annotations

from typing import Any

from services.api.domain.specir.runtime.catalog import BUILTIN_QCSPEC_SPECIR_CATALOG
from services.api.domain.specir.runtime.registry import specir_is_ready
from services.api.domain.specir.runtime.spu_library import BUILTIN_QCSPEC_FULL_SPU_LIBRARY


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _extract_spu_summary(item: dict[str, Any]) -> dict[str, Any]:
    uri = _to_text(item.get("uri")).strip()
    title = _to_text(item.get("title")).strip()
    content = _as_dict(item.get("content"))
    identity = _as_dict(content.get("identity"))
    measure_rule = _as_dict(content.get("measure_rule"))
    consumption = _as_dict(content.get("consumption"))
    qc_gate = _as_dict(content.get("qc_gate"))
    return {
        "uri": uri,
        "version": _to_text(uri.rsplit("@", 1)[-1] if "@" in uri else "").strip(),
        "title": title,
        "industry": _to_text(identity.get("industry")).strip(),
        "category_path": [str(x).strip() for x in _as_list(identity.get("category_path")) if str(x).strip()],
        "standard_codes": [str(x).strip() for x in _as_list(identity.get("standard_codes")) if str(x).strip()],
        "unit": _to_text(measure_rule.get("unit") or content.get("unit")).strip(),
        "quota_ref": _to_text(consumption.get("quota_ref") or content.get("quota_ref")).strip(),
        "meter_rule_ref": _to_text(measure_rule.get("meter_rule_ref") or content.get("meter_rule_ref")).strip(),
        "gate_refs": [str(x).strip() for x in _as_list(qc_gate.get("gate_refs") or content.get("gate_refs")) if str(x).strip()],
        "schema": _to_text(content.get("schema")).strip(),
    }


def _match_filters(
    *,
    row: dict[str, Any],
    industry: str = "",
    version: str = "",
    q: str = "",
) -> bool:
    target_industry = _to_text(industry).strip().lower()
    target_version = _to_text(version).strip().lower()
    target_q = _to_text(q).strip().lower()
    if target_industry:
        if target_industry not in _to_text(row.get("industry")).strip().lower():
            return False
    if target_version:
        if target_version not in _to_text(row.get("version")).strip().lower():
            return False
    if target_q:
        haystack = " ".join(
            [
                _to_text(row.get("uri")).strip().lower(),
                _to_text(row.get("title")).strip().lower(),
                _to_text(row.get("industry")).strip().lower(),
                " ".join([_to_text(x).strip().lower() for x in _as_list(row.get("category_path"))]),
                " ".join([_to_text(x).strip().lower() for x in _as_list(row.get("standard_codes"))]),
            ]
        )
        if target_q not in haystack:
            return False
    return True


def _fetch_registry_spu_rows(*, sb: Any, status: str = "active", limit: int = 200) -> list[dict[str, Any]]:
    if sb is None:
        return []
    if not specir_is_ready(sb=sb):
        return []
    capped = max(1, min(int(limit or 200), 1000))
    query = sb.table("specir_objects").select("uri,kind,title,content,status,updated_at").eq("kind", "spu")
    normalized_status = _to_text(status).strip().lower()
    if normalized_status:
        query = query.eq("status", normalized_status)
    rows = query.order("updated_at", desc=True).limit(capped).execute().data or []
    return [_as_dict(row) for row in rows]


def list_specir_spu_library(
    *,
    sb: Any = None,
    source: str = "builtin",
    industry: str = "",
    version: str = "",
    q: str = "",
    limit: int = 200,
    status: str = "active",
) -> dict[str, Any]:
    normalized_source = _to_text(source).strip().lower() or "builtin"
    include_builtin = normalized_source in {"builtin", "all"}
    include_registry = normalized_source in {"registry", "all"}

    merged: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    if include_builtin:
        for item in BUILTIN_QCSPEC_FULL_SPU_LIBRARY:
            row = _extract_spu_summary(_as_dict(item))
            if row.get("uri"):
                merged[str(row["uri"])] = row
                sources[str(row["uri"])] = "builtin_full"
        # Keep fallback compatibility for catalog SPU rows.
        for item in BUILTIN_QCSPEC_SPECIR_CATALOG:
            if _to_text(_as_dict(item).get("kind")).strip().lower() != "spu":
                continue
            row = _extract_spu_summary(_as_dict(item))
            uri = _to_text(row.get("uri")).strip()
            if uri and uri not in merged:
                merged[uri] = row
                sources[uri] = "builtin_catalog"

    if include_registry:
        registry_rows = _fetch_registry_spu_rows(sb=sb, status=status, limit=limit)
        for item in registry_rows:
            row = _extract_spu_summary(item)
            uri = _to_text(row.get("uri")).strip()
            if uri:
                merged[uri] = row
                sources[uri] = "registry"

    rows = []
    for uri, row in merged.items():
        if _match_filters(row=row, industry=industry, version=version, q=q):
            rows.append({**row, "source": sources.get(uri, normalized_source)})
    rows.sort(key=lambda x: (_to_text(x.get("uri")).strip().lower(), _to_text(x.get("title")).strip().lower()))
    capped = max(1, min(int(limit or 200), 1000))
    rows = rows[:capped]

    return {
        "ok": True,
        "source": normalized_source,
        "count": len(rows),
        "items": rows,
        "filters": {
            "industry": _to_text(industry).strip(),
            "version": _to_text(version).strip(),
            "q": _to_text(q).strip(),
            "limit": capped,
            "status": _to_text(status).strip(),
        },
    }


__all__ = [
    "list_specir_spu_library",
]
