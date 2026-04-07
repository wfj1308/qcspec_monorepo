"""
SpecDict <-> Gate decoupling service.

Implements:
- spec_dicts persistence helpers
- gates persistence helpers
- subitem -> gate binding resolution
- resolve_dynamic_threshold(gate_id, context)
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from fastapi import HTTPException
from services.api.domain.specir.runtime.registry import (
    build_specir_ref_uri,
    ensure_specir_object,
)


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


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_context_tokens(context: Any) -> list[str]:
    raw: list[str] = []
    if isinstance(context, str):
        raw.append(context)
    elif isinstance(context, dict):
        for key in ("context", "component_type", "part", "structure_type", "position"):
            v = _to_text(context.get(key) or "").strip()
            if v:
                raw.append(v)
    alias = {
        # Canonical English keys
        "main_beam": "main_beam",
        "mainbeam": "main_beam",
        "guardrail": "guardrail",
        "pier": "pier",
        "slab": "slab",
        # Chinese aliases (unicode-escaped for stable source encoding)
        "\u4e3b\u6881": "main_beam",       # 主梁
        "\u62a4\u680f": "guardrail",      # 护栏
        "\u6865\u58a9": "pier",           # 桥墩
        "\u6881\u677f": "slab",           # 梁板
        "\u4e0a\u90e8\u7ed3\u6784": "main_beam",  # 上部结构
        "\u4e0b\u90e8\u7ed3\u6784": "pier",       # 下部结构
    }
    out: list[str] = []
    seen: set[str] = set()
    for token in raw:
        original = _to_text(token).strip()
        normalized = original.lower()
        if normalized and normalized not in seen:
            out.append(normalized)
            seen.add(normalized)
        mapped = alias.get(original) or alias.get(normalized)
        if mapped and mapped not in seen:
            out.append(mapped)
            seen.add(mapped)
    return out

def _safe_specdict_key(raw: Any) -> str:
    text = _to_text(raw).strip()
    if not text:
        return ""
    text = text.replace("v://norm/", "").replace("@", "-").replace("/", "-").replace("#", "-")
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", text).strip("-")
    return text[:120]


def _safe_gate_id(raw: Any, *, fallback: str) -> str:
    text = _to_text(raw).strip()
    if text:
        return text
    return fallback


def _safe_spec_uri(spec_uri: Any, spec_dict_key: str, version: str, spec_item: str) -> str:
    text = _to_text(spec_uri).strip()
    if text:
        return text
    v = _to_text(version).strip() or "v1.0"
    key = _to_text(spec_dict_key).strip() or "custom"
    item = _to_text(spec_item).strip()
    if item:
        return f"v://specdict/{key}@{v}#{item}"
    return f"v://specdict/{key}@{v}"


def _safe_ref_token(value: Any) -> str:
    text = _to_text(value).strip()
    if not text:
        return ""
    text = text.replace("::", "/").replace("#", "/").replace("@", "-")
    text = re.sub(r"[^0-9A-Za-z._/-]+", "-", text).strip("-/")
    text = re.sub(r"/{2,}", "/", text)
    return text[:180]


def _build_gate_ref_pack(
    *,
    linked_gate_id: str,
    linked_gate_ids: list[str],
    linked_spec_uri: str,
    spec_dict_key: str,
    spec_item: str,
) -> dict[str, Any]:
    normalized_gate_id = _to_text(linked_gate_id).strip()
    normalized_gate_ids = [_to_text(x).strip() for x in linked_gate_ids if _to_text(x).strip()]
    if normalized_gate_id and normalized_gate_id not in normalized_gate_ids:
        normalized_gate_ids.insert(0, normalized_gate_id)
    ref_gate_uris = [f"v://norm/gate/{_safe_ref_token(gid)}@v1" for gid in normalized_gate_ids if _safe_ref_token(gid)]
    ref_gate_uri = ref_gate_uris[0] if ref_gate_uris else ""
    ref_spec_uri = _to_text(linked_spec_uri).strip() if _to_text(linked_spec_uri).strip().startswith("v://") else ""
    normalized_dict_key = _safe_specdict_key(spec_dict_key)
    ref_spec_dict_uri = f"v://norm/specdict/{_safe_ref_token(normalized_dict_key)}@v1" if normalized_dict_key else ""
    normalized_item = _to_text(spec_item).strip()
    if normalized_item and ref_spec_dict_uri:
        ref_spec_item_uri = f"{ref_spec_dict_uri}#{_safe_ref_token(normalized_item)}"
    elif normalized_item and ref_spec_uri:
        ref_spec_item_uri = f"{ref_spec_uri}#{_safe_ref_token(normalized_item)}"
    else:
        ref_spec_item_uri = ""
    return {
        "ref_gate_uri": ref_gate_uri,
        "ref_gate_uris": ref_gate_uris,
        "ref_spec_uri": ref_spec_uri,
        "ref_spec_dict_uri": ref_spec_dict_uri,
        "ref_spec_item_uri": ref_spec_item_uri,
    }


def _sync_specir_from_spec_dict(
    *,
    sb: Any,
    spec_dict_key: str,
    title: str,
    version: str,
    authority: str,
    spec_uri: str,
    items: dict[str, Any],
    metadata: dict[str, Any],
    is_active: bool,
) -> None:
    token = _safe_ref_token(spec_dict_key)
    if not token:
        return
    ref_spec_dict_uri = build_specir_ref_uri(kind="specdict", key=token, version="v1")
    if not ref_spec_dict_uri:
        return
    try:
        ensure_specir_object(
            sb=sb,
            uri=ref_spec_dict_uri,
            kind="spec_dict",
            title=_to_text(title).strip() or _to_text(spec_dict_key).strip(),
            content={
                "spec_dict_key": _to_text(spec_dict_key).strip(),
                "version": _to_text(version).strip(),
                "authority": _to_text(authority).strip(),
                "spec_uri": _to_text(spec_uri).strip(),
                "items": _as_dict(items),
                "is_active": bool(is_active),
            },
            metadata=_as_dict(metadata),
            status="active" if bool(is_active) else "inactive",
        )
        for item_key, item_rule in _as_dict(items).items():
            normalized_item_key = _to_text(item_key).strip()
            if not normalized_item_key:
                continue
            ensure_specir_object(
                sb=sb,
                uri=f"{ref_spec_dict_uri}#{_safe_ref_token(normalized_item_key)}",
                kind="spec_item",
                title=f"{_to_text(title).strip() or _to_text(spec_dict_key).strip()}::{normalized_item_key}",
                content={
                    "spec_dict_uri": ref_spec_dict_uri,
                    "spec_dict_key": _to_text(spec_dict_key).strip(),
                    "spec_item": normalized_item_key,
                    "rule": _as_dict(item_rule),
                },
                metadata={"source": "specdict_gate.save_spec_dict"},
                status="active" if bool(is_active) else "inactive",
            )
    except Exception:
        return


def _sync_specir_from_gate_binding(
    *,
    sb: Any,
    gate_id: str,
    gate_id_base: str,
    subitem_code: str,
    spec_dict_key: str,
    spec_item: str,
    match_kind: str,
    execution_strategy: str,
    fail_action: str,
    gate_rules: list[dict[str, Any]],
    metadata: dict[str, Any],
    is_active: bool,
) -> None:
    normalized_gate_id = _to_text(gate_id).strip()
    token = _safe_ref_token(normalized_gate_id)
    if not token:
        return
    ref_gate_uri = build_specir_ref_uri(kind="gate", key=token, version="v1")
    if not ref_gate_uri:
        return
    ref_pack = _build_gate_ref_pack(
        linked_gate_id=normalized_gate_id,
        linked_gate_ids=[normalized_gate_id],
        linked_spec_uri="",
        spec_dict_key=spec_dict_key,
        spec_item=spec_item,
    )
    try:
        ensure_specir_object(
            sb=sb,
            uri=ref_gate_uri,
            kind="gate",
            title=normalized_gate_id,
            content={
                "gate_id": normalized_gate_id,
                "gate_id_base": _to_text(gate_id_base).strip(),
                "subitem_code": _to_text(subitem_code).strip(),
                "match_kind": _to_text(match_kind).strip(),
                "execution_strategy": _to_text(execution_strategy).strip(),
                "fail_action": _to_text(fail_action).strip(),
                "spec_dict_key": _to_text(spec_dict_key).strip(),
                "spec_item": _to_text(spec_item).strip(),
                "spec_dict_uri": _to_text(ref_pack.get("ref_spec_dict_uri") or "").strip(),
                "spec_item_uri": _to_text(ref_pack.get("ref_spec_item_uri") or "").strip(),
                "rules": _as_list(gate_rules),
                "is_active": bool(is_active),
            },
            metadata=_as_dict(metadata),
            status="active" if bool(is_active) else "inactive",
        )
    except Exception:
        return


def _extract_item_rule(items: dict[str, Any], spec_item: str) -> tuple[str, dict[str, Any]]:
    if not items:
        return "", {}
    key = _to_text(spec_item).strip()
    if key and isinstance(items.get(key), dict):
        return key, _as_dict(items.get(key))
    for k, v in items.items():
        if isinstance(v, dict):
            return _to_text(k).strip(), v
    return "", {}


def _table_exists_probe(sb: Any, table_name: str) -> bool:
    try:
        sb.table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def get_spec_dict(*, sb: Any, spec_dict_key: str) -> dict[str, Any]:
    key = _safe_specdict_key(spec_dict_key)
    if not key:
        raise HTTPException(400, "spec_dict_key is required")
    if not _table_exists_probe(sb, "spec_dicts"):
        return {"ok": False, "error": "spec_dicts table not ready", "spec_dict_key": key}
    rows = (
        sb.table("spec_dicts")
        .select("*")
        .eq("spec_dict_key", key)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return {"ok": False, "error": "spec_dict not found", "spec_dict_key": key}
    row = _as_dict(rows[0])
    items = _as_dict(row.get("items"))
    return {
        "ok": True,
        "spec_dict_key": _to_text(row.get("spec_dict_key") or "").strip(),
        "title": _to_text(row.get("title") or "").strip(),
        "version": _to_text(row.get("version") or "").strip(),
        "authority": _to_text(row.get("authority") or "").strip(),
        "spec_uri": _to_text(row.get("spec_uri") or "").strip(),
        "items": items,
        "metadata": _as_dict(row.get("metadata")),
        "is_active": bool(row.get("is_active")),
        "created_at": _to_text(row.get("created_at") or "").strip(),
        "updated_at": _to_text(row.get("updated_at") or "").strip(),
    }


def save_spec_dict(
    *,
    sb: Any,
    spec_dict_key: str,
    title: str = "",
    version: str = "v1.0",
    authority: str = "",
    spec_uri: str = "",
    items: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    key = _safe_specdict_key(spec_dict_key)
    if not key:
        raise HTTPException(400, "spec_dict_key is required")
    if not _table_exists_probe(sb, "spec_dicts"):
        raise HTTPException(503, "spec_dicts table not ready, run SQL migration first")
    payload = {
        "spec_dict_key": key,
        "title": _to_text(title).strip() or key,
        "version": _to_text(version).strip() or "v1.0",
        "authority": _to_text(authority).strip(),
        "spec_uri": _to_text(spec_uri).strip(),
        "items": _as_dict(items),
        "metadata": _as_dict(metadata),
        "is_active": bool(is_active),
    }
    rows = (
        sb.table("spec_dicts")
        .upsert(payload, on_conflict="spec_dict_key")
        .execute()
        .data
        or []
    )
    row = _as_dict(rows[0]) if rows else payload
    saved_items = _as_dict(row.get("items") or payload["items"])
    saved_metadata = _as_dict(row.get("metadata") or payload["metadata"])
    _sync_specir_from_spec_dict(
        sb=sb,
        spec_dict_key=_to_text(row.get("spec_dict_key") or key).strip(),
        title=_to_text(row.get("title") or payload["title"]).strip(),
        version=_to_text(row.get("version") or payload["version"]).strip(),
        authority=_to_text(row.get("authority") or payload["authority"]).strip(),
        spec_uri=_to_text(row.get("spec_uri") or payload["spec_uri"]).strip(),
        items=saved_items,
        metadata=saved_metadata,
        is_active=bool(row.get("is_active") if row.get("is_active") is not None else payload["is_active"]),
    )
    return {
        "ok": True,
        "spec_dict_key": _to_text(row.get("spec_dict_key") or key).strip(),
        "title": _to_text(row.get("title") or payload["title"]).strip(),
        "version": _to_text(row.get("version") or payload["version"]).strip(),
        "spec_uri": _to_text(row.get("spec_uri") or payload["spec_uri"]).strip(),
        "items": saved_items,
        "metadata": saved_metadata,
        "updated_at": _to_text(row.get("updated_at") or _utc_iso()).strip(),
    }


def _load_spec_dict_map(*, sb: Any, keys: list[str]) -> dict[str, dict[str, Any]]:
    normalized = sorted({k for k in (_safe_specdict_key(x) for x in keys) if k})
    if not normalized:
        return {}
    if not _table_exists_probe(sb, "spec_dicts"):
        return {}
    rows = (
        sb.table("spec_dicts")
        .select("*")
        .in_("spec_dict_key", normalized)
        .eq("is_active", True)
        .limit(1000)
        .execute()
        .data
        or []
    )
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        rd = _as_dict(row)
        key = _safe_specdict_key(rd.get("spec_dict_key"))
        if key:
            out[key] = rd
    return out


def _load_candidate_gates(*, sb: Any) -> list[dict[str, Any]]:
    if not _table_exists_probe(sb, "gates"):
        return []
    return (
        sb.table("gates")
        .select("*")
        .eq("is_active", True)
        .limit(5000)
        .execute()
        .data
        or []
    )


def _gate_match_score(subitem_code: str, gate_row: dict[str, Any]) -> int:
    target = _to_text(subitem_code).strip()
    pattern = _to_text(gate_row.get("subitem_code") or "").strip()
    match_kind = _to_text(gate_row.get("match_kind") or "").strip().lower()
    if not target or not pattern:
        return -1
    if match_kind == "exact":
        return 1000 if target == pattern else -1
    if match_kind == "chapter":
        chapter = target.split("-")[0] if "-" in target else target
        return 500 if chapter == pattern else -1
    # default prefix
    if target == pattern:
        return 800
    if target.startswith(f"{pattern}-"):
        return 700 - abs(len(target) - len(pattern))
    return -1


def resolve_gate_binding(
    *,
    sb: Any,
    subitem_code: str,
    fallback_spec_uri: str = "",
) -> dict[str, Any]:
    code = _to_text(subitem_code).strip()
    if not code:
        payload = {
            "from_registry": False,
            "item_code": "",
            "linked_gate_id": "",
            "linked_gate_ids": [],
            "linked_gate_rules": [],
            "linked_spec_uri": _to_text(fallback_spec_uri).strip(),
            "spec_dict_key": "",
            "spec_item": "",
            "gate_template_lock": False,
            "gate_binding_hash": "",
        }
        payload.update(
            _build_gate_ref_pack(
                linked_gate_id="",
                linked_gate_ids=[],
                linked_spec_uri=_to_text(fallback_spec_uri).strip(),
                spec_dict_key="",
                spec_item="",
            )
        )
        return payload

    candidate_rows = _load_candidate_gates(sb=sb)
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in candidate_rows:
        rd = _as_dict(row)
        score = _gate_match_score(code, rd)
        if score >= 0:
            scored.append((score, rd))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected_rows = [row for _, row in scored]

    spec_map = _load_spec_dict_map(
        sb=sb,
        keys=[_to_text(x.get("spec_dict_key") or "").strip() for x in selected_rows],
    )
    linked_rules: list[dict[str, Any]] = []
    linked_gate_ids: list[str] = []
    linked_spec_uri = _to_text(fallback_spec_uri).strip()
    spec_dict_key = ""
    spec_item = ""
    execution_strategy = "all_pass"
    fail_action = "trigger_review_trip"

    for idx, gate in enumerate(selected_rows):
        gate_id = _to_text(gate.get("gate_id") or "").strip()
        if not gate_id:
            continue
        linked_gate_ids.append(gate_id)
        dict_key = _safe_specdict_key(gate.get("spec_dict_key"))
        dict_row = _as_dict(spec_map.get(dict_key))
        item_key = _to_text(gate.get("spec_item") or "").strip()
        item_rule_key, item_rule = _extract_item_rule(_as_dict(dict_row.get("items")), item_key)
        gate_spec_uri = _safe_spec_uri(
            dict_row.get("spec_uri"),
            dict_key,
            _to_text(dict_row.get("version") or "v1.0").strip(),
            item_rule_key,
        )
        linked_rules.append(
            {
                "gate_id": gate_id,
                "gate_key": gate_id.split("::")[-1] if "::" in gate_id else gate_id,
                "gate_name": _to_text(gate.get("metadata") or {}).strip() if isinstance(gate.get("metadata"), str) else "",
                "match_kind": _to_text(gate.get("match_kind") or "").strip(),
                "match_code": _to_text(gate.get("subitem_code") or "").strip(),
                "spec_dict_key": dict_key,
                "spec_item": item_rule_key or item_key,
                "spec_uri": gate_spec_uri,
                "operator": _to_text(item_rule.get("operator") or "").strip().lower(),
                "unit": _to_text(item_rule.get("unit") or "").strip(),
                "metric": _to_text(item_rule_key).strip(),
                "priority": idx,
            }
        )
        if not linked_spec_uri and gate_spec_uri:
            linked_spec_uri = gate_spec_uri
        if not spec_dict_key and dict_key:
            spec_dict_key = dict_key
        if not spec_item and (item_rule_key or item_key):
            spec_item = item_rule_key or item_key
        if idx == 0:
            execution_strategy = _to_text(gate.get("execution_strategy") or "").strip() or execution_strategy
            fail_action = _to_text(gate.get("fail_action") or "").strip() or fail_action

    if not linked_gate_ids:
        fallback_gate_id = f"QCGate::{code}::AUTO_DEFAULT"
        linked_gate_ids = [fallback_gate_id]
        linked_rules = [
            {
                "gate_id": fallback_gate_id,
                "gate_key": "AUTO_DEFAULT",
                "gate_name": "Auto Fallback Gate",
                "match_kind": "fallback",
                "match_code": code,
                "spec_dict_key": "",
                "spec_item": "",
                "spec_uri": linked_spec_uri,
                "operator": "",
                "unit": "",
                "metric": "",
                "priority": 0,
            }
        ]

    linked_gate_id = linked_gate_ids[0]
    gate_template_lock = bool(spec_dict_key or linked_spec_uri)
    gate_binding_hash = _sha256_json(
        {
            "item_code": code,
            "linked_gate_id": linked_gate_id,
            "linked_gate_ids": linked_gate_ids,
            "linked_spec_uri": linked_spec_uri,
            "spec_dict_key": spec_dict_key,
            "spec_item": spec_item,
        }
    )
    payload = {
        "from_registry": bool(selected_rows),
        "item_code": code,
        "linked_gate_id": linked_gate_id,
        "linked_gate_ids": linked_gate_ids,
        "linked_gate_rules": linked_rules,
        "linked_spec_uri": linked_spec_uri,
        "spec_dict_key": spec_dict_key,
        "spec_item": spec_item,
        "execution_strategy": execution_strategy,
        "fail_action": fail_action,
        "gate_template_lock": gate_template_lock,
        "gate_binding_hash": gate_binding_hash,
    }
    payload.update(
        _build_gate_ref_pack(
            linked_gate_id=linked_gate_id,
            linked_gate_ids=linked_gate_ids,
            linked_spec_uri=linked_spec_uri,
            spec_dict_key=spec_dict_key,
            spec_item=spec_item,
        )
    )
    return payload


def upsert_gate_binding(
    *,
    sb: Any,
    gate_id: str,
    subitem_code: str,
    spec_dict_key: str,
    spec_item: str,
    gate_id_base: str = "",
    match_kind: str = "exact",
    execution_strategy: str = "all_pass",
    fail_action: str = "trigger_review_trip",
    context: str = "",
    gate_rules: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    if not _table_exists_probe(sb, "gates"):
        raise HTTPException(503, "gates table not ready, run SQL migration first")
    normalized_gate_id = _safe_gate_id(gate_id, fallback=f"QCGate::{_to_text(subitem_code).strip()}::AUTO")
    normalized_key = _safe_specdict_key(spec_dict_key)
    if not normalized_key:
        raise HTTPException(400, "spec_dict_key is required for gate binding")
    payload = {
        "gate_id": normalized_gate_id,
        "gate_id_base": _to_text(gate_id_base).strip() or normalized_gate_id,
        "subitem_code": _to_text(subitem_code).strip(),
        "match_kind": _to_text(match_kind).strip() or "exact",
        "execution_strategy": _to_text(execution_strategy).strip() or "all_pass",
        "fail_action": _to_text(fail_action).strip() or "trigger_review_trip",
        "spec_dict_key": normalized_key,
        "spec_item": _to_text(spec_item).strip(),
        "context": _to_text(context).strip(),
        "gate_rules": _as_list(gate_rules),
        "metadata": _as_dict(metadata),
        "is_active": bool(is_active),
    }
    rows = sb.table("gates").upsert(payload, on_conflict="gate_id").execute().data or []
    row = _as_dict(rows[0]) if rows else payload
    _sync_specir_from_gate_binding(
        sb=sb,
        gate_id=_to_text(row.get("gate_id") or normalized_gate_id).strip(),
        gate_id_base=_to_text(row.get("gate_id_base") or payload["gate_id_base"]).strip(),
        subitem_code=_to_text(row.get("subitem_code") or payload["subitem_code"]).strip(),
        spec_dict_key=_to_text(row.get("spec_dict_key") or normalized_key).strip(),
        spec_item=_to_text(row.get("spec_item") or payload["spec_item"]).strip(),
        match_kind=_to_text(row.get("match_kind") or payload["match_kind"]).strip(),
        execution_strategy=_to_text(row.get("execution_strategy") or payload["execution_strategy"]).strip(),
        fail_action=_to_text(row.get("fail_action") or payload["fail_action"]).strip(),
        gate_rules=_as_list(row.get("gate_rules") or payload["gate_rules"]),
        metadata=_as_dict(row.get("metadata") or payload["metadata"]),
        is_active=bool(row.get("is_active") if row.get("is_active") is not None else payload["is_active"]),
    )
    return {
        "ok": True,
        "gate_id": _to_text(row.get("gate_id") or normalized_gate_id).strip(),
        "subitem_code": _to_text(row.get("subitem_code") or payload["subitem_code"]).strip(),
        "spec_dict_key": _to_text(row.get("spec_dict_key") or normalized_key).strip(),
        "spec_item": _to_text(row.get("spec_item") or payload["spec_item"]).strip(),
    }


def resolve_dynamic_threshold(
    *,
    sb: Any,
    gate_id: str,
    context: Any = None,
) -> dict[str, Any]:
    normalized_gate_id = _to_text(gate_id).strip()
    if not normalized_gate_id:
        return {"found": False, "reason": "gate_id_empty"}
    if not _table_exists_probe(sb, "gates") or not _table_exists_probe(sb, "spec_dicts"):
        return {"found": False, "reason": "specdict_or_gates_table_not_ready", "gate_id": normalized_gate_id}

    gate_rows = (
        sb.table("gates")
        .select("*")
        .eq("gate_id", normalized_gate_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
        .data
        or []
    )
    gate_row = _as_dict(gate_rows[0]) if gate_rows else {}
    if not gate_row and "@v" in normalized_gate_id.lower():
        gate_base = normalized_gate_id.split("@", 1)[0]
        gate_rows = (
            sb.table("gates")
            .select("*")
            .eq("gate_id_base", gate_base)
            .eq("is_active", True)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        gate_row = _as_dict(gate_rows[0]) if gate_rows else {}
    if not gate_row:
        return {"found": False, "reason": "gate_not_found", "gate_id": normalized_gate_id}

    spec_key = _safe_specdict_key(gate_row.get("spec_dict_key"))
    spec_pack = get_spec_dict(sb=sb, spec_dict_key=spec_key)
    if not spec_pack.get("ok"):
        return {
            "found": False,
            "reason": "spec_dict_not_found",
            "gate_id": _to_text(gate_row.get("gate_id") or normalized_gate_id).strip(),
            "spec_dict_key": spec_key,
        }

    items = _as_dict(spec_pack.get("items"))
    item_key, item_rule = _extract_item_rule(items, _to_text(gate_row.get("spec_item") or "").strip())
    if not item_rule:
        return {
            "found": False,
            "reason": "spec_item_not_found",
            "gate_id": _to_text(gate_row.get("gate_id") or normalized_gate_id).strip(),
            "spec_dict_key": spec_key,
            "spec_item": _to_text(gate_row.get("spec_item") or "").strip(),
        }

    default_threshold = item_rule.get("default_threshold")
    if default_threshold is None:
        default_threshold = item_rule.get("threshold")
    context_rules = _as_dict(item_rule.get("context_rules"))
    context_key = ""
    selected_threshold = default_threshold
    for token in _normalize_context_tokens(context):
        if token in context_rules:
            context_key = token
            selected_threshold = context_rules[token]
            break

    spec_uri = _safe_spec_uri(
        spec_pack.get("spec_uri"),
        spec_key,
        _to_text(spec_pack.get("version") or "v1.0").strip(),
        item_key,
    )
    ref_pack = _build_gate_ref_pack(
        linked_gate_id=_to_text(gate_row.get("gate_id") or "").strip(),
        linked_gate_ids=[_to_text(gate_row.get("gate_id") or "").strip()],
        linked_spec_uri=spec_uri,
        spec_dict_key=spec_key,
        spec_item=item_key,
    )
    return {
        "found": True,
        "gate_id": _to_text(gate_row.get("gate_id") or "").strip(),
        "gate_id_base": _to_text(gate_row.get("gate_id_base") or "").strip(),
        "spec_dict_key": spec_key,
        "spec_item": item_key,
        "ref_gate_uri": _to_text(ref_pack.get("ref_gate_uri") or "").strip(),
        "ref_spec_uri": _to_text(ref_pack.get("ref_spec_uri") or "").strip(),
        "ref_spec_dict_uri": _to_text(ref_pack.get("ref_spec_dict_uri") or "").strip(),
        "ref_spec_item_uri": _to_text(ref_pack.get("ref_spec_item_uri") or "").strip(),
        "title": _to_text(spec_pack.get("title") or "").strip(),
        "version": _to_text(spec_pack.get("version") or "").strip(),
        "spec_uri": spec_uri,
        "effective_spec_uri": spec_uri,
        "context_key": context_key,
        "context_matched": bool(context_key),
        "threshold": selected_threshold,
        "operator": _to_text(item_rule.get("operator") or "range").strip().lower(),
        "unit": _to_text(item_rule.get("unit") or "").strip(),
        "mode": _to_text(item_rule.get("mode") or "absolute").strip().lower() or "absolute",
        "spec_excerpt": _to_text(spec_pack.get("title") or "").strip(),
        "params_snapshot": item_rule,
        "execution_strategy": _to_text(gate_row.get("execution_strategy") or "").strip(),
        "fail_action": _to_text(gate_row.get("fail_action") or "").strip(),
    }


def evaluate_with_threshold_pack(
    *,
    threshold_pack: dict[str, Any],
    values: list[float],
    design_value: float | None,
) -> dict[str, Any]:
    pack = _as_dict(threshold_pack)
    vals = [float(v) for v in (values or [])]
    if not bool(pack.get("found")):
        return {
            "matched": False,
            "threshold": pack,
            "result": "PENDING",
            "deviation_percent": None,
            "values_for_eval": vals,
            "design_value": design_value,
        }
    if not vals:
        return {
            "matched": True,
            "threshold": pack,
            "result": "PENDING",
            "deviation_percent": None,
            "values_for_eval": [],
            "design_value": design_value,
        }

    mode = _to_text(pack.get("mode") or "absolute").strip().lower()
    eval_values = list(vals)
    if mode == "deviation_from_design" and design_value is not None:
        eval_values = [float(v) - float(design_value) for v in vals]

    raw_threshold = pack.get("threshold")
    operator = _to_text(pack.get("operator") or "range").strip().lower()
    result = "PENDING"
    deviation_percent: float | None = None
    lower: float | None = None
    upper: float | None = None
    center: float | None = None
    tolerance: float | None = None

    if isinstance(raw_threshold, (list, tuple)) and len(raw_threshold) >= 2:
        lo = _to_float(raw_threshold[0])
        hi = _to_float(raw_threshold[1])
        if lo is not None and hi is not None:
            lower, upper = min(lo, hi), max(lo, hi)
            center = round((lower + upper) / 2.0, 6)
            tolerance = round((upper - lower) / 2.0, 6)
            result = "PASS" if all(lower <= value <= upper for value in eval_values) else "FAIL"
            exceed = 0.0
            for value in eval_values:
                if value < lower:
                    exceed = max(exceed, lower - value)
                elif value > upper:
                    exceed = max(exceed, value - upper)
            base = max(abs(upper), abs(lower), 1.0)
            deviation_percent = round((exceed / base) * 100.0, 4)
    else:
        bound = _to_float(raw_threshold)
        if bound is not None:
            center = bound
            if operator in {"<=", "lt", "max"}:
                result = "PASS" if all(value <= bound for value in eval_values) else "FAIL"
                deviation_percent = round(((max(eval_values) - bound) / max(abs(bound), 1.0)) * 100.0, 4)
            elif operator in {">=", "gt", "min"}:
                result = "PASS" if all(value >= bound for value in eval_values) else "FAIL"
                deviation_percent = round(((bound - min(eval_values)) / max(abs(bound), 1.0)) * 100.0, 4)
            else:
                result = "PASS" if all(abs(value - bound) < 1e-9 for value in eval_values) else "FAIL"
                deviation_percent = round((abs(sum(eval_values) / len(eval_values) - bound) / max(abs(bound), 1.0)) * 100.0, 4)

    return {
        "matched": True,
        "threshold": pack,
        "result": result,
        "deviation_percent": deviation_percent,
        "values_for_eval": eval_values,
        "design_value": design_value,
        "lower": lower,
        "upper": upper,
        "center": center,
        "tolerance": tolerance,
    }
