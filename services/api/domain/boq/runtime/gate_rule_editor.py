"""
Gate rule editor service:
- Visual rule payload query
- Norm library import
- Natural language to rule conversion (ClawPeg simulated parser)
- Versioned save / rollback
- Batch apply to similar BOQ items
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from fastapi import HTTPException

from services.api.domain.boq.runtime.utxo import resolve_linked_gates
from services.api.core.norm.normpeg_engine import NormPegEngine, parse_norm_uri
from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.domain.boq.runtime.specdict_gate import (
    get_spec_dict,
    save_spec_dict,
    upsert_gate_binding,
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
        text = _to_text(value).strip().replace(",", "")
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
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _item_code_parts(item_code: str) -> list[str]:
    return [x.strip() for x in _to_text(item_code).split("-") if x.strip()]


def _is_leaf_row(row: dict[str, Any]) -> bool:
    sd = _as_dict(row.get("state_data"))
    if "is_leaf" in sd:
        return bool(sd.get("is_leaf"))
    tree = _as_dict(sd.get("hierarchy_tree"))
    if "is_leaf" in tree:
        return bool(tree.get("is_leaf"))
    children = _as_list(tree.get("children")) or _as_list(tree.get("children_codes"))
    return len(children) == 0


def _item_code_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    item_no = _to_text(sd.get("item_no") or "").strip()
    if item_no:
        return item_no
    boq_item_uri = _to_text(
        sd.get("boq_item_uri")
        or sd.get("item_uri")
        or sd.get("boq_uri")
        or row.get("segment_uri")
        or ""
    ).strip().rstrip("/")
    if boq_item_uri and "/" in boq_item_uri:
        return boq_item_uri.split("/")[-1]
    return ""


def _normalize_rules(raw_rules: Any) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for idx, item in enumerate(_as_list(raw_rules), start=1):
        row = _as_dict(item)
        if not row:
            continue
        threshold_raw = row.get("threshold")
        threshold_value = row.get("threshold_value")
        if threshold_value is None:
            threshold_value = threshold_raw
        rule = {
            "seq": idx,
            "inspection_item": _to_text(
                row.get("inspection_item") or row.get("metric") or row.get("name") or f"rule_{idx}"
            ).strip(),
            "operator": _to_text(row.get("operator") or "range").strip().lower(),
            "threshold": _to_text(threshold_raw if threshold_raw is not None else "").strip(),
            "threshold_value": threshold_value,
            "spec_uri": _to_text(row.get("spec_uri") or "").strip(),
            "context": _to_text(row.get("context") or row.get("context_key") or "").strip(),
            "unit": _to_text(row.get("unit") or "").strip(),
            "source": _to_text(row.get("source") or "").strip() or "manual",
        }
        rules.append(rule)
    return rules


def _version_key(version_text: str) -> tuple[int, int]:
    m = re.match(r"^v(\d+)\.(\d+)$", _to_text(version_text).strip().lower())
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def _next_version(history_rows: list[dict[str, Any]]) -> str:
    major = 1
    minor = -1
    for row in history_rows:
        sd = _as_dict(row.get("state_data"))
        v = _to_text(sd.get("version") or "").strip().lower()
        ma, mi = _version_key(v)
        if (ma, mi) > (major, minor):
            major, minor = ma, mi
    if minor < 0:
        return "v1.0"
    return f"v{major}.{minor + 1}"


def _derive_specdict_from_rules(
    *,
    subitem_code: str,
    gate_id_base: str,
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    first = _as_dict(rules[0]) if rules else {}
    first_spec_uri = _to_text(first.get("spec_uri") or "").strip()
    parsed = parse_norm_uri(first_spec_uri)
    code = _to_text(parsed.get("code") or "").strip()
    version = _to_text(parsed.get("version") or "").strip() or "v1.0"
    path = _to_text(parsed.get("path") or "").strip().replace("/", ".")
    if code:
        spec_dict_key = f"{code}-{version}-{path}" if path else f"{code}-{version}"
    else:
        sanitized_gate = re.sub(r"[^a-zA-Z0-9._-]+", "-", _to_text(gate_id_base or "").strip()).strip("-")
        spec_dict_key = sanitized_gate or f"CUSTOM-{_to_text(subitem_code).strip()}"
    spec_dict_key = spec_dict_key[:120]

    items: dict[str, Any] = {}
    default_item_key = ""
    for idx, row in enumerate(rules, start=1):
        rule = _as_dict(row)
        item_key = _to_text(
            rule.get("inspection_item")
            or parse_norm_uri(rule.get("spec_uri")).get("fragment")
            or f"rule_{idx}"
        ).strip()
        if not item_key:
            item_key = f"rule_{idx}"
        if not default_item_key:
            default_item_key = item_key
        item = items.setdefault(
            item_key,
            {
                "operator": _to_text(rule.get("operator") or "range").strip().lower(),
                "unit": _to_text(rule.get("unit") or "").strip(),
                "mode": "deviation_from_design" if _to_text(rule.get("operator") or "").strip().lower() == "range" else "absolute",
                "default_threshold": rule.get("threshold_value") if rule.get("threshold_value") is not None else rule.get("threshold"),
                "context_rules": {},
            },
        )
        context_key = _to_text(rule.get("context") or "").strip()
        threshold_value = rule.get("threshold_value")
        if threshold_value is None:
            threshold_value = rule.get("threshold")
        if context_key:
            item["context_rules"][context_key] = threshold_value
        elif item.get("default_threshold") in ("", None):
            item["default_threshold"] = threshold_value
    return {
        "spec_dict_key": spec_dict_key,
        "spec_item": default_item_key,
        "title": _to_text(code or "Custom SpecDict").strip() or "Custom SpecDict",
        "version": _to_text(version).strip() or "v1.0",
        "spec_uri": _to_text(parsed.get("base_uri") or first_spec_uri).strip(),
        "items": items,
    }


def _load_gate_rule_rows(
    *,
    sb: Any,
    project_uri: str,
    subitem_code: str,
    gate_id_base: str = "",
    limit: int = 500,
) -> list[dict[str, Any]]:
    normalized_project_uri = _to_text(project_uri).strip()
    normalized_code = _to_text(subitem_code).strip()
    if not normalized_project_uri or not normalized_code:
        return []
    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .eq("proof_type", "gate_rule")
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 2000)))
            .execute()
            .data
            or []
        )
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    expected_gate_base = _to_text(gate_id_base).strip()
    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("subitem_code") or "").strip() != normalized_code:
            continue
        if expected_gate_base and _to_text(sd.get("gate_id_base") or "").strip() != expected_gate_base:
            continue
        out.append(row)
    return out


def _serialize_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        history.append(
            {
                "proof_id": _to_text(row.get("proof_id") or "").strip(),
                "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                "gate_id": _to_text(sd.get("gate_id") or "").strip(),
                "gate_id_base": _to_text(sd.get("gate_id_base") or "").strip(),
                "version": _to_text(sd.get("version") or "").strip(),
                "execution_strategy": _to_text(sd.get("execution_strategy") or "").strip(),
                "fail_action": _to_text(sd.get("fail_action") or "").strip(),
                "rule_count": len(_as_list(sd.get("rules"))),
                "rule_pack_hash": _to_text(sd.get("rule_pack_hash") or "").strip(),
                "created_at": _to_text(row.get("created_at") or "").strip(),
                "author": _to_text(sd.get("executor_uri") or "").strip(),
            }
        )
    history.sort(key=lambda x: _version_key(_to_text(x.get("version") or "").strip()), reverse=True)
    return history


def import_from_norm_library(
    *,
    sb: Any,
    spec_uri: str,
    context: str = "",
) -> dict[str, Any]:
    normalized_spec_uri = _to_text(spec_uri).strip()
    if not normalized_spec_uri:
        raise HTTPException(400, "spec_uri is required")

    engine = NormPegEngine.from_sources(sb=sb)
    parsed = parse_norm_uri(normalized_spec_uri)
    target_base = _to_text(parsed.get("base_uri") or "").strip()
    entry = None
    for candidate in engine.entries:
        if _to_text(parse_norm_uri(candidate.uri).get("base_uri") or "").strip() == target_base:
            entry = candidate
            break

    if entry is None:
        threshold_pack = engine.get_threshold(normalized_spec_uri, {"context": context})
        return {
            "ok": bool(threshold_pack.get("found")),
            "spec_uri": normalized_spec_uri,
            "effective_spec_uri": _to_text(threshold_pack.get("effective_spec_uri") or normalized_spec_uri).strip(),
            "spec_excerpt": _to_text(threshold_pack.get("spec_excerpt") or "").strip(),
            "rules": [],
        }

    params = entry.params if isinstance(entry.params, dict) else {}
    if not params:
        return {
            "ok": True,
            "spec_uri": normalized_spec_uri,
            "effective_spec_uri": target_base or entry.uri,
            "spec_excerpt": _to_text(entry.content).strip(),
            "rules": [],
        }

    rules: list[dict[str, Any]] = []
    for idx, param_key in enumerate(params.keys(), start=1):
        threshold_pack = engine.get_threshold(f"{target_base}#{param_key}", {"context": context})
        threshold_value = threshold_pack.get("threshold")
        threshold_text = ""
        if isinstance(threshold_value, (list, tuple)):
            vals = [str(x) for x in threshold_value]
            threshold_text = "~".join(vals)
        elif threshold_value is not None:
            threshold_text = str(threshold_value)
        rules.append(
            {
                "seq": idx,
                "inspection_item": _to_text(param_key).strip(),
                "operator": _to_text(threshold_pack.get("operator") or "range").strip().lower(),
                "threshold": threshold_text,
                "threshold_value": threshold_value,
                "spec_uri": _to_text(threshold_pack.get("effective_spec_uri") or "").strip() or f"{target_base}#{param_key}",
                "context": _to_text(threshold_pack.get("context_key") or context).strip(),
                "unit": _to_text(threshold_pack.get("unit") or "").strip(),
                "source": "norm_library",
            }
        )

    return {
        "ok": True,
        "spec_uri": normalized_spec_uri,
        "effective_spec_uri": target_base or entry.uri,
        "spec_excerpt": _to_text(entry.content).strip(),
        "rules": rules,
    }


def generate_rules_via_ai(
    *,
    prompt: str,
    subitem_code: str = "",
) -> dict[str, Any]:
    text = _to_text(prompt).strip()
    if not text:
        raise HTTPException(400, "prompt is required")

    lower = text.lower()

    metric_map = [
        ("yield_strength", ("屈服", "yield", "yield_strength")),
        ("crack_width", ("裂缝", "crack", "crack_width")),
        ("spacing_tolerance", ("间距", "spacing", "spacing_tolerance")),
        ("diameter_tolerance", ("直径", "diameter", "diameter_tolerance")),
    ]
    metric = "custom_metric"
    for metric_key, keywords in metric_map:
        if any((k in text) or (k in lower) for k in keywords):
            metric = metric_key
            break

    context_alias = [
        ("主梁", ("主梁", "main_beam")),
        ("桥墩", ("桥墩", "pier")),
        ("护栏", ("护栏", "guardrail")),
        ("梁板", ("梁板", "slab", "beam")),
    ]
    context = ""
    for context_key, keywords in context_alias:
        if any((k in text) or (k in lower) for k in keywords):
            context = context_key
            break

    operator = "range"
    if any(x in text for x in ("不低于", "不少于", "大于等于")) or ">=" in text:
        operator = ">="
    elif any(x in text for x in ("不高于", "不大于", "小于等于")) or "<=" in text:
        operator = "<="
    elif any(x in text for x in ("小于", "低于")) or "<" in text:
        operator = "<"
    elif any(x in text for x in ("大于", "高于")) or ">" in text:
        operator = ">"

    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    threshold_value: Any = None
    threshold_text = ""
    if len(numbers) >= 2 and any(x in text for x in ("~", "到", "-", "至", "between")) and operator == "range":
        lo = float(numbers[0])
        hi = float(numbers[1])
        threshold_value = [min(lo, hi), max(lo, hi)]
        threshold_text = f"{min(lo, hi)}~{max(lo, hi)}"
    elif numbers:
        threshold_value = float(numbers[0])
        threshold_text = str(threshold_value)

    unit = ""
    if "mpa" in lower:
        unit = "MPa"
    elif "cm" in lower:
        unit = "cm"
    elif "mm" in lower:
        unit = "mm"

    spec_uri = ""
    if metric == "yield_strength":
        spec_uri = "v://norm/GB50204@2015/5.3.2#diameter_tolerance"
    elif metric == "crack_width":
        spec_uri = "v://norm/JTG_F80@2017/4.3#crack_width_max"
    elif metric == "spacing_tolerance":
        spec_uri = "v://norm/GB50204@2015/5.3.3#spacing_tolerance"
    elif metric == "diameter_tolerance":
        spec_uri = "v://norm/GB50204@2015/5.3.2#diameter_tolerance"

    rule = {
        "seq": 1,
        "inspection_item": metric,
        "operator": operator,
        "threshold": threshold_text or "pending",
        "threshold_value": threshold_value,
        "spec_uri": spec_uri,
        "context": context,
        "unit": unit,
        "source": "clawpeg_ai",
        "nl_prompt": text,
    }
    confidence = 0.62
    if threshold_value is not None:
        confidence += 0.2
    if context:
        confidence += 0.08
    if spec_uri:
        confidence += 0.08

    return {
        "ok": True,
        "subitem_code": _to_text(subitem_code).strip(),
        "engine": "ClawPeg-Simulated-v1",
        "confidence": round(min(confidence, 0.99), 2),
        "rules": [rule],
    }


def apply_to_all_similar_items(
    *,
    sb: Any,
    project_uri: str,
    subitem_code: str,
    gate_pack: dict[str, Any],
    apply_to_similar: bool,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    normalized_code = _to_text(subitem_code).strip()
    if not normalized_project_uri or not normalized_code:
        raise HTTPException(400, "project_uri and subitem_code are required")

    parts = _item_code_parts(normalized_code)
    similar_prefix = "-".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else normalized_code)

    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .eq("spent", False)
            .order("created_at", desc=False)
            .limit(20000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to query proof_utxo for batch apply: {exc}") from exc

    applied: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_leaf_row(row):
            continue
        item_code = _item_code_from_row(row)
        if not item_code:
            continue
        if apply_to_similar:
            if not (item_code == normalized_code or item_code.startswith(f"{similar_prefix}-")):
                continue
        else:
            if item_code != normalized_code:
                continue

        proof_id = _to_text(row.get("proof_id") or "").strip()
        if not proof_id:
            continue
        sd = dict(_as_dict(row.get("state_data")))
        linked_rules = _normalize_rules(gate_pack.get("rules"))
        linked_ids = [_to_text(gate_pack.get("gate_id") or "").strip()]
        linked_ids.extend(
            [_to_text(x).strip() for x in _as_list(sd.get("linked_gate_ids")) if _to_text(x).strip()]
        )
        dedup_ids: list[str] = []
        seen: set[str] = set()
        for gid in linked_ids:
            if gid and gid not in seen:
                dedup_ids.append(gid)
                seen.add(gid)

        sd.update(
            {
                "linked_gate_id": _to_text(gate_pack.get("gate_id") or "").strip(),
                "linked_gate_ids": dedup_ids,
                "linked_gate_rules": linked_rules,
                "linked_spec_uri": _to_text(
                    gate_pack.get("linked_spec_uri")
                    or (_as_dict(linked_rules[0]).get("spec_uri") if linked_rules else "")
                    or ""
                ).strip(),
                "gate_template_lock": True,
                "gate_id_base": _to_text(gate_pack.get("gate_id_base") or "").strip(),
                "gate_version": _to_text(gate_pack.get("version") or "").strip(),
                "gate_rule_proof_id": _to_text(gate_pack.get("proof_id") or "").strip(),
                "gate_rule_pack_hash": _to_text(gate_pack.get("rule_pack_hash") or "").strip(),
                "spec_dict_key": _to_text(gate_pack.get("spec_dict_key") or "").strip(),
                "spec_item": _to_text(gate_pack.get("spec_item") or "").strip(),
                "gate_rule_applied_at": _utc_iso(),
            }
        )
        try:
            sb.table("proof_utxo").update({"state_data": sd}).eq("proof_id", proof_id).execute()
            if _to_text(gate_pack.get("spec_dict_key") or "").strip():
                try:
                    upsert_gate_binding(
                        sb=sb,
                        gate_id=_to_text(gate_pack.get("gate_id") or "").strip(),
                        gate_id_base=_to_text(gate_pack.get("gate_id_base") or "").strip(),
                        subitem_code=item_code,
                        spec_dict_key=_to_text(gate_pack.get("spec_dict_key") or "").strip(),
                        spec_item=_to_text(gate_pack.get("spec_item") or "").strip(),
                        execution_strategy=_to_text(gate_pack.get("execution_strategy") or "all_pass").strip(),
                        fail_action=_to_text(gate_pack.get("fail_action") or "trigger_review_trip").strip(),
                        gate_rules=linked_rules,
                        metadata={"source": "apply_to_all_similar_items"},
                        is_active=True,
                    )
                except Exception:
                    pass
            applied.append(
                {
                    "proof_id": proof_id,
                    "item_code": item_code,
                    "boq_item_uri": _to_text(sd.get("boq_item_uri") or "").strip(),
                }
            )
        except Exception as exc:
            failed.append({"proof_id": proof_id, "item_code": item_code, "error": f"{exc.__class__.__name__}: {exc}"})

    return {
        "ok": len(failed) == 0,
        "apply_to_similar": bool(apply_to_similar),
        "similar_prefix": similar_prefix,
        "applied_count": len(applied),
        "failed_count": len(failed),
        "applied": applied,
        "failed": failed,
    }


def save_gate_rule_version(
    *,
    sb: Any,
    project_uri: str,
    subitem_code: str,
    gate_id_base: str = "",
    rules: list[dict[str, Any]] | None = None,
    execution_strategy: str = "all_pass",
    fail_action: str = "trigger_review_trip",
    apply_to_similar: bool = False,
    executor_uri: str = "v://executor/chief-engineer/",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    normalized_code = _to_text(subitem_code).strip()
    if not normalized_project_uri or not normalized_code:
        raise HTTPException(400, "project_uri and subitem_code are required")

    normalized_rules = _normalize_rules(rules or [])
    if not normalized_rules:
        raise HTTPException(400, "rules are required")

    inferred_gate = resolve_linked_gates(item_code=normalized_code, fallback_spec_uri="", sb=sb)
    default_gate_base = _to_text(inferred_gate.get("linked_gate_id") or "").strip() or f"QCGate::{normalized_code}::custom"
    normalized_gate_base = _to_text(gate_id_base).strip() or default_gate_base
    if "@v" in normalized_gate_base.lower():
        normalized_gate_base = normalized_gate_base.split("@", 1)[0]

    specdict_payload = _derive_specdict_from_rules(
        subitem_code=normalized_code,
        gate_id_base=normalized_gate_base,
        rules=normalized_rules,
    )
    try:
        saved_specdict = save_spec_dict(
            sb=sb,
            spec_dict_key=_to_text(specdict_payload.get("spec_dict_key") or "").strip(),
            title=_to_text(specdict_payload.get("title") or "").strip(),
            version=_to_text(specdict_payload.get("version") or "").strip() or "v1.0",
            authority=_to_text(specdict_payload.get("title") or "").strip(),
            spec_uri=_to_text(specdict_payload.get("spec_uri") or "").strip(),
            items=_as_dict(specdict_payload.get("items")),
            metadata={"source": "gate_rule_editor", "subitem_code": normalized_code},
            is_active=True,
        )
    except Exception:
        saved_specdict = {
            "ok": False,
            "spec_dict_key": _to_text(specdict_payload.get("spec_dict_key") or "").strip(),
        }

    history_rows = _load_gate_rule_rows(
        sb=sb,
        project_uri=normalized_project_uri,
        subitem_code=normalized_code,
        gate_id_base=normalized_gate_base,
    )
    version = _next_version(history_rows)
    gate_id = f"{normalized_gate_base}@{version}"
    now_iso = _utc_iso()
    pack_canonical = {
        "project_uri": normalized_project_uri,
        "subitem_code": normalized_code,
        "gate_id": gate_id,
        "gate_id_base": normalized_gate_base,
        "version": version,
        "rules": normalized_rules,
        "execution_strategy": _to_text(execution_strategy).strip() or "all_pass",
        "fail_action": _to_text(fail_action).strip() or "trigger_review_trip",
        "spec_dict_key": _to_text(saved_specdict.get("spec_dict_key") or "").strip(),
        "spec_item": _to_text(specdict_payload.get("spec_item") or "").strip(),
        "saved_at": now_iso,
    }
    rule_pack_hash = _sha256_json(pack_canonical)
    proof_id = f"GP-GATE-{rule_pack_hash[:16].upper()}"

    engine = ProofUTXOEngine(sb)
    state_data = {
        "asset_type": "gate_rule",
        "status": "ACTIVE",
        "subitem_code": normalized_code,
        "gate_id": gate_id,
        "gate_id_base": normalized_gate_base,
        "version": version,
        "rules": normalized_rules,
        "execution_strategy": _to_text(execution_strategy).strip() or "all_pass",
        "fail_action": _to_text(fail_action).strip() or "trigger_review_trip",
        "spec_dict_key": _to_text(saved_specdict.get("spec_dict_key") or "").strip(),
        "spec_item": _to_text(specdict_payload.get("spec_item") or "").strip(),
        "rule_pack_hash": rule_pack_hash,
        "executor_uri": _to_text(executor_uri).strip(),
        "saved_at": now_iso,
        "metadata": _as_dict(metadata),
    }
    segment_uri = f"{normalized_project_uri.rstrip('/')}/boq/{normalized_code}"
    norm_uri = _to_text(_as_dict(normalized_rules[0]).get("spec_uri") or "").strip() or None

    try:
        rule_row = engine.create(
            proof_id=proof_id,
            owner_uri=_to_text(executor_uri).strip() or "v://executor/chief-engineer/",
            project_uri=normalized_project_uri,
            project_id=None,
            proof_type="gate_rule",
            result="PASS",
            state_data=state_data,
            conditions=[],
            parent_proof_id=None,
            norm_uri=norm_uri,
            segment_uri=segment_uri,
            signer_uri=_to_text(executor_uri).strip() or "v://executor/chief-engineer/",
            signer_role="ENGINEER",
            gitpeg_anchor=None,
            anchor_config=None,
        )
    except Exception:
        fallback_id = f"{proof_id}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
        rule_row = engine.create(
            proof_id=fallback_id,
            owner_uri=_to_text(executor_uri).strip() or "v://executor/chief-engineer/",
            project_uri=normalized_project_uri,
            project_id=None,
            proof_type="gate_rule",
            result="PASS",
            state_data=state_data,
            conditions=[],
            parent_proof_id=None,
            norm_uri=norm_uri,
            segment_uri=segment_uri,
            signer_uri=_to_text(executor_uri).strip() or "v://executor/chief-engineer/",
            signer_role="ENGINEER",
            gitpeg_anchor=None,
            anchor_config=None,
        )
    actual_proof_id = _to_text(rule_row.get("proof_id") or proof_id).strip()
    state_data["proof_id"] = actual_proof_id
    try:
        if _to_text(saved_specdict.get("spec_dict_key") or "").strip():
            upsert_gate_binding(
                sb=sb,
                gate_id=gate_id,
                gate_id_base=normalized_gate_base,
                subitem_code=normalized_code,
                spec_dict_key=_to_text(saved_specdict.get("spec_dict_key") or "").strip(),
                spec_item=_to_text(specdict_payload.get("spec_item") or "").strip(),
                execution_strategy=_to_text(execution_strategy).strip() or "all_pass",
                fail_action=_to_text(fail_action).strip() or "trigger_review_trip",
                gate_rules=normalized_rules,
                metadata={"source": "save_gate_rule_version", "proof_id": actual_proof_id},
                is_active=True,
            )
    except Exception:
        pass

    batch_apply = apply_to_all_similar_items(
        sb=sb,
        project_uri=normalized_project_uri,
        subitem_code=normalized_code,
        gate_pack={
            "proof_id": actual_proof_id,
            "gate_id": gate_id,
            "gate_id_base": normalized_gate_base,
            "version": version,
            "rules": normalized_rules,
            "linked_spec_uri": _to_text(_as_dict(normalized_rules[0]).get("spec_uri") or "").strip(),
            "rule_pack_hash": rule_pack_hash,
            "spec_dict_key": _to_text(saved_specdict.get("spec_dict_key") or "").strip(),
            "spec_item": _to_text(specdict_payload.get("spec_item") or "").strip(),
            "execution_strategy": _to_text(execution_strategy).strip() or "all_pass",
            "fail_action": _to_text(fail_action).strip() or "trigger_review_trip",
        },
        apply_to_similar=bool(apply_to_similar),
    )

    latest_history = _serialize_history(
        _load_gate_rule_rows(
            sb=sb,
            project_uri=normalized_project_uri,
            subitem_code=normalized_code,
            gate_id_base=normalized_gate_base,
        )
    )
    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "subitem_code": normalized_code,
        "gate_id": gate_id,
        "gate_id_base": normalized_gate_base,
        "version": version,
        "proof_id": actual_proof_id,
        "proof_hash": _to_text(rule_row.get("proof_hash") or "").strip(),
        "rule_pack_hash": rule_pack_hash,
        "execution_strategy": _to_text(execution_strategy).strip() or "all_pass",
        "fail_action": _to_text(fail_action).strip() or "trigger_review_trip",
        "spec_dict_key": _to_text(saved_specdict.get("spec_dict_key") or "").strip(),
        "spec_item": _to_text(specdict_payload.get("spec_item") or "").strip(),
        "batch_apply": batch_apply,
        "history": latest_history,
    }


def rollback_gate_rule(
    *,
    sb: Any,
    project_uri: str,
    subitem_code: str,
    target_proof_id: str = "",
    target_version: str = "",
    apply_to_similar: bool = True,
    executor_uri: str = "v://executor/chief-engineer/",
) -> dict[str, Any]:
    rows = _load_gate_rule_rows(
        sb=sb,
        project_uri=project_uri,
        subitem_code=subitem_code,
    )
    if not rows:
        raise HTTPException(404, "no gate rule version history found")
    selected: dict[str, Any] | None = None
    normalized_target_pid = _to_text(target_proof_id).strip()
    normalized_target_version = _to_text(target_version).strip().lower()
    for row in rows:
        pid = _to_text(row.get("proof_id") or "").strip()
        ver = _to_text(_as_dict(row.get("state_data")).get("version") or "").strip().lower()
        if normalized_target_pid and pid == normalized_target_pid:
            selected = row
            break
        if (not normalized_target_pid) and normalized_target_version and ver == normalized_target_version:
            selected = row
            break
    if selected is None:
        selected = rows[0]

    selected_sd = _as_dict(selected.get("state_data"))
    save_result = save_gate_rule_version(
        sb=sb,
        project_uri=_to_text(project_uri).strip(),
        subitem_code=_to_text(subitem_code).strip(),
        gate_id_base=_to_text(selected_sd.get("gate_id_base") or "").strip(),
        rules=_as_list(selected_sd.get("rules")),
        execution_strategy=_to_text(selected_sd.get("execution_strategy") or "all_pass").strip(),
        fail_action=_to_text(selected_sd.get("fail_action") or "trigger_review_trip").strip(),
        apply_to_similar=bool(apply_to_similar),
        executor_uri=_to_text(executor_uri).strip() or "v://executor/chief-engineer/",
        metadata={
            "rollback_from_proof_id": _to_text(selected.get("proof_id") or "").strip(),
            "rollback_from_version": _to_text(selected_sd.get("version") or "").strip(),
        },
    )
    save_result["rollback"] = {
        "source_proof_id": _to_text(selected.get("proof_id") or "").strip(),
        "source_version": _to_text(selected_sd.get("version") or "").strip(),
    }
    return save_result


def get_gate_editor_payload(
    *,
    sb: Any,
    project_uri: str,
    subitem_code: str,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    normalized_code = _to_text(subitem_code).strip()
    if not normalized_project_uri or not normalized_code:
        raise HTTPException(400, "project_uri and subitem_code are required")

    history_rows = _load_gate_rule_rows(
        sb=sb,
        project_uri=normalized_project_uri,
        subitem_code=normalized_code,
    )
    history = _serialize_history(history_rows)
    latest_row = history_rows[0] if history_rows else {}
    latest_sd = _as_dict(_as_dict(latest_row).get("state_data"))

    default_binding = resolve_linked_gates(item_code=normalized_code, fallback_spec_uri="", sb=sb)
    base_rules = _normalize_rules(latest_sd.get("rules"))
    if not base_rules:
        base_rules = _normalize_rules(_as_list(default_binding.get("linked_gate_rules")))

    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .eq("spent", False)
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []
    live_binding = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _item_code_from_row(row) != normalized_code:
            continue
        sd = _as_dict(row.get("state_data"))
        live_binding = {
            "proof_id": _to_text(row.get("proof_id") or "").strip(),
            "linked_gate_id": _to_text(sd.get("linked_gate_id") or "").strip(),
            "linked_gate_ids": _as_list(sd.get("linked_gate_ids")),
            "linked_spec_uri": _to_text(sd.get("linked_spec_uri") or "").strip(),
            "spec_dict_key": _to_text(sd.get("spec_dict_key") or "").strip(),
            "spec_item": _to_text(sd.get("spec_item") or "").strip(),
            "gate_version": _to_text(sd.get("gate_version") or "").strip(),
            "gate_rule_proof_id": _to_text(sd.get("gate_rule_proof_id") or "").strip(),
            "gate_rule_pack_hash": _to_text(sd.get("gate_rule_pack_hash") or "").strip(),
        }
        break

    spec_dict_key = _to_text(
        latest_sd.get("spec_dict_key")
        or live_binding.get("spec_dict_key")
        or default_binding.get("spec_dict_key")
        or ""
    ).strip()
    spec_dict_payload = get_spec_dict(sb=sb, spec_dict_key=spec_dict_key) if spec_dict_key else {"ok": False}

    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "subitem_code": normalized_code,
        "gate_id_base": _to_text(latest_sd.get("gate_id_base") or default_binding.get("linked_gate_id") or "").strip(),
        "gate_id": _to_text(latest_sd.get("gate_id") or default_binding.get("linked_gate_id") or "").strip(),
        "version": _to_text(latest_sd.get("version") or "v1.0").strip(),
        "execution_strategy": _to_text(latest_sd.get("execution_strategy") or "all_pass").strip(),
        "fail_action": _to_text(latest_sd.get("fail_action") or "trigger_review_trip").strip(),
        "spec_dict_key": spec_dict_key,
        "spec_item": _to_text(latest_sd.get("spec_item") or live_binding.get("spec_item") or default_binding.get("spec_item") or "").strip(),
        "spec_dict": spec_dict_payload,
        "rules": base_rules,
        "live_binding": live_binding,
        "history": history,
    }



