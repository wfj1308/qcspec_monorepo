"""SpecIR global registry helpers.

Stores global, reusable standard-library objects (SPU/spec/gate/quota/meter_rule).
Project rows should persist only `ref_*` URIs, then resolve through this registry.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from services.api.domain.specir.runtime.spu_schema import validate_spu_content

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


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _table_exists_probe(sb: Any, table_name: str) -> bool:
    try:
        sb.table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def _normalize_uri(uri: Any) -> str:
    text = _to_text(uri).strip()
    if not text:
        return ""
    return re.sub(r"\s+", "", text)


def _extract_version(uri: str) -> str:
    normalized = _normalize_uri(uri)
    if not normalized:
        return "v1"
    if "@" in normalized:
        return _to_text(normalized.rsplit("@", 1)[-1]).strip() or "v1"
    return "v1"


def specir_is_ready(*, sb: Any) -> bool:
    return _table_exists_probe(sb, "specir_objects")


def get_specir_object(*, sb: Any, uri: str) -> dict[str, Any]:
    normalized_uri = _normalize_uri(uri)
    if not normalized_uri:
        return {"ok": False, "error": "uri_required"}
    if not specir_is_ready(sb=sb):
        return {"ok": False, "error": "specir_table_not_ready", "uri": normalized_uri}
    rows = (
        sb.table("specir_objects")
        .select("*")
        .eq("uri", normalized_uri)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return {"ok": False, "error": "not_found", "uri": normalized_uri}
    row = _as_dict(rows[0])
    return {
        "ok": True,
        "uri": _to_text(row.get("uri") or normalized_uri).strip(),
        "kind": _to_text(row.get("kind") or "").strip(),
        "version": _to_text(row.get("version") or "").strip(),
        "title": _to_text(row.get("title") or "").strip(),
        "content": _as_dict(row.get("content")),
        "content_hash": _to_text(row.get("content_hash") or "").strip(),
        "status": _to_text(row.get("status") or "").strip(),
        "metadata": _as_dict(row.get("metadata")),
        "updated_at": _to_text(row.get("updated_at") or "").strip(),
        "created_at": _to_text(row.get("created_at") or "").strip(),
    }


def upsert_specir_object(
    *,
    sb: Any,
    uri: str,
    kind: str,
    content: dict[str, Any] | None = None,
    version: str = "",
    title: str = "",
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_uri = _normalize_uri(uri)
    if not normalized_uri:
        return {"ok": False, "error": "uri_required"}
    normalized_kind = _to_text(kind).strip().lower()
    if not normalized_kind:
        return {"ok": False, "error": "kind_required", "uri": normalized_uri}
    if not specir_is_ready(sb=sb):
        return {"ok": False, "error": "specir_table_not_ready", "uri": normalized_uri}
    payload_content = _as_dict(content)
    if normalized_kind == "spu":
        validation = validate_spu_content(
            spu_uri=normalized_uri,
            title=_to_text(title).strip(),
            content=payload_content,
        )
        if not bool(validation.get("ok")):
            return {
                "ok": False,
                "error": _to_text(validation.get("error") or "invalid_spu_schema").strip(),
                "detail": validation.get("detail") or [],
                "uri": normalized_uri,
            }
        payload_content = _as_dict(validation.get("content"))
    payload = {
        "uri": normalized_uri,
        "kind": normalized_kind,
        "version": _to_text(version).strip() or _extract_version(normalized_uri),
        "title": _to_text(title).strip(),
        "content": payload_content,
        "content_hash": _sha256_json(payload_content),
        "status": _to_text(status).strip().lower() or "active",
        "metadata": _as_dict(metadata),
    }
    rows = (
        sb.table("specir_objects")
        .upsert(payload, on_conflict="uri")
        .execute()
        .data
        or []
    )
    row = _as_dict(rows[0]) if rows else payload
    return {
        "ok": True,
        "uri": _to_text(row.get("uri") or normalized_uri).strip(),
        "kind": _to_text(row.get("kind") or normalized_kind).strip(),
        "version": _to_text(row.get("version") or payload["version"]).strip(),
        "title": _to_text(row.get("title") or payload["title"]).strip(),
        "content_hash": _to_text(row.get("content_hash") or payload["content_hash"]).strip(),
        "status": _to_text(row.get("status") or payload["status"]).strip(),
        "metadata": _as_dict(row.get("metadata") or payload["metadata"]),
        "updated_at": _to_text(row.get("updated_at") or _utc_iso()).strip(),
    }


def ensure_specir_object(
    *,
    sb: Any,
    uri: str,
    kind: str,
    content: dict[str, Any] | None = None,
    version: str = "",
    title: str = "",
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = get_specir_object(sb=sb, uri=uri)
    if bool(current.get("ok")):
        return current
    return upsert_specir_object(
        sb=sb,
        uri=uri,
        kind=kind,
        content=content,
        version=version,
        title=title,
        status=status,
        metadata=metadata,
    )


def build_specir_ref_uri(*, kind: str, key: str, version: str = "v1") -> str:
    normalized_kind = _to_text(kind).strip().lower()
    normalized_key = _to_text(key).strip().strip("/")
    normalized_version = _to_text(version).strip() or "v1"
    if not normalized_kind or not normalized_key:
        return ""
    return f"v://norm/{normalized_kind}/{normalized_key}@{normalized_version}"


__all__ = [
    "build_specir_ref_uri",
    "ensure_specir_object",
    "get_specir_object",
    "specir_is_ready",
    "upsert_specir_object",
]
