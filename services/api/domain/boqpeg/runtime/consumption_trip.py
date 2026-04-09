"""Consumption-trip runtime: welding/formwork/prestressing consumption actions."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import math
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
import httpx

from services.api.domain.boqpeg.models import (
    ConsumptionTrip,
    ConsumptionTripRequest,
    ConsumptionTripSubmitResult,
    ConsumableItem,
    FormworkAsset,
    FormworkUseTripRequest,
    PrestressingTripRequest,
    TripSignature,
    WeldingTripRequest,
)
from services.api.domain.utxo.integrations import ProofUTXOEngine


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _fetch_proof_rows(*, sb: Any, project_uri: str = "", proof_type: str = "inspection") -> list[dict[str, Any]]:
    if sb is None:
        return []
    query = sb.table("proof_utxo").select("*").eq("proof_type", proof_type)
    if _to_text(project_uri).strip():
        query = query.eq("project_uri", _to_text(project_uri).strip().rstrip("/"))
    rows = query.order("created_at", desc=False).limit(50000).execute().data or []
    return [row for row in rows if isinstance(row, dict)]


def _find_iqc_row_by_uri(*, sb: Any, iqc_uri: str) -> dict[str, Any]:
    needle = _to_text(iqc_uri).strip()
    if not needle:
        raise HTTPException(status_code=400, detail="batch_ref is required")
    latest: dict[str, Any] | None = None
    latest_mark = ""
    for row in _fetch_proof_rows(sb=sb, proof_type="inspection"):
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("proof_kind")).strip() != "iqc_material_submit":
            continue
        if _to_text(sd.get("iqc_uri")).strip() != needle:
            continue
        marker = _to_text(sd.get("submitted_at") or row.get("created_at")).strip()
        if marker >= latest_mark:
            latest_mark = marker
            latest = row
    if latest is None:
        raise HTTPException(status_code=404, detail=f"iqc_not_found: {needle}")
    return latest


def _iter_consumption_trips(*, sb: Any, project_uri: str = "", component_uri: str = "") -> list[dict[str, Any]]:
    c_uri = _to_text(component_uri).strip().rstrip("/")
    rows = _fetch_proof_rows(sb=sb, project_uri=project_uri, proof_type="inspection")
    out: list[dict[str, Any]] = []
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("proof_kind")).strip() != "consumption_trip":
            continue
        if c_uri and _to_text(sd.get("component_uri")).strip().rstrip("/") != c_uri:
            continue
        out.append(row)
    return out


def _iter_formwork_assets(*, sb: Any, project_uri: str = "", asset_uri: str = "") -> list[dict[str, Any]]:
    a_uri = _to_text(asset_uri).strip()
    rows = _fetch_proof_rows(sb=sb, project_uri=project_uri, proof_type="document")
    out: list[dict[str, Any]] = []
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("proof_kind")).strip() != "formwork_asset_snapshot":
            continue
        if a_uri and _to_text(sd.get("asset_uri")).strip() != a_uri:
            continue
        out.append(row)
    out.sort(key=lambda item: _to_text(item.get("created_at")).strip())
    return out


def _consumption_used_by_batch(*, sb: Any, batch_ref: str) -> float:
    target = _to_text(batch_ref).strip()
    used = 0.0
    for row in _iter_consumption_trips(sb=sb):
        sd = _as_dict(row.get("state_data"))
        for raw in _as_list(sd.get("consumables")):
            item = _as_dict(raw)
            if _to_text(item.get("batch_ref")).strip() != target:
                continue
            used += float(item.get("quantity_used") or 0.0)
    return used


def _normalize_signature(signer_uri: str, signatures: list[TripSignature]) -> list[TripSignature]:
    if signatures:
        return signatures
    return [
        TripSignature(
            signer_uri=signer_uri,
            signer_name="",
            signed_at=_utc_now(),
            sig_data=f"signpeg:v1:{hashlib.sha256(f'{signer_uri}:{_utc_now().isoformat()}'.encode('utf-8')).hexdigest()}",
        )
    ]


def _consumable_cost(consumables: list[ConsumableItem]) -> float:
    total = 0.0
    for item in consumables:
        total += float(item.quantity_used) * float(item.unit_price or 0.0)
    return round(total, 6)


def _sum_trip_labor_hours(process_params: dict[str, Any]) -> float:
    return float(process_params.get("labor_hours") or process_params.get("man_hours") or 0.0)


def _sum_trip_labor_cost(process_params: dict[str, Any]) -> float:
    rate = float(process_params.get("labor_rate") or process_params.get("hour_rate") or 0.0)
    return round(_sum_trip_labor_hours(process_params) * rate, 6)


def _serialize_for_hash(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _build_trip_uri(*, project_uri: str, created_at: datetime) -> str:
    root = _to_text(project_uri).strip().rstrip("/") or "v://cn.大锦/DJGS"
    date_str = created_at.strftime("%Y/%m%d")
    return f"{root}/trip/{date_str}/CTRIP-{uuid4().hex[:8].upper()}"


def _build_trip(
    *,
    request: ConsumptionTripRequest,
    trip_role: str,
    consumables: list[ConsumableItem],
    result: str,
    extra_cost: float = 0.0,
    overuse_alerted: bool = False,
) -> ConsumptionTrip:
    created_at = _utc_now()
    trip_uri = _build_trip_uri(project_uri=request.project_uri, created_at=created_at)
    base_cost = _consumable_cost(consumables) + float(extra_cost or 0.0) + _sum_trip_labor_cost(request.process_params)
    return ConsumptionTrip(
        v_uri=trip_uri,
        trip_role=trip_role,
        location=_to_text(request.location).strip(),
        work_on=request.work_on or [_to_text(request.component_uri).strip()],
        consumables=consumables,
        process_params=request.process_params,
        executor_uri=_to_text(request.executor_uri).strip(),
        equipment_uri=_to_text(request.equipment_uri).strip(),
        signatures=_normalize_signature(_to_text(request.executor_uri).strip(), request.signatures),
        photos=[_to_text(item).strip() for item in request.photos if _to_text(item).strip()],
        test_reports=[_to_text(item).strip() for item in request.test_reports if _to_text(item).strip()],
        result=result,
        cost_aggregate=round(base_cost, 6),
        project_uri=_to_text(request.project_uri).strip().rstrip("/"),
        component_uri=_to_text(request.component_uri).strip().rstrip("/"),
        created_at=created_at,
        overuse_alerted=bool(overuse_alerted),
    )


def _persist_trip(sb: Any, *, trip: ConsumptionTrip, owner_uri: str, commit: bool) -> ConsumptionTrip:
    payload = trip.model_dump(mode="json", by_alias=True)
    state_data = {
        "proof_kind": "consumption_trip",
        **payload,
    }
    payload_hash = hashlib.sha256(_serialize_for_hash(state_data).encode("utf-8")).hexdigest()
    proof_id = f"GP-CONSUME-{_sha16(f'{trip.v_uri}:{payload_hash}:{trip.created_at.isoformat()}').upper()}"
    if bool(commit) and sb is not None:
        row = ProofUTXOEngine(sb).create(
            proof_id=proof_id,
            owner_uri=_to_text(owner_uri).strip() or f"{trip.project_uri}/role/system/",
            project_uri=trip.project_uri,
            proof_type="inspection",
            result="PASS" if trip.result == "合格" else "FAIL",
            state_data={**state_data, "data_hash": payload_hash},
            norm_uri="v://norm/NormPeg/ConsumptionTrip/1.0",
            segment_uri=f"{trip.component_uri}/consumption/{_safe_uri_token(trip.trip_role)}",
            signer_uri=trip.executor_uri,
            signer_role="CONSUMPTION",
        )
        trip.proof_id = _to_text(row.get("proof_id")).strip() or proof_id
        trip.proof_hash = _to_text(row.get("proof_hash")).strip() or payload_hash
        _insert_gate_trip(sb=sb, trip=trip)
    else:
        trip.proof_id = proof_id
        trip.proof_hash = payload_hash
    return trip


def _insert_gate_trip(*, sb: Any, trip: ConsumptionTrip) -> None:
    if sb is None:
        return
    executor_name = ""
    if trip.signatures:
        executor_name = _to_text(trip.signatures[0].signer_name).strip()
    sb.table("gate_trips").insert(
        {
            "trip_uri": trip.v_uri,
            "doc_id": f"CONS-{_safe_uri_token(trip.component_uri)}-{_safe_uri_token(trip.trip_role)}",
            "body_hash": trip.proof_hash,
            "executor_uri": trip.executor_uri,
            "executor_name": executor_name,
            "dto_role": "constructor",
            "trip_role": trip.trip_role,
            "action": "consume",
            "sig_data": trip.signatures[0].sig_data if trip.signatures else "",
            "signed_at": trip.created_at.isoformat(),
            "verified": trip.result == "合格",
            "metadata": {
                "component_uri": trip.component_uri,
                "location": trip.location,
                "result": trip.result,
                "cost_aggregate": float(trip.cost_aggregate),
                "consumables": [item.model_dump(mode="json") for item in trip.consumables],
            },
            "created_at": _utc_now().isoformat(),
        }
    ).execute()


def _append_railpact_labor(sb: Any, *, trip: ConsumptionTrip) -> None:
    if sb is None:
        return
    labor_cost = _sum_trip_labor_cost(trip.process_params)
    if labor_cost <= 0:
        return
    sb.table("railpact_settlements").insert(
        {
            "trip_uri": trip.v_uri,
            "executor_uri": trip.executor_uri,
            "doc_id": f"CONS-LABOR-{_safe_uri_token(trip.component_uri)}",
            "amount": labor_cost,
            "energy_delta": 0,
            "settled_at": _utc_now().isoformat(),
            "metadata": {
                "kind": "consumption_trip_labor",
                "component_uri": trip.component_uri,
                "trip_role": trip.trip_role,
                "labor_hours": _sum_trip_labor_hours(trip.process_params),
                "labor_rate": float(trip.process_params.get("labor_rate") or trip.process_params.get("hour_rate") or 0.0),
            },
        }
    ).execute()


def _load_project_row(sb: Any, project_uri: str) -> dict[str, Any]:
    rows = (
        sb.table("projects")
        .select("*")
        .eq("v_uri", _to_text(project_uri).strip().rstrip("/"))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return {}
    return rows[0] if isinstance(rows[0], dict) else {}


async def _send_overuse_alert(*, sb: Any, project_uri: str, trip: ConsumptionTrip, items: list[ConsumableItem]) -> dict[str, Any]:
    project = _load_project_row(sb, project_uri)
    enterprise_id = _to_text(project.get("enterprise_id")).strip()
    if not enterprise_id:
        return {"attempted": False, "reason": "enterprise_id_missing"}
    cfg_rows = sb.table("enterprise_configs").select("custom_fields").eq("enterprise_id", enterprise_id).limit(1).execute().data or []
    cfg = cfg_rows[0] if cfg_rows and isinstance(cfg_rows[0], dict) else {}
    webhook_url = _to_text(_as_dict(cfg.get("custom_fields")).get("webhook_url")).strip()
    if not webhook_url:
        return {"attempted": False, "reason": "webhook_url_missing"}
    payload = {
        "event": "consumption.overuse.alert",
        "project_uri": trip.project_uri,
        "component_uri": trip.component_uri,
        "trip_uri": trip.v_uri,
        "trip_role": trip.trip_role,
        "executor_uri": trip.executor_uri,
        "items": [item.model_dump(mode="json") for item in items],
        "created_at": _utc_now().isoformat(),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(webhook_url, json=payload)
        return {"attempted": True, "success": 200 <= response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        return {"attempted": True, "success": False, "reason": f"{exc.__class__.__name__}: {exc}"}


def _persist_overuse_alert_proof(
    *,
    sb: Any,
    trip: ConsumptionTrip,
    owner_uri: str,
    items: list[ConsumableItem],
    commit: bool,
) -> str:
    state_data = {
        "proof_kind": "consumption_overuse_alert",
        "trip_uri": trip.v_uri,
        "project_uri": trip.project_uri,
        "component_uri": trip.component_uri,
        "trip_role": trip.trip_role,
        "items": [item.model_dump(mode="json") for item in items],
        "created_at": _utc_now().isoformat(),
    }
    alert_hash = hashlib.sha256(_serialize_for_hash(state_data).encode("utf-8")).hexdigest()
    alert_proof_id = f"GP-OVERUSE-{_sha16(f'{trip.v_uri}:{alert_hash}').upper()}"
    if bool(commit) and sb is not None:
        ProofUTXOEngine(sb).create(
            proof_id=alert_proof_id,
            owner_uri=_to_text(owner_uri).strip() or f"{trip.project_uri}/role/system/",
            project_uri=trip.project_uri,
            proof_type="document",
            result="WARNING",
            state_data={**state_data, "alert_hash": alert_hash},
            norm_uri="v://norm/NormPeg/ConsumptionOveruseAlert/1.0",
            segment_uri=f"{trip.component_uri}/consumption/alerts",
            signer_uri=trip.executor_uri,
            signer_role="SYSTEM",
        )
    return alert_proof_id


def _validate_consumables(
    *,
    sb: Any,
    items: list[ConsumableItem],
) -> tuple[list[ConsumableItem], list[dict[str, Any]], list[ConsumableItem]]:
    normalized: list[ConsumableItem] = []
    batch_usage: list[dict[str, Any]] = []
    overused: list[ConsumableItem] = []
    for raw in items:
        item = raw.model_copy(deep=True)
        if float(item.quantity_used or 0.0) <= 0:
            raise HTTPException(status_code=400, detail=f"invalid_quantity_used: {item.name}")
        iqc_row = _find_iqc_row_by_uri(sb=sb, iqc_uri=item.batch_ref)
        iqc_sd = _as_dict(iqc_row.get("state_data"))
        status = _to_text(iqc_sd.get("status")).strip().lower()
        if status not in {"approved", "pass", "passed", "ok"}:
            raise HTTPException(status_code=409, detail=f"batch_not_approved: {item.batch_ref}")

        total_qty = float(iqc_sd.get("total_qty") or 0.0)
        used_before = _consumption_used_by_batch(sb=sb, batch_ref=item.batch_ref)
        used_after = used_before + float(item.quantity_used)
        if total_qty > 0 and used_after > total_qty + 1e-9:
            raise HTTPException(
                status_code=409,
                detail=f"batch_remaining_not_enough: {item.batch_ref} remaining={round(total_qty - used_before, 6)}",
            )
        iqc_unit = _to_text(iqc_sd.get("unit")).strip()
        if iqc_unit and _to_text(item.quantity_unit).strip() and iqc_unit != _to_text(item.quantity_unit).strip():
            raise HTTPException(status_code=409, detail=f"unit_mismatch_with_iqc: {item.batch_ref}")

        if not _to_text(item.material_code).strip():
            item.material_code = _to_text(iqc_sd.get("material_code")).strip()
        if float(item.unit_price or 0.0) <= 0:
            item.unit_price = float(iqc_sd.get("unit_price") or 0.0)
        if not _to_text(item.quantity_unit).strip():
            item.quantity_unit = iqc_unit

        if float(item.standard_qty or 0.0) > 0 and float(item.quantity_used) > float(item.standard_qty) * 1.1:
            if not _to_text(item.over_reason).strip():
                raise HTTPException(status_code=422, detail=f"overuse_reason_required: {item.name}")
            overused.append(item)

        batch_usage.append(
            {
                "batch_ref": item.batch_ref,
                "material_code": item.material_code,
                "total_qty": total_qty,
                "used_before": round(used_before, 6),
                "used_after": round(used_after, 6),
                "remaining": round(max(total_qty - used_after, 0.0), 6),
                "unit": item.quantity_unit,
            }
        )
        normalized.append(item)
    return normalized, batch_usage, overused


def _load_latest_formwork_asset(*, sb: Any, project_uri: str, asset_uri: str) -> FormworkAsset | None:
    rows = _iter_formwork_assets(sb=sb, project_uri=project_uri, asset_uri=asset_uri)
    if not rows:
        return None
    latest = rows[-1]
    sd = _as_dict(latest.get("state_data"))
    return FormworkAsset(
        v_uri=_to_text(sd.get("asset_uri")).strip() or asset_uri,
        name=_to_text(sd.get("name")).strip(),
        purchase_price=float(sd.get("purchase_price") or 0.0),
        expected_uses=int(sd.get("expected_uses") or 0),
        current_uses=int(sd.get("current_uses") or 0),
        remaining_uses=int(sd.get("remaining_uses") or 0),
        use_history=[_to_text(x).strip() for x in _as_list(sd.get("use_history")) if _to_text(x).strip()],
        cumulative_wear=float(sd.get("cumulative_wear") or 0.0),
        status=_to_text(sd.get("status")).strip() or "in_service",
        updated_at=datetime.fromisoformat(_to_text(sd.get("updated_at") or latest.get("created_at")).replace("Z", "+00:00")),
    )


def _persist_formwork_asset(*, sb: Any, trip: ConsumptionTrip, asset: FormworkAsset, owner_uri: str, commit: bool) -> FormworkAsset:
    state_data = {
        "proof_kind": "formwork_asset_snapshot",
        "project_uri": trip.project_uri,
        "component_uri": trip.component_uri,
        "trip_uri": trip.v_uri,
        "asset_uri": asset.v_uri,
        **asset.model_dump(mode="json"),
    }
    payload_hash = hashlib.sha256(_serialize_for_hash(state_data).encode("utf-8")).hexdigest()
    proof_id = f"GP-FORMWORK-{_sha16(f'{asset.v_uri}:{payload_hash}:{trip.created_at.isoformat()}').upper()}"
    if bool(commit) and sb is not None:
        ProofUTXOEngine(sb).create(
            proof_id=proof_id,
            owner_uri=_to_text(owner_uri).strip() or f"{trip.project_uri}/role/system/",
            project_uri=trip.project_uri,
            proof_type="document",
            result="PASS",
            state_data={**state_data, "data_hash": payload_hash},
            norm_uri="v://norm/NormPeg/FormworkAsset/1.0",
            segment_uri=f"{trip.component_uri}/formwork/{_safe_uri_token(asset.v_uri)}",
            signer_uri=trip.executor_uri,
            signer_role="ASSET",
        )
    return asset


async def submit_welding_trip(*, sb: Any, body: WeldingTripRequest, commit: bool = True) -> ConsumptionTripSubmitResult:
    consumables, batch_usage, overused = _validate_consumables(sb=sb, items=body.consumables)
    trip = _build_trip(request=body, trip_role=body.trip_role, consumables=consumables, result="合格", overuse_alerted=bool(overused))
    trip = _persist_trip(sb, trip=trip, owner_uri=body.owner_uri, commit=bool(commit))
    _append_railpact_labor(sb, trip=trip)

    warnings: list[str] = []
    if overused:
        _persist_overuse_alert_proof(sb=sb, trip=trip, owner_uri=body.owner_uri, items=overused, commit=bool(commit))
        notify = await _send_overuse_alert(sb=sb, project_uri=trip.project_uri, trip=trip, items=overused)
        warnings.append(f"overuse_alert:{json.dumps(notify, ensure_ascii=False)}")

    return ConsumptionTripSubmitResult(
        ok=True,
        trip=trip,
        gate_passed=True,
        gate_reason="",
        batch_usage=batch_usage,
        warnings=warnings,
    )


async def submit_formwork_use_trip(*, sb: Any, body: FormworkUseTripRequest, commit: bool = True) -> ConsumptionTripSubmitResult:
    consumables, batch_usage, overused = _validate_consumables(sb=sb, items=body.consumables)

    existing = _load_latest_formwork_asset(sb=sb, project_uri=body.project_uri, asset_uri=body.formwork_asset_uri)
    expected_uses = int(existing.expected_uses if existing else body.expected_uses)
    purchase_price = float(existing.purchase_price if existing else body.purchase_price)
    if expected_uses <= 0:
        raise HTTPException(status_code=422, detail="expected_uses must be > 0")
    if purchase_price < 0:
        raise HTTPException(status_code=422, detail="purchase_price must be >= 0")
    next_current_uses = int((existing.current_uses if existing else 0) + 1)
    remaining = max(expected_uses - next_current_uses, 0)
    wear = min(max(next_current_uses / expected_uses, 0.0), 1.0)
    depreciation = round(purchase_price / expected_uses, 6)
    status = "retired" if remaining <= 0 else "in_service"
    asset = FormworkAsset(
        v_uri=_to_text(body.formwork_asset_uri).strip(),
        name=_to_text(body.formwork_asset_name).strip() or (existing.name if existing else "Formwork"),
        purchase_price=purchase_price,
        expected_uses=expected_uses,
        current_uses=next_current_uses,
        remaining_uses=remaining,
        use_history=(existing.use_history if existing else []),
        cumulative_wear=round(wear, 6),
        status=status,
        updated_at=_utc_now(),
    )

    params = dict(body.process_params)
    params["depreciation_allocated"] = depreciation
    body = body.model_copy(update={"process_params": params})

    trip = _build_trip(
        request=body,
        trip_role=body.trip_role,
        consumables=consumables,
        result="合格",
        extra_cost=depreciation,
        overuse_alerted=bool(overused),
    )
    asset.use_history = [*asset.use_history, trip.v_uri]
    trip = _persist_trip(sb, trip=trip, owner_uri=body.owner_uri, commit=bool(commit))
    _persist_formwork_asset(sb=sb, trip=trip, asset=asset, owner_uri=body.owner_uri, commit=bool(commit))
    _append_railpact_labor(sb, trip=trip)

    warnings: list[str] = []
    if overused:
        _persist_overuse_alert_proof(sb=sb, trip=trip, owner_uri=body.owner_uri, items=overused, commit=bool(commit))
        notify = await _send_overuse_alert(sb=sb, project_uri=trip.project_uri, trip=trip, items=overused)
        warnings.append(f"overuse_alert:{json.dumps(notify, ensure_ascii=False)}")

    batch_usage.append(
        {
            "asset_uri": asset.v_uri,
            "current_uses": asset.current_uses,
            "remaining_uses": asset.remaining_uses,
            "depreciation_allocated": depreciation,
            "status": asset.status,
        }
    )
    return ConsumptionTripSubmitResult(
        ok=True,
        trip=trip,
        gate_passed=True,
        gate_reason="",
        batch_usage=batch_usage,
        formwork_asset=asset,
        warnings=warnings,
    )


async def submit_prestressing_trip(*, sb: Any, body: PrestressingTripRequest, commit: bool = True) -> ConsumptionTripSubmitResult:
    consumables, batch_usage, overused = _validate_consumables(sb=sb, items=body.consumables)
    theoretical = float(body.theoretical_elongation or 0.0)
    actual = float(body.actual_elongation or 0.0)
    if theoretical <= 0:
        raise HTTPException(status_code=422, detail="theoretical_elongation must be > 0")
    deviation_ratio = (actual - theoretical) / theoretical
    gate_passed = math.fabs(deviation_ratio) <= float(body.tolerance_ratio)
    gate_reason = ""
    if not gate_passed:
        gate_reason = f"prestressing_elongation_out_of_range: deviation={round(deviation_ratio * 100, 3)}%"

    params = dict(body.process_params)
    params.update(
        {
            "theoretical_elongation": theoretical,
            "actual_elongation": actual,
            "deviation_ratio": deviation_ratio,
            "tolerance_ratio": float(body.tolerance_ratio),
        }
    )
    body = body.model_copy(update={"process_params": params})
    trip = _build_trip(
        request=body,
        trip_role=body.trip_role,
        consumables=consumables,
        result="合格" if gate_passed else "不合格",
        overuse_alerted=bool(overused),
    )
    trip = _persist_trip(sb, trip=trip, owner_uri=body.owner_uri, commit=bool(commit))
    _append_railpact_labor(sb, trip=trip)

    warnings: list[str] = []
    if overused:
        _persist_overuse_alert_proof(sb=sb, trip=trip, owner_uri=body.owner_uri, items=overused, commit=bool(commit))
        notify = await _send_overuse_alert(sb=sb, project_uri=trip.project_uri, trip=trip, items=overused)
        warnings.append(f"overuse_alert:{json.dumps(notify, ensure_ascii=False)}")

    if not gate_passed:
        warnings.append(gate_reason)

    return ConsumptionTripSubmitResult(
        ok=True,
        trip=trip,
        gate_passed=gate_passed,
        gate_reason=gate_reason,
        batch_usage=batch_usage,
        warnings=warnings,
    )


def sum_consumable_trips(*, sb: Any, component_uri: str) -> dict[str, Any]:
    records = _iter_consumption_trips(sb=sb, component_uri=component_uri)
    total = 0.0
    refs: list[str] = []
    by_material: dict[str, dict[str, Any]] = {}
    for row in records:
        sd = _as_dict(row.get("state_data"))
        refs.append(_to_text(row.get("proof_id")).strip())
        for raw in _as_list(sd.get("consumables")):
            item = _as_dict(raw)
            qty = float(item.get("quantity_used") or 0.0)
            price = float(item.get("unit_price") or 0.0)
            line_cost = round(qty * price, 6)
            total += line_cost
            key = _to_text(item.get("material_code") or item.get("name")).strip() or "unknown"
            cur = by_material.setdefault(
                key,
                {
                    "material_code": key,
                    "name": _to_text(item.get("name")).strip(),
                    "quantity": 0.0,
                    "cost": 0.0,
                    "unit": _to_text(item.get("quantity_unit")).strip(),
                },
            )
            cur["quantity"] += qty
            cur["cost"] += line_cost
    return {"total_consumables_cost": round(total, 6), "materials": list(by_material.values()), "proof_refs": [x for x in refs if x]}


def sum_formwork_depreciation(*, sb: Any, component_uri: str) -> dict[str, Any]:
    records = _iter_consumption_trips(sb=sb, component_uri=component_uri)
    total = 0.0
    refs: list[str] = []
    for row in records:
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("trip_role")).strip() != "construction.formwork":
            continue
        params = _as_dict(sd.get("process_params"))
        depreciation = float(params.get("depreciation_allocated") or params.get("depreciation") or 0.0)
        if depreciation <= 0:
            # fallback: subtract consumables and labor from aggregated cost
            total_cost = float(sd.get("cost_归集") or sd.get("cost_aggregate") or 0.0)
            consumables_cost = 0.0
            for raw in _as_list(sd.get("consumables")):
                item = _as_dict(raw)
                consumables_cost += float(item.get("quantity_used") or 0.0) * float(item.get("unit_price") or 0.0)
            labor = _sum_trip_labor_cost(params)
            depreciation = max(total_cost - consumables_cost - labor, 0.0)
        total += depreciation
        refs.append(_to_text(row.get("proof_id")).strip())
    return {"total_depreciation_cost": round(total, 6), "proof_refs": [x for x in refs if x]}


__all__ = [
    "submit_welding_trip",
    "submit_formwork_use_trip",
    "submit_prestressing_trip",
    "sum_consumable_trips",
    "sum_formwork_depreciation",
]
