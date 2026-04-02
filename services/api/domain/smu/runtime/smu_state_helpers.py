"""State-domain helper functions for SMU freeze and qualification logic."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_float as _to_float,
    to_text as _to_text,
)


def smu_id_from_item_code(item_code: str) -> str:
    token = _to_text(item_code).strip().rstrip("/").split("/")[-1]
    if "-" in token:
        return token.split("-")[0]
    return token


def is_smu_frozen(*, sb: Any, project_uri: str, smu_id: str) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    s_id = _to_text(smu_id).strip()
    if not p_uri or not s_id:
        return {"frozen": False}
    try:
        rows = (
            sb.table("proof_utxo")
            .select("proof_id,result,created_at,state_data")
            .eq("project_uri", p_uri)
            .eq("proof_type", "smu_freeze")
            .filter("state_data->>smu_id", "eq", s_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
            .data
            or []
        )
    except Exception:
        return {"frozen": False}
    latest = rows[0] if rows else {}
    if not latest:
        return {"frozen": False}
    status = _to_text(latest.get("result") or "").strip().upper()
    is_frozen_state = status == "PASS"
    return {
        "frozen": is_frozen_state,
        "proof_id": _to_text(latest.get("proof_id") or "").strip(),
        "created_at": _to_text(latest.get("created_at") or "").strip(),
    }


def resolve_smu_leaf_items(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
    get_boq_realtime_status: Callable[..., dict[str, Any]],
) -> list[dict[str, Any]]:
    s_id = _to_text(smu_id).strip()
    if not s_id:
        return []
    status = _as_dict(get_boq_realtime_status(sb=sb, project_uri=project_uri, limit=10000))
    out: list[dict[str, Any]] = []
    for item in _as_list(status.get("items")):
        row = _as_dict(item)
        item_no = _to_text(row.get("item_no") or "").strip()
        if not item_no or not item_no.startswith(s_id):
            continue
        if not _to_text(row.get("boq_item_uri") or "").strip():
            continue
        out.append(row)
    return out


def collect_smu_qualification(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
    get_boq_realtime_status: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    items = resolve_smu_leaf_items(
        sb=sb,
        project_uri=project_uri,
        smu_id=smu_id,
        get_boq_realtime_status=get_boq_realtime_status,
    )
    total = len(items)
    qualified = 0
    incomplete: list[dict[str, Any]] = []
    for row in items:
        settlement_count = int(_to_float(row.get("settlement_count")) or 0)
        latest_settlement = _to_text(row.get("latest_settlement_proof_id") or "").strip()
        if settlement_count > 0 and latest_settlement:
            qualified += 1
            continue
        incomplete.append(
            {
                "item_no": _to_text(row.get("item_no") or "").strip(),
                "boq_item_uri": _to_text(row.get("boq_item_uri") or "").strip(),
                "settlement_count": settlement_count,
                "latest_settlement_proof_id": latest_settlement,
            }
        )
    all_qualified = total > 0 and qualified == total
    return {
        "smu_id": _to_text(smu_id).strip(),
        "leaf_total": total,
        "qualified_leaf_count": qualified,
        "unqualified_leaf_count": max(0, total - qualified),
        "all_qualified": all_qualified,
        "pending_items": incomplete[:200],
    }


def mark_smu_scope_immutable(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
    freeze_proof_id: str,
    total_proof_hash: str,
    boq_rows: Callable[..., list[dict[str, Any]]],
    utc_iso: Callable[[], str],
) -> dict[str, Any]:
    rows = boq_rows(sb, project_uri=project_uri, boq_item_uri="", only_unspent=False, limit=50000)
    touched = 0
    skipped = 0
    now = _to_text(utc_iso() or "").strip()
    for row in rows:
        seg = _to_text(row.get("segment_uri") or "").strip()
        if "/boq/" not in seg:
            continue
        item_code = seg.rstrip("/").split("/")[-1]
        if not item_code.startswith(smu_id):
            continue
        sd = _as_dict(row.get("state_data"))
        freeze_meta = _as_dict(sd.get("smu_freeze"))
        if bool(freeze_meta.get("immutable")):
            skipped += 1
            continue
        freeze_meta.update(
            {
                "immutable": True,
                "frozen_at": now,
                "freeze_proof_id": freeze_proof_id,
                "smu_id": smu_id,
                "total_proof_hash": total_proof_hash,
            }
        )
        sd["immutable"] = True
        sd["immutable_at"] = now
        sd["smu_freeze"] = freeze_meta
        pid = _to_text(row.get("proof_id") or "").strip()
        if pid:
            sb.table("proof_utxo").update({"state_data": sd}).eq("proof_id", pid).execute()
            touched += 1
    return {"touched": touched, "skipped": skipped}


__all__ = [
    "collect_smu_qualification",
    "is_smu_frozen",
    "mark_smu_scope_immutable",
    "resolve_smu_leaf_items",
    "smu_id_from_item_code",
]

