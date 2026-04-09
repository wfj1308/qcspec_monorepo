"""Equipment asset + equipment-trip runtime."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
import httpx

from services.api.domain.boqpeg.models import (
    EquipmentHistoryResult,
    EquipmentTrip,
    EquipmentTripRequest,
    EquipmentTripSubmitResult,
    ToolAsset,
    ToolAssetRegisterRequest,
    ToolAssetStatusResult,
    TripSignature,
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


def _serialize_for_hash(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _fetch_proof_rows(*, sb: Any, project_uri: str = "", proof_type: str = "document") -> list[dict[str, Any]]:
    if sb is None:
        return []
    query = sb.table("proof_utxo").select("*").eq("proof_type", proof_type)
    if _to_text(project_uri).strip():
        query = query.eq("project_uri", _to_text(project_uri).strip().rstrip("/"))
    rows = query.order("created_at", desc=False).limit(50000).execute().data or []
    return [row for row in rows if isinstance(row, dict)]


def _build_signature(signer_uri: str, signatures: list[TripSignature]) -> list[TripSignature]:
    if signatures:
        return signatures
    now = _utc_now()
    return [
        TripSignature(
            signer_uri=signer_uri,
            signer_name="",
            signed_at=now,
            sig_data=f"signpeg:v1:{hashlib.sha256(f'{signer_uri}:{now.isoformat()}'.encode('utf-8')).hexdigest()}",
        )
    ]


def _asset_from_row(row: dict[str, Any]) -> ToolAsset:
    sd = _as_dict(row.get("state_data"))
    payload = _as_dict(sd.get("asset"))
    if not payload:
        payload = {
            "v_uri": _to_text(sd.get("asset_uri")).strip(),
            "project_uri": _to_text(sd.get("project_uri")).strip(),
            "name": _to_text(sd.get("name")).strip(),
            "model_no": _to_text(sd.get("model_no")).strip(),
            "asset_mode": _to_text(sd.get("asset_mode")).strip() or "owned",
            "equipment_manager_uri": _to_text(sd.get("equipment_manager_uri")).strip(),
            "calibration_cert_no": _to_text(sd.get("calibration_cert_no")).strip(),
            "calibration_valid_until": sd.get("calibration_valid_until"),
            "annual_inspection_status": _to_text(sd.get("annual_inspection_status")).strip() or "valid",
            "annual_inspection_valid_until": sd.get("annual_inspection_valid_until"),
            "operator_skill_required": _as_list(sd.get("operator_skill_required")),
            "maintenance_status": _to_text(sd.get("maintenance_status")).strip() or "normal",
            "maintenance_due_at": sd.get("maintenance_due_at"),
            "rental_shift_rate": float(sd.get("rental_shift_rate") or 0.0),
            "purchase_price": float(sd.get("purchase_price") or 0.0),
            "depreciation_years": float(sd.get("depreciation_years") or 8.0),
            "annual_work_hours": float(sd.get("annual_work_hours") or 2000.0),
            "status": _to_text(sd.get("status")).strip() or "in_service",
            "metadata": _as_dict(sd.get("metadata")),
            "created_at": _to_text(sd.get("created_at") or row.get("created_at")).strip(),
            "updated_at": _to_text(sd.get("updated_at") or row.get("created_at")).strip(),
        }
    return ToolAsset.model_validate(payload)


def _latest_asset_row(*, sb: Any, equipment_uri: str) -> dict[str, Any] | None:
    uri = _to_text(equipment_uri).strip()
    latest = None
    latest_marker = ""
    for row in _fetch_proof_rows(sb=sb, proof_type="document"):
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("proof_kind")).strip() != "tool_asset_snapshot":
            continue
        if _to_text(sd.get("asset_uri")).strip() != uri:
            continue
        marker = _to_text(sd.get("updated_at") or row.get("created_at")).strip()
        if marker >= latest_marker:
            latest_marker = marker
            latest = row
    return latest


def _list_asset_rows(*, sb: Any, equipment_uri: str) -> list[dict[str, Any]]:
    uri = _to_text(equipment_uri).strip()
    rows: list[dict[str, Any]] = []
    for row in _fetch_proof_rows(sb=sb, proof_type="document"):
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("proof_kind")).strip() != "tool_asset_snapshot":
            continue
        if _to_text(sd.get("asset_uri")).strip() != uri:
            continue
        rows.append(row)
    rows.sort(key=lambda item: _to_text(item.get("created_at")).strip())
    return rows


def _list_equipment_trip_rows(*, sb: Any, equipment_uri: str = "", component_uri: str = "", project_uri: str = "") -> list[dict[str, Any]]:
    rows = _fetch_proof_rows(sb=sb, project_uri=project_uri, proof_type="inspection")
    e_uri = _to_text(equipment_uri).strip()
    c_uri = _to_text(component_uri).strip().rstrip("/")
    out: list[dict[str, Any]] = []
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("proof_kind")).strip() != "equipment_trip":
            continue
        if e_uri and _to_text(sd.get("equipment_uri")).strip() != e_uri:
            continue
        if c_uri and _to_text(sd.get("component_uri")).strip().rstrip("/") != c_uri:
            continue
        out.append(row)
    out.sort(key=lambda item: _to_text(item.get("created_at")).strip())
    return out


def _persist_asset(*, sb: Any, asset: ToolAsset, owner_uri: str, signer_uri: str, commit: bool) -> ToolAsset:
    now = _utc_now()
    payload = asset.model_copy(update={"updated_at": now})
    state_data = {
        "proof_kind": "tool_asset_snapshot",
        "asset_uri": payload.v_uri,
        "project_uri": payload.project_uri,
        "updated_at": payload.updated_at.isoformat(),
        "asset": payload.model_dump(mode="json"),
    }
    payload_hash = hashlib.sha256(_serialize_for_hash(state_data).encode("utf-8")).hexdigest()
    proof_id = f"GP-EQUIP-ASSET-{_sha16(f'{payload.v_uri}:{payload_hash}:{payload.updated_at.isoformat()}').upper()}"
    if bool(commit) and sb is not None:
        ProofUTXOEngine(sb).create(
            proof_id=proof_id,
            owner_uri=_to_text(owner_uri).strip() or f"{payload.project_uri}/role/system/",
            project_uri=payload.project_uri,
            proof_type="document",
            result="PASS",
            state_data={**state_data, "data_hash": payload_hash},
            norm_uri="v://norm/NormPeg/ToolAsset/1.0",
            segment_uri=f"{payload.project_uri}/equipment/{_safe_uri_token(payload.v_uri)}",
            signer_uri=_to_text(signer_uri).strip() or _to_text(owner_uri).strip() or "v://executor/system/",
            signer_role="ASSET",
        )
    return payload


def _extract_operator_skill_blobs(executor_row: dict[str, Any]) -> list[str]:
    blobs: list[str] = []
    skills = _as_list(executor_row.get("skills"))
    for raw in skills:
        sd = _as_dict(raw)
        scope = " ".join(_to_text(x).strip().lower() for x in _as_list(sd.get("scope")) if _to_text(x).strip())
        blob = " ".join(
            [
                _to_text(sd.get("skill_uri")).strip().lower(),
                _to_text(sd.get("level")).strip().lower(),
                scope,
            ]
        ).strip()
        if blob:
            blobs.append(blob)
    return blobs


def _load_executor_row(*, sb: Any, executor_uri: str) -> dict[str, Any] | None:
    rows = (
        sb.table("san_executors")
        .select("*")
        .eq("executor_uri", _to_text(executor_uri).strip())
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None
    return rows[0] if isinstance(rows[0], dict) else None


def _equipment_gate(asset: ToolAsset, operator_row: dict[str, Any] | None) -> list[str]:
    now = _utc_now()
    today = now.date()
    reasons: list[str] = []
    if asset.status != "in_service":
        reasons.append(f"asset_status_not_allowed:{asset.status}")
    if asset.calibration_valid_until and asset.calibration_valid_until < today:
        reasons.append("calibration_certificate_expired")
    if asset.annual_inspection_status != "valid":
        reasons.append(f"annual_inspection_invalid:{asset.annual_inspection_status}")
    if asset.annual_inspection_valid_until and asset.annual_inspection_valid_until < today:
        reasons.append("annual_inspection_expired")
    if asset.maintenance_status in {"overdue", "in_maintenance"}:
        reasons.append(f"maintenance_status_blocked:{asset.maintenance_status}")
    if asset.maintenance_due_at and asset.maintenance_due_at.astimezone(UTC) < now:
        reasons.append("maintenance_due_expired")

    required = [_to_text(item).strip().lower() for item in asset.operator_skill_required if _to_text(item).strip()]
    if required:
        if operator_row is None:
            reasons.append("operator_not_registered")
        else:
            blobs = _extract_operator_skill_blobs(operator_row)
            for token in required:
                if not any(token in blob for blob in blobs):
                    reasons.append(f"operator_skill_missing:{token}")
    return reasons


def _equipment_warnings(asset: ToolAsset) -> list[str]:
    now = _utc_now()
    today = now.date()
    warnings: list[str] = []
    if asset.calibration_valid_until:
        days_left = (asset.calibration_valid_until - today).days
        if 0 <= days_left <= 30:
            warnings.append(f"calibration_expiring_in_{days_left}_days")
    if asset.maintenance_due_at:
        days_left = (asset.maintenance_due_at.astimezone(UTC).date() - today).days
        if 0 <= days_left <= 7:
            warnings.append(f"maintenance_due_in_{days_left}_days")
    return warnings


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


async def _send_equipment_alert(*, sb: Any, project_uri: str, equipment_uri: str, warnings: list[str], manager_uri: str) -> dict[str, Any]:
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
        "event": "equipment.warning",
        "project_uri": project_uri,
        "equipment_uri": equipment_uri,
        "equipment_manager_uri": manager_uri,
        "warnings": warnings,
        "created_at": _utc_now().isoformat(),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(webhook_url, json=payload)
        return {"attempted": True, "success": 200 <= response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        return {"attempted": True, "success": False, "reason": f"{exc.__class__.__name__}: {exc}"}


def _trip_from_row(row: dict[str, Any]) -> EquipmentTrip:
    sd = _as_dict(row.get("state_data"))
    payload = _as_dict(sd.get("trip"))
    if not payload:
        payload = {
            "trip_uri": _to_text(sd.get("trip_uri")).strip(),
            "project_uri": _to_text(sd.get("project_uri")).strip(),
            "component_uri": _to_text(sd.get("component_uri")).strip(),
            "equipment_uri": _to_text(sd.get("equipment_uri")).strip(),
            "equipment_name": _to_text(sd.get("equipment_name")).strip(),
            "trip_role": _to_text(sd.get("trip_role")).strip() or "equipment.shift",
            "operator_executor_uri": _to_text(sd.get("operator_executor_uri")).strip(),
            "work_hours": float(sd.get("work_hours") or 0.0),
            "shift_count": float(sd.get("shift_count") or 0.0),
            "mode": _to_text(sd.get("mode")).strip() or "owned",
            "unit_rate": float(sd.get("unit_rate") or 0.0),
            "rental_cost": float(sd.get("rental_cost") or 0.0),
            "depreciation_cost": float(sd.get("depreciation_cost") or 0.0),
            "machine_cost": float(sd.get("machine_cost") or 0.0),
            "gate_passed": bool(sd.get("gate_passed", True)),
            "gate_reason": _to_text(sd.get("gate_reason")).strip(),
            "process_params": _as_dict(sd.get("process_params")),
            "signatures": _as_list(sd.get("signatures")),
            "photos": _as_list(sd.get("photos")),
            "created_at": _to_text(sd.get("created_at") or row.get("created_at")).strip(),
            "proof_id": _to_text(row.get("proof_id")).strip(),
            "proof_hash": _to_text(row.get("proof_hash")).strip(),
        }
    return EquipmentTrip.model_validate(payload)


def register_tool_asset(*, sb: Any, body: ToolAssetRegisterRequest, commit: bool = True) -> ToolAsset:
    asset = ToolAsset(
        v_uri=_to_text(body.v_uri).strip(),
        project_uri=_to_text(body.project_uri).strip().rstrip("/"),
        name=_to_text(body.name).strip(),
        model_no=_to_text(body.model_no).strip(),
        asset_mode=body.asset_mode,
        equipment_manager_uri=_to_text(body.equipment_manager_uri).strip(),
        calibration_cert_no=_to_text(body.calibration_cert_no).strip(),
        calibration_valid_until=body.calibration_valid_until,
        annual_inspection_status=body.annual_inspection_status,
        annual_inspection_valid_until=body.annual_inspection_valid_until,
        operator_skill_required=[_to_text(x).strip().lower() for x in body.operator_skill_required if _to_text(x).strip()],
        maintenance_status=body.maintenance_status,
        maintenance_due_at=body.maintenance_due_at,
        rental_shift_rate=float(body.rental_shift_rate or 0.0),
        purchase_price=float(body.purchase_price or 0.0),
        depreciation_years=float(body.depreciation_years or 8.0),
        annual_work_hours=float(body.annual_work_hours or 2000.0),
        status=body.status,
        metadata=_as_dict(body.metadata),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    if not asset.v_uri:
        raise HTTPException(status_code=422, detail="equipment_uri_required")
    if not asset.project_uri:
        raise HTTPException(status_code=422, detail="project_uri_required")
    if not asset.name:
        raise HTTPException(status_code=422, detail="equipment_name_required")
    return _persist_asset(
        sb=sb,
        asset=asset,
        owner_uri=body.owner_uri,
        signer_uri=body.executor_uri,
        commit=bool(commit),
    )


def _build_status(asset: ToolAsset, operator_row: dict[str, Any] | None = None) -> ToolAssetStatusResult:
    reasons = _equipment_gate(asset, operator_row)
    warnings = _equipment_warnings(asset)
    return ToolAssetStatusResult(
        equipment_uri=asset.v_uri,
        ready=len(reasons) == 0,
        status=asset.status,
        calibration_valid_until=asset.calibration_valid_until,
        annual_inspection_status=asset.annual_inspection_status,
        annual_inspection_valid_until=asset.annual_inspection_valid_until,
        maintenance_status=asset.maintenance_status,
        maintenance_due_at=asset.maintenance_due_at,
        warnings=warnings,
        gate_reasons=reasons,
        asset=asset,
    )


async def get_equipment_status(*, sb: Any, equipment_uri: str, operator_executor_uri: str = "") -> ToolAssetStatusResult:
    row = _latest_asset_row(sb=sb, equipment_uri=equipment_uri)
    if row is None:
        raise HTTPException(status_code=404, detail=f"equipment_not_found: {equipment_uri}")
    asset = _asset_from_row(row)
    operator = _load_executor_row(sb=sb, executor_uri=operator_executor_uri) if _to_text(operator_executor_uri).strip() else None
    status = _build_status(asset, operator)
    if status.warnings:
        await _send_equipment_alert(
            sb=sb,
            project_uri=asset.project_uri,
            equipment_uri=asset.v_uri,
            warnings=status.warnings,
            manager_uri=asset.equipment_manager_uri,
        )
    return status


def _compute_machine_cost(*, asset: ToolAsset, req: EquipmentTripRequest) -> tuple[float, float, float, float]:
    work_hours = float(req.work_hours or 0.0)
    shift_count = float(req.shift_count or 0.0)
    if work_hours <= 0 and shift_count > 0:
        work_hours = shift_count * 8.0
    if shift_count <= 0 and work_hours > 0:
        shift_count = work_hours / 8.0

    unit_rate = float(req.unit_rate or 0.0)
    rental_cost = 0.0
    depreciation_cost = 0.0
    mode = asset.asset_mode
    if mode == "rental":
        rate = unit_rate if unit_rate > 0 else float(asset.rental_shift_rate or 0.0)
        rental_cost = round(rate * shift_count, 6)
        unit_rate = rate
    else:
        years = max(float(asset.depreciation_years or 0.0), 0.1)
        annual_hours = max(float(asset.annual_work_hours or 0.0), 1.0)
        annual_dep = float(asset.purchase_price or 0.0) / years
        depreciation_cost = round(annual_dep * (work_hours / annual_hours), 6)
    machine_cost = round(rental_cost + depreciation_cost, 6)
    return work_hours, shift_count, unit_rate, machine_cost


def _insert_gate_trip(*, sb: Any, trip: EquipmentTrip) -> None:
    if sb is None:
        return
    executor_name = _to_text(trip.signatures[0].signer_name).strip() if trip.signatures else ""
    sb.table("gate_trips").insert(
        {
            "trip_uri": trip.trip_uri,
            "doc_id": f"EQUIP-{_safe_uri_token(trip.component_uri)}-{_safe_uri_token(trip.equipment_uri)}",
            "body_hash": trip.proof_hash,
            "executor_uri": trip.operator_executor_uri,
            "executor_name": executor_name,
            "dto_role": "constructor",
            "trip_role": trip.trip_role,
            "action": "equipment_use",
            "sig_data": trip.signatures[0].sig_data if trip.signatures else "",
            "signed_at": trip.created_at.isoformat(),
            "verified": trip.gate_passed,
            "metadata": {
                "component_uri": trip.component_uri,
                "equipment_uri": trip.equipment_uri,
                "machine_cost": trip.machine_cost,
                "gate_reason": trip.gate_reason,
            },
            "created_at": _utc_now().isoformat(),
        }
    ).execute()


def _insert_settlement(*, sb: Any, trip: EquipmentTrip) -> None:
    if sb is None:
        return
    if float(trip.machine_cost or 0.0) <= 0:
        return
    sb.table("railpact_settlements").insert(
        {
            "trip_uri": trip.trip_uri,
            "executor_uri": trip.operator_executor_uri,
            "doc_id": f"EQUIP-COST-{_safe_uri_token(trip.component_uri)}",
            "amount": float(trip.machine_cost),
            "energy_delta": 0,
            "settled_at": _utc_now().isoformat(),
            "metadata": {
                "kind": "equipment_trip_machine",
                "component_uri": trip.component_uri,
                "equipment_uri": trip.equipment_uri,
                "mode": trip.mode,
                "rental_cost": trip.rental_cost,
                "depreciation_cost": trip.depreciation_cost,
            },
        }
    ).execute()


def _persist_trip(*, sb: Any, trip: EquipmentTrip, owner_uri: str, commit: bool) -> EquipmentTrip:
    state_data = {
        "proof_kind": "equipment_trip",
        **trip.model_dump(mode="json"),
    }
    payload_hash = hashlib.sha256(_serialize_for_hash(state_data).encode("utf-8")).hexdigest()
    proof_id = f"GP-EQUIP-TRIP-{_sha16(f'{trip.trip_uri}:{payload_hash}:{trip.created_at.isoformat()}').upper()}"
    if bool(commit) and sb is not None:
        row = ProofUTXOEngine(sb).create(
            proof_id=proof_id,
            owner_uri=_to_text(owner_uri).strip() or f"{trip.project_uri}/role/system/",
            project_uri=trip.project_uri,
            proof_type="inspection",
            result="PASS" if trip.gate_passed else "FAIL",
            state_data={**state_data, "data_hash": payload_hash},
            norm_uri="v://norm/NormPeg/EquipmentTrip/1.0",
            segment_uri=f"{trip.component_uri}/equipment/{_safe_uri_token(trip.equipment_uri)}",
            signer_uri=trip.operator_executor_uri,
            signer_role="EQUIPMENT",
        )
        trip.proof_id = _to_text(row.get("proof_id")).strip() or proof_id
        trip.proof_hash = _to_text(row.get("proof_hash")).strip() or payload_hash
        _insert_gate_trip(sb=sb, trip=trip)
        _insert_settlement(sb=sb, trip=trip)
    else:
        trip.proof_id = proof_id
        trip.proof_hash = payload_hash
    return trip


async def submit_equipment_trip(*, sb: Any, body: EquipmentTripRequest, commit: bool = True) -> EquipmentTripSubmitResult:
    row = _latest_asset_row(sb=sb, equipment_uri=body.equipment_uri)
    if row is None:
        raise HTTPException(status_code=404, detail=f"equipment_not_found: {body.equipment_uri}")
    asset = _asset_from_row(row)
    operator = _load_executor_row(sb=sb, executor_uri=body.operator_executor_uri)
    status = _build_status(asset, operator)
    if not status.ready:
        raise HTTPException(status_code=409, detail=f"equipment_gate_failed: {', '.join(status.gate_reasons)}")

    now = _utc_now()
    trip_uri = f"{asset.project_uri}/trip/{now.strftime('%Y/%m%d')}/ETRIP-{uuid4().hex[:8].upper()}"
    work_hours, shift_count, unit_rate, machine_cost = _compute_machine_cost(asset=asset, req=body)
    rental_cost = machine_cost if asset.asset_mode == "rental" else 0.0
    depreciation_cost = machine_cost if asset.asset_mode == "owned" else 0.0
    signatures = _build_signature(body.operator_executor_uri, body.signatures)
    trip = EquipmentTrip(
        trip_uri=trip_uri,
        project_uri=asset.project_uri,
        component_uri=_to_text(body.component_uri).strip().rstrip("/"),
        equipment_uri=asset.v_uri,
        equipment_name=asset.name,
        trip_role=_to_text(body.trip_role).strip() or "equipment.shift",
        operator_executor_uri=_to_text(body.operator_executor_uri).strip(),
        work_hours=work_hours,
        shift_count=shift_count,
        mode=asset.asset_mode,
        unit_rate=unit_rate,
        rental_cost=round(rental_cost, 6),
        depreciation_cost=round(depreciation_cost, 6),
        machine_cost=round(machine_cost, 6),
        gate_passed=True,
        gate_reason="",
        process_params=_as_dict(body.process_params),
        signatures=signatures,
        photos=[_to_text(item).strip() for item in body.photos if _to_text(item).strip()],
        created_at=now,
    )
    trip = _persist_trip(sb=sb, trip=trip, owner_uri=body.owner_uri, commit=bool(commit))

    warnings = status.warnings
    if warnings:
        await _send_equipment_alert(
            sb=sb,
            project_uri=asset.project_uri,
            equipment_uri=asset.v_uri,
            warnings=warnings,
            manager_uri=asset.equipment_manager_uri,
        )
    return EquipmentTripSubmitResult(
        ok=True,
        trip=trip,
        gate_passed=True,
        gate_reason="",
        equipment_status=status,
        warnings=warnings,
    )


async def get_equipment_history(*, sb: Any, equipment_uri: str) -> EquipmentHistoryResult:
    latest = _latest_asset_row(sb=sb, equipment_uri=equipment_uri)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"equipment_not_found: {equipment_uri}")
    asset = _asset_from_row(latest)
    trip_rows = _list_equipment_trip_rows(sb=sb, equipment_uri=equipment_uri)
    asset_rows = _list_asset_rows(sb=sb, equipment_uri=equipment_uri)
    status = _build_status(asset, None)
    if status.warnings:
        await _send_equipment_alert(
            sb=sb,
            project_uri=asset.project_uri,
            equipment_uri=asset.v_uri,
            warnings=status.warnings,
            manager_uri=asset.equipment_manager_uri,
        )
    return EquipmentHistoryResult(
        equipment_uri=_to_text(equipment_uri).strip(),
        trips=[_trip_from_row(row) for row in trip_rows],
        asset_snapshots=[_asset_from_row(row) for row in asset_rows],
        warnings=status.warnings,
    )


def sum_equipment_trip_cost(*, sb: Any, component_uri: str) -> dict[str, Any]:
    rows = _list_equipment_trip_rows(sb=sb, component_uri=component_uri)
    total = 0.0
    refs: list[str] = []
    by_mode: dict[str, float] = {"rental": 0.0, "owned": 0.0}
    for row in rows:
        trip = _trip_from_row(row)
        total += float(trip.machine_cost or 0.0)
        refs.append(_to_text(trip.proof_id).strip())
        by_mode[trip.mode] = float(by_mode.get(trip.mode) or 0.0) + float(trip.machine_cost or 0.0)
    return {
        "total_equipment_cost": round(total, 6),
        "proof_refs": [item for item in refs if item],
        "by_mode": {key: round(value, 6) for key, value in by_mode.items()},
    }


__all__ = [
    "register_tool_asset",
    "submit_equipment_trip",
    "get_equipment_status",
    "get_equipment_history",
    "sum_equipment_trip_cost",
]

