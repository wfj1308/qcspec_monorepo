"""
SpecDict evolution helpers.
services/api/specdict_evolution_service.py
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import hashlib
import json
import re
from typing import Any

from services.api.specdict_gate_service import get_spec_dict, save_spec_dict


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


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _hash_project_uri(uri: str) -> str:
    return hashlib.sha256(_to_text(uri).strip().encode("utf-8")).hexdigest()[:12]


def _extract_values(sd: dict[str, Any]) -> list[float]:
    values: list[float] = []
    norm_eval = _as_dict(sd.get("norm_evaluation"))
    for v in _as_list(norm_eval.get("values_for_eval")):
        f = _to_float(v)
        if f is not None:
            values.append(float(f))
    if not values:
        payload = _as_dict(sd.get("quality_payload"))
        for key in ("measured_value", "value", "measured", "quantity"):
            f = _to_float(payload.get(key))
            if f is not None:
                values.append(float(f))
                break
    return values


def analyze_specdict_evolution(
    *,
    sb: Any,
    project_uris: list[str],
    min_samples: int = 5,
) -> dict[str, Any]:
    uris = [u for u in (_to_text(x).strip() for x in project_uris) if u]
    rows = []
    try:
        q = sb.table("proof_utxo").select("proof_id,project_uri,proof_type,result,state_data,created_at").order("created_at", desc=False)
        if uris:
            q = q.in_("project_uri", uris)
        rows = q.limit(60000).execute().data or []
    except Exception:
        rows = []

    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"pass": 0, "fail": 0, "values": []})
    for row in rows:
        if not isinstance(row, dict):
            continue
        ptype = _to_text(row.get("proof_type") or "").strip().lower()
        if ptype not in {"inspection", "lab"}:
            continue
        result = _to_text(row.get("result") or "").strip().upper()
        sd = _as_dict(row.get("state_data"))
        key = _to_text(sd.get("spec_dict_key") or "").strip()
        if not key:
            continue
        spec_item = _to_text(sd.get("spec_item") or "").strip()
        bucket_key = f"{key}#{spec_item}" if spec_item else key
        if result == "PASS":
            buckets[bucket_key]["pass"] += 1
        elif result == "FAIL":
            buckets[bucket_key]["fail"] += 1
        buckets[bucket_key]["values"].extend(_extract_values(sd))

    items: list[dict[str, Any]] = []
    high_risk: list[dict[str, Any]] = []
    best_practice: list[dict[str, Any]] = []

    for k, v in buckets.items():
        total = int(v["pass"] + v["fail"])
        if total < max(1, min_samples):
            continue
        pass_rate = (v["pass"] / total) if total else 0.0
        fail_rate = (v["fail"] / total) if total else 0.0
        values = v.get("values") or []
        avg_value = sum(values) / len(values) if values else None
        item = {
            "spec_key": k,
            "total": total,
            "pass": v["pass"],
            "fail": v["fail"],
            "pass_rate": round(pass_rate, 4),
            "fail_rate": round(fail_rate, 4),
            "avg_value": round(avg_value, 4) if avg_value is not None else None,
        }
        items.append(item)
        if fail_rate >= 0.2 and v["fail"] >= 2:
            high_risk.append(item)
        if pass_rate >= 0.95 and v["pass"] >= max(3, min_samples // 2):
            best_practice.append(item)

    return {
        "ok": True,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "project_uris": uris,
        "total_rules": len(items),
        "high_risk": high_risk[:200],
        "best_practice": best_practice[:200],
        "items": items,
    }


def export_specdict_bundle(
    *,
    sb: Any,
    project_uris: list[str],
    min_samples: int = 5,
    namespace_uri: str = "v://global/templates",
    commit: bool = False,
) -> dict[str, Any]:
    analysis = analyze_specdict_evolution(sb=sb, project_uris=project_uris, min_samples=min_samples)
    keys = [x.get("spec_key") for x in (analysis.get("items") or []) if _to_text(x.get("spec_key"))]
    spec_dicts: list[dict[str, Any]] = []
    for key in keys:
        spec_key = _to_text(key).split("#")[0]
        if not spec_key:
            continue
        sd = get_spec_dict(sb=sb, spec_dict_key=spec_key)
        if not sd.get("ok"):
            continue
        items = _as_dict(sd.get("items"))
        meta = _as_dict(sd.get("metadata"))
        meta["anonymized_from"] = [_hash_project_uri(u) for u in project_uris]
        meta["source_namespace"] = namespace_uri
        meta["evolution_summary"] = {
            "total_rules": analysis.get("total_rules"),
            "generated_at": analysis.get("generated_at"),
        }
        payload = {
            "spec_dict_key": f"global-{spec_key}",
            "title": _to_text(sd.get("title") or spec_key),
            "version": _to_text(sd.get("version") or "v1.0"),
            "authority": _to_text(sd.get("authority") or "") or "CoordOS",
            "spec_uri": f"{namespace_uri}/{spec_key}",
            "items": items,
            "metadata": meta,
            "is_active": True,
        }
        if commit:
            saved = save_spec_dict(
                sb=sb,
                spec_dict_key=payload["spec_dict_key"],
                title=payload["title"],
                version=payload["version"],
                authority=payload["authority"],
                spec_uri=payload["spec_uri"],
                items=payload["items"],
                metadata=payload["metadata"],
                is_active=True,
            )
            spec_dicts.append(saved)
        else:
            spec_dicts.append(payload)

    return {
        "ok": True,
        "analysis": analysis,
        "spec_dicts": spec_dicts,
        "commit": commit,
        "namespace_uri": namespace_uri,
    }
