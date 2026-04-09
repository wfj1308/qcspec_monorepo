"""Material inspection-batch UTXO runtime."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from services.api.domain.boqpeg.models import (
    InspectionBatchResult,
    MaterialUTXO,
    MaterialUTXOQueryResult,
)
from services.api.domain.utxo.integrations import ProofUTXOEngine


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _safe_uri_token(value: str) -> str:
    text = _to_text(value).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "na"


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _fetch_proof_rows(*, sb: Any, proof_type: str = "inspection") -> list[dict[str, Any]]:
    if sb is None:
        return []
    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("proof_type", proof_type)
        .order("created_at", desc=False)
        .limit(50000)
        .execute()
        .data
        or []
    )
    return [row for row in rows if isinstance(row, dict)]


def _parse_result(value: Any) -> str:
    token = _to_text(value).strip().lower()
    if token in {"approved", "rejected", "pending"}:
        return token
    if token in {"pass", "passed", "ok"}:
        return "approved"
    if token in {"fail", "failed", "error"}:
        return "rejected"
    return "pending"


def _proof_result(value: str) -> str:
    token = _parse_result(value)
    if token == "approved":
        return "PASS"
    if token == "rejected":
        return "FAIL"
    return "PENDING"


def _utxo_status_from_result(value: str) -> str:
    token = _parse_result(value)
    if token == "approved":
        return "consumed"
    if token == "rejected":
        return "rejected"
    return "reserved"


def _find_iqc_record_by_uri(*, sb: Any, iqc_uri: str) -> dict[str, Any]:
    needle = _to_text(iqc_uri).strip()
    if not needle:
        raise HTTPException(status_code=400, detail="iqc_uri is required")
    latest: dict[str, Any] | None = None
    latest_ts = ""
    for row in _fetch_proof_rows(sb=sb, proof_type="inspection"):
        state_data = _as_dict(row.get("state_data"))
        if _to_text(state_data.get("proof_kind")).strip() != "iqc_material_submit":
            continue
        if _to_text(state_data.get("iqc_uri")).strip() != needle:
            continue
        marker = _to_text(state_data.get("submitted_at") or row.get("created_at")).strip()
        if marker >= latest_ts:
            latest_ts = marker
            latest = row
    if latest is None:
        raise HTTPException(status_code=404, detail=f"iqc_not_found: {needle}")
    return latest


def _iter_material_utxo_rows(
    *,
    sb: Any,
    iqc_uri: str = "",
    component_uri: str = "",
    process_step: str = "",
) -> list[dict[str, Any]]:
    q_iqc_uri = _to_text(iqc_uri).strip()
    q_component_uri = _to_text(component_uri).strip().rstrip("/")
    q_process_step = _to_text(process_step).strip()
    out: list[dict[str, Any]] = []
    for row in _fetch_proof_rows(sb=sb, proof_type="inspection"):
        state_data = _as_dict(row.get("state_data"))
        if _to_text(state_data.get("proof_kind")).strip() != "material_inspection_batch":
            continue
        if q_iqc_uri and _to_text(state_data.get("iqc_uri")).strip() != q_iqc_uri:
            continue
        if q_component_uri and _to_text(state_data.get("component_uri")).strip().rstrip("/") != q_component_uri:
            continue
        if q_process_step and _to_text(state_data.get("process_step")).strip() != q_process_step:
            continue
        out.append(row)
    out.sort(key=lambda row: _to_text(_as_dict(row.get("state_data")).get("created_at") or row.get("created_at")).strip())
    return out


def _material_utxo_from_row(row: dict[str, Any]) -> MaterialUTXO:
    sd = _as_dict(row.get("state_data"))
    return MaterialUTXO(
        utxo_id=_to_text(sd.get("utxo_id")).strip(),
        material_code=_to_text(sd.get("material_code")).strip(),
        batch_no=_to_text(sd.get("batch_no")).strip(),
        iqc_uri=_to_text(sd.get("iqc_uri")).strip(),
        total_qty=float(sd.get("total_qty") or 0.0),
        used_qty=float(sd.get("used_qty") or 0.0),
        remaining=float(sd.get("remaining") or 0.0),
        unit=_to_text(sd.get("unit")).strip(),
        unit_price=float(sd.get("unit_price") or 0.0),
        supplier=_to_text(sd.get("supplier")).strip(),
        inspection_batch_no=_to_text(sd.get("inspection_batch_no")).strip(),
        inspection_form=_to_text(sd.get("inspection_form")).strip(),
        inspection_uri=_to_text(sd.get("inspection_uri")).strip(),
        inspection_result=_parse_result(sd.get("inspection_result")),
        component_uri=_to_text(sd.get("component_uri")).strip(),
        process_step=_to_text(sd.get("process_step")).strip(),
        quantity=float(sd.get("quantity") or 0.0),
        status=_to_text(sd.get("status")).strip() or "consumed",
        v_uri=_to_text(sd.get("v_uri")).strip(),
        data_hash=_to_text(sd.get("data_hash")).strip(),
        signed_by=_to_text(sd.get("signed_by")).strip(),
        created_at=datetime.fromisoformat(
            _to_text(sd.get("created_at") or row.get("created_at")).replace("Z", "+00:00")
        ),
        proof_id=_to_text(row.get("proof_id")).strip(),
        proof_hash=_to_text(row.get("proof_hash")).strip(),
    )


def _consumed_qty(records: list[MaterialUTXO]) -> float:
    qty = 0.0
    for item in records:
        if item.inspection_result == "approved":
            qty += float(item.quantity or 0.0)
    return qty


def _serialize_for_hash(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def create_inspection_batch(
    *,
    sb: Any,
    iqc_uri: str,
    component_uri: str,
    process_step: str,
    quantity: float,
    unit: str,
    inspection_form: str,
    inspection_batch_no: str,
    inspection_result: str,
    test_results: dict[str, Any] | None,
    executor_uri: str,
    owner_uri: str,
    commit: bool = True,
) -> InspectionBatchResult:
    if float(quantity or 0.0) <= 0:
        raise HTTPException(status_code=400, detail="quantity must be > 0")
    c_uri = _to_text(component_uri).strip().rstrip("/")
    if not c_uri:
        raise HTTPException(status_code=400, detail="component_uri is required")
    p_step = _to_text(process_step).strip()
    if not p_step:
        raise HTTPException(status_code=400, detail="process_step is required")
    signer = _to_text(executor_uri).strip()
    if not signer:
        raise HTTPException(status_code=400, detail="executor_uri is required")

    iqc_row = _find_iqc_record_by_uri(sb=sb, iqc_uri=iqc_uri)
    iqc_sd = _as_dict(iqc_row.get("state_data"))
    iqc_status = _parse_result(iqc_sd.get("status"))
    if iqc_status != "approved":
        raise HTTPException(status_code=409, detail=f"iqc_not_approved: {iqc_status}")

    total_qty = float(iqc_sd.get("total_qty") or 0.0)
    material_code = _to_text(iqc_sd.get("material_code")).strip()
    batch_no = _to_text(iqc_sd.get("batch_no")).strip()
    actual_unit = _to_text(unit).strip() or _to_text(iqc_sd.get("unit")).strip()
    if total_qty <= 0:
        raise HTTPException(status_code=409, detail="iqc_total_qty_missing")
    if actual_unit and _to_text(iqc_sd.get("unit")).strip() and actual_unit != _to_text(iqc_sd.get("unit")).strip():
        raise HTTPException(status_code=409, detail="unit_mismatch_with_iqc")

    existing_rows = _iter_material_utxo_rows(sb=sb, iqc_uri=iqc_uri)
    existing = [_material_utxo_from_row(row) for row in existing_rows]
    already_used = _consumed_qty(existing)
    if already_used + float(quantity) > total_qty + 1e-9:
        remaining = max(total_qty - already_used, 0.0)
        raise HTTPException(
            status_code=409,
            detail=f"material_remaining_not_enough: remaining={round(remaining, 6)} {actual_unit}",
        )

    now = _utc_now()
    parsed_result = _parse_result(inspection_result)
    if not _to_text(inspection_batch_no).strip():
        inspection_batch_no = f"JYP-{now.strftime('%Y-%m%d')}-{len(existing) + 1:03d}"
    i_batch = _to_text(inspection_batch_no).strip()
    i_uri = f"v://cost/inspection-batch/{_safe_uri_token(i_batch)}"
    utxo_id = f"UTXO-{uuid4().hex[:10].upper()}"
    v_uri = f"v://cost/material-utxo/{utxo_id}"
    used_qty = already_used + (float(quantity) if parsed_result == "approved" else 0.0)
    remaining = max(total_qty - used_qty, 0.0)
    unit_price = float(iqc_sd.get("unit_price") or 0.0)
    supplier = _to_text(iqc_sd.get("supplier")).strip()
    payload_core = {
        "utxo_id": utxo_id,
        "material_code": material_code,
        "batch_no": batch_no,
        "iqc_uri": _to_text(iqc_uri).strip(),
        "total_qty": total_qty,
        "used_qty": used_qty,
        "remaining": remaining,
        "unit": actual_unit,
        "unit_price": unit_price,
        "supplier": supplier,
        "inspection_batch_no": i_batch,
        "inspection_form": _to_text(inspection_form).strip(),
        "inspection_uri": i_uri,
        "inspection_result": parsed_result,
        "component_uri": c_uri,
        "process_step": p_step,
        "quantity": float(quantity),
        "status": _utxo_status_from_result(parsed_result),
        "v_uri": v_uri,
        "signed_by": signer,
        "created_at": now.isoformat(),
        "test_results": _as_dict(test_results),
    }
    payload_hash = hashlib.sha256(_serialize_for_hash(payload_core).encode("utf-8")).hexdigest()
    state_data = {
        "proof_kind": "material_inspection_batch",
        **payload_core,
        "data_hash": payload_hash,
    }
    proof_id = f"GP-MATERIAL-UTXO-{_sha16(f'{v_uri}:{payload_hash}:{now.isoformat()}').upper()}"
    proof_hash = payload_hash
    committed = False
    if bool(commit) and sb is not None:
        row = ProofUTXOEngine(sb).create(
            proof_id=proof_id,
            owner_uri=_to_text(owner_uri).strip() or _to_text(iqc_sd.get("project_uri")).strip(),
            project_uri=_to_text(iqc_sd.get("project_uri")).strip(),
            proof_type="inspection",
            result=_proof_result(parsed_result),
            state_data=state_data,
            norm_uri="v://norm/NormPeg/MaterialUTXO/1.0",
            segment_uri=f"{c_uri}/materials/{_safe_uri_token(material_code)}/{_safe_uri_token(i_batch)}",
            signer_uri=signer,
            signer_role="IQC",
        )
        proof_id = _to_text(row.get("proof_id")).strip() or proof_id
        proof_hash = _to_text(row.get("proof_hash")).strip() or proof_hash
        committed = True

    utxo = MaterialUTXO(
        **{**state_data, "proof_id": proof_id, "proof_hash": proof_hash},
    )
    return InspectionBatchResult(
        iqc_uri=_to_text(iqc_uri).strip(),
        component_uri=c_uri,
        process_step=p_step,
        quantity=float(quantity),
        unit=actual_unit,
        total_qty=total_qty,
        used_qty=used_qty,
        remaining=remaining,
        material_code=material_code,
        inspection_batch_no=i_batch,
        inspection_uri=i_uri,
        inspection_result=parsed_result,
        utxo=utxo,
        committed=committed,
    )


def get_material_utxo_by_iqc(*, sb: Any, iqc_uri: str) -> MaterialUTXOQueryResult:
    records = [_material_utxo_from_row(row) for row in _iter_material_utxo_rows(sb=sb, iqc_uri=iqc_uri)]
    iqc_row = _find_iqc_record_by_uri(sb=sb, iqc_uri=iqc_uri)
    iqc_sd = _as_dict(iqc_row.get("state_data"))
    used = _consumed_qty(records)
    total_qty = float(iqc_sd.get("total_qty") or 0.0)
    unit_price = float(iqc_sd.get("unit_price") or 0.0)
    summary = {
        "material_code": _to_text(iqc_sd.get("material_code")).strip(),
        "batch_no": _to_text(iqc_sd.get("batch_no")).strip(),
        "unit": _to_text(iqc_sd.get("unit")).strip(),
        "supplier": _to_text(iqc_sd.get("supplier")).strip(),
        "unit_price": unit_price,
        "total_qty": total_qty,
        "used_qty": used,
        "remaining": max(total_qty - used, 0.0),
        "record_count": len(records),
        "material_cost": round(sum(float(item.quantity) * unit_price for item in records if item.inspection_result == "approved"), 6),
    }
    return MaterialUTXOQueryResult(scope="iqc", key=_to_text(iqc_uri).strip(), records=records, summary=summary)


def get_material_utxo_by_component(*, sb: Any, component_uri: str) -> MaterialUTXOQueryResult:
    c_uri = _to_text(component_uri).strip().rstrip("/")
    records = [_material_utxo_from_row(row) for row in _iter_material_utxo_rows(sb=sb, component_uri=c_uri)]
    total_cost = 0.0
    by_material: dict[str, dict[str, Any]] = {}
    for item in records:
        if item.inspection_result != "approved":
            continue
        cost = float(item.quantity) * float(item.unit_price)
        total_cost += cost
        key = item.material_code
        cur = by_material.setdefault(
            key,
            {"material_code": key, "unit": item.unit, "quantity": 0.0, "cost": 0.0},
        )
        cur["quantity"] += float(item.quantity)
        cur["cost"] += float(cost)
    summary = {
        "record_count": len(records),
        "total_cost": round(total_cost, 6),
        "by_material": list(by_material.values()),
    }
    return MaterialUTXOQueryResult(scope="component", key=c_uri, records=records, summary=summary)


def summarize_component_step_materials(
    *,
    sb: Any,
    component_uri: str,
    process_step: str = "",
) -> dict[str, dict[str, Any]]:
    rows = _iter_material_utxo_rows(sb=sb, component_uri=component_uri, process_step=process_step)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = _material_utxo_from_row(row)
        if item.inspection_result != "approved":
            continue
        key = item.material_code.lower()
        cur = out.setdefault(
            key,
            {
                "material_code": item.material_code,
                "qty": 0.0,
                "unit": item.unit,
                "cost": 0.0,
                "records": [],
            },
        )
        cur["qty"] += float(item.quantity)
        cur["cost"] += float(item.quantity) * float(item.unit_price)
        cur["records"].append(
            {
                "utxo_id": item.utxo_id,
                "inspection_batch_no": item.inspection_batch_no,
                "iqc_uri": item.iqc_uri,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "cost": float(item.quantity) * float(item.unit_price),
                "inspection_uri": item.inspection_uri,
            }
        )
    return out


def summarize_component_material_cost(*, sb: Any, component_uri: str) -> dict[str, Any]:
    grouped = summarize_component_step_materials(sb=sb, component_uri=component_uri, process_step="")
    total = round(sum(float(item.get("cost") or 0.0) for item in grouped.values()), 6)
    return {"total_material_cost": total, "materials": list(grouped.values())}

