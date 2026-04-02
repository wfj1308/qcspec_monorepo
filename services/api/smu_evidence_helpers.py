"""Evidence and gate data helper functions for SMU orchestration."""

from __future__ import annotations

from typing import Any, Callable

from services.api.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_float as _to_float,
    to_text as _to_text,
)


def resolve_boq_balance(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    get_boq_realtime_status: Callable[..., dict[str, Any]],
) -> dict[str, float]:
    status = _as_dict(get_boq_realtime_status(sb=sb, project_uri=project_uri, limit=10000))
    items = _as_list(status.get("items"))
    item = next((x for x in items if _to_text(_as_dict(x).get("boq_item_uri")).strip() == boq_item_uri), None)
    if not isinstance(item, dict):
        return {"baseline": 0.0, "settled": 0.0}
    approved_qty = _to_float(item.get("approved_quantity"))
    contract_qty = _to_float(item.get("contract_quantity"))
    design_qty = _to_float(item.get("design_quantity"))
    baseline = approved_qty if approved_qty is not None and approved_qty > 0 else (
        contract_qty if contract_qty is not None and contract_qty > 0 else (design_qty or 0.0)
    )
    settled = _to_float(item.get("settled_quantity")) or 0.0
    return {"baseline": float(baseline), "settled": float(settled)}


def resolve_lab_pass_for_sample(*, sb: Any, project_uri: str, boq_item_uri: str, sample_id: str) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    b_uri = _to_text(boq_item_uri).strip().rstrip("/")
    sample = _to_text(sample_id).strip()
    if not p_uri or not b_uri or not sample:
        return {"ok": False, "pass": 0, "total": 0}
    try:
        rows = (
            sb.table("proof_utxo")
            .select("proof_id, result, proof_type, state_data, segment_uri, created_at")
            .eq("project_uri", p_uri)
            .eq("proof_type", "lab")
            .order("created_at", desc=False)
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        return {"ok": False, "pass": 0, "total": 0, "error": f"{exc.__class__.__name__}"}
    matched: list[dict[str, Any]] = []
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        uri = _to_text(sd.get("boq_item_uri") or row.get("segment_uri") or "").strip().rstrip("/")
        if uri != b_uri:
            continue
        if _to_text(sd.get("sample_id") or "").strip() != sample:
            continue
        matched.append(row)
    if not matched:
        return {"ok": True, "pass": 0, "total": 0}
    lab_pass = [x for x in matched if _to_text(x.get("result") or "").strip().upper() == "PASS"]
    latest_pass = lab_pass[-1] if lab_pass else None
    return {
        "ok": True,
        "pass": len(lab_pass),
        "total": len(matched),
        "latest_pass_proof_id": _to_text((latest_pass or {}).get("proof_id") or "").strip(),
    }


def verify_conservation(*, baseline: float, settled: float, claim: float) -> dict[str, Any]:
    baseline_val = float(baseline or 0.0)
    settled_val = float(settled or 0.0)
    claim_val = float(claim or 0.0)
    total = settled_val + claim_val
    if baseline_val <= 0:
        return {"ok": True, "gap_ratio": 0.0, "total": total, "baseline": baseline_val}
    gap_ratio = abs(total - baseline_val) / baseline_val
    gap_ratio = round(gap_ratio, 4)
    ok = total <= baseline_val + 1e-9
    return {"ok": ok, "gap_ratio": gap_ratio, "total": total, "baseline": baseline_val}


def resolve_lab_status(*, sb: Any, project_uri: str, boq_item_uri: str) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    b_uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not p_uri or not b_uri:
        return {"ok": False, "status": "MISSING", "total": 0, "pass": 0}
    try:
        rows = (
            sb.table("proof_utxo")
            .select("proof_id, result, proof_type, state_data, segment_uri, created_at")
            .eq("project_uri", p_uri)
            .eq("proof_type", "lab")
            .order("created_at", desc=False)
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        return {"ok": False, "status": "UNAVAILABLE", "total": 0, "pass": 0, "error": f"{exc.__class__.__name__}"}

    matched: list[dict[str, Any]] = []
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        uri = _to_text(sd.get("boq_item_uri") or row.get("segment_uri") or "").strip().rstrip("/")
        if uri == b_uri:
            matched.append(row)

    if not matched:
        return {"ok": True, "status": "MISSING", "total": 0, "pass": 0}

    lab_pass = [x for x in matched if _to_text(x.get("result") or "").strip().upper() == "PASS"]
    latest = matched[-1]
    latest_pass = lab_pass[-1] if lab_pass else None
    status = "PASS" if lab_pass else "FAIL"
    return {
        "ok": True,
        "status": status,
        "total": len(matched),
        "pass": len(lab_pass),
        "latest_proof_id": _to_text((latest or {}).get("proof_id") or "").strip(),
        "latest_pass_proof_id": _to_text((latest_pass or {}).get("proof_id") or "").strip(),
    }


__all__ = [
    "resolve_boq_balance",
    "resolve_lab_pass_for_sample",
    "resolve_lab_status",
    "verify_conservation",
]
