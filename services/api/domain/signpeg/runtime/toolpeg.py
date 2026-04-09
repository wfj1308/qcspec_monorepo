"""ToolPeg runtime: tool registration, gate validation, usage updates and warnings."""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from fastapi import HTTPException

from services.api.domain.signpeg.models import (
    CapabilitySpec,
    ConsumableSpec,
    ReusableSpec,
    Tool,
    ToolCertificate,
    ToolListItem,
    ToolListResponse,
    ToolMaintainRequest,
    ToolRegisterRequest,
    ToolRetireRequest,
    ToolStatusResponse,
    ToolUseRequest,
    ToolUseResponse,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _normalize_uri(value: Any) -> str:
    raw = _to_text(value).strip()
    return unquote(raw) if "%" in raw else raw


def _serialize(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    text = _to_text(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii") or text
    text = re.sub(r"[^0-9a-zA-Z_-]+", "-", text).strip("-").lower()
    return text or f"tool-{uuid4().hex[:8]}"


def _proof_id(prefix: str, payload: Any) -> str:
    digest = _sha256_text(_serialize(payload))[:8].upper()
    return f"{prefix}-{digest}"


def _new_tool_id() -> str:
    return f"TOOL-{uuid4().hex[:8].upper()}"


def _build_tool_uri(*, owner_uri: str, tool_code: str) -> str:
    base = _normalize_uri(owner_uri).strip().rstrip("/")
    if not base:
        raise HTTPException(status_code=422, detail="owner_uri_required")
    if not base.startswith("v://"):
        base = f"v://{base.lstrip('/')}"
    return f"{base}/tool/{_slug(tool_code)}"


def _normalize_tool_certificates(certificates: list[ToolCertificate]) -> list[ToolCertificate]:
    out: list[ToolCertificate] = []
    for cert in certificates:
        status = cert.status
        if cert.valid_until < _utc_now().date() and status == "active":
            status = "expired"
        scan_hash = _to_text(cert.scan_hash).strip()
        if not scan_hash:
            seed = f"{cert.cert_type}:{cert.cert_no}:{cert.valid_until.isoformat()}"
            scan_hash = f"sha256:{_sha256_text(seed)}"
        out.append(cert.model_copy(update={"status": status, "scan_hash": scan_hash}))
    return out


def _ensure_tool_certificates_valid(certificates: list[ToolCertificate]) -> None:
    today = _utc_now().date()
    for cert in certificates:
        if cert.status == "revoked":
            raise HTTPException(status_code=422, detail=f"tool_certificate_revoked: {cert.cert_no}")
        if cert.valid_until < today:
            raise HTTPException(status_code=422, detail=f"tool_certificate_expired: {cert.cert_no}")


def _normalize_consumable(spec: ConsumableSpec | None) -> ConsumableSpec | None:
    if spec is None:
        return None
    remaining = float(spec.remaining_qty)
    if remaining <= 0 and float(spec.initial_qty) > 0:
        remaining = float(spec.initial_qty)
    return spec.model_copy(update={"remaining_qty": max(remaining, 0.0)})


def _normalize_reusable(spec: ReusableSpec | None) -> ReusableSpec | None:
    if spec is None:
        return None
    expected = max(int(spec.expected_life), 0)
    current = max(int(spec.current_uses), 0)
    remaining = int(spec.remaining_uses)
    if remaining <= 0 and expected > 0:
        remaining = max(expected - current, 0)
    maintenance_cycle = max(int(spec.maintenance_cycle), 0)
    next_maintenance_at = int(spec.next_maintenance_at)
    if next_maintenance_at <= 0 and maintenance_cycle > 0:
        next_maintenance_at = maintenance_cycle
    depreciation_per_use = float(spec.depreciation_per_use)
    if depreciation_per_use <= 0 and expected > 0 and float(spec.purchase_price) > 0:
        depreciation_per_use = float(spec.purchase_price) / float(expected)
    return spec.model_copy(
        update={
            "remaining_uses": max(remaining, 0),
            "next_maintenance_at": max(next_maintenance_at, 0),
            "depreciation_per_use": float(depreciation_per_use),
        }
    )


def _normalize_capability(spec: CapabilitySpec | None) -> CapabilitySpec | None:
    if spec is None:
        return None
    quota_total = max(int(spec.quota_total), 0)
    quota_used = max(int(spec.quota_used), 0)
    quota_remaining = int(spec.quota_remaining)
    if quota_remaining <= 0 and quota_total > 0:
        quota_remaining = max(quota_total - quota_used, 0)
    return spec.model_copy(update={"quota_total": quota_total, "quota_used": quota_used, "quota_remaining": max(quota_remaining, 0)})


def _tool_from_row(row: dict[str, Any]) -> Tool:
    tool_id = _to_text(row.get("tool_id")).strip() or _to_text(row.get("id")).strip() or _new_tool_id()
    payload = {
        "tool_id": tool_id,
        "tool_uri": _to_text(row.get("tool_uri")).strip(),
        "tool_name": _to_text(row.get("tool_name")).strip(),
        "tool_code": _to_text(row.get("tool_code")).strip(),
        "tool_type": _to_text(row.get("tool_type")).strip() or "reusable",
        "owner_type": _to_text(row.get("owner_type")).strip() or "org",
        "owner_uri": _to_text(row.get("owner_uri")).strip(),
        "project_uri": _to_text(row.get("project_uri")).strip(),
        "certificates": _as_list(row.get("certificates")),
        "tool_energy": _as_dict(row.get("tool_energy")) if row.get("tool_energy") is not None else None,
        "consumable_spec": _as_dict(row.get("consumable_spec")) if row.get("consumable_spec") is not None else None,
        "reusable_spec": _as_dict(row.get("reusable_spec")) if row.get("reusable_spec") is not None else None,
        "capability_spec": _as_dict(row.get("capability_spec")) if row.get("capability_spec") is not None else None,
        "status": _to_text(row.get("status")).strip() or "available",
        "use_history": [_to_text(x).strip() for x in _as_list(row.get("use_history")) if _to_text(x).strip()],
        "registration_proof": _to_text(row.get("registration_proof")).strip(),
        "registered_at": _to_text(row.get("registered_at")).strip() or _utc_now().isoformat(),
        "updated_at": _to_text(row.get("updated_at")).strip() or _utc_now().isoformat(),
    }
    tool = Tool.model_validate(payload)
    return tool.model_copy(
        update={
            "certificates": _normalize_tool_certificates(tool.certificates),
            "consumable_spec": _normalize_consumable(tool.consumable_spec),
            "reusable_spec": _normalize_reusable(tool.reusable_spec),
            "capability_spec": _normalize_capability(tool.capability_spec),
        }
    )


def _tool_to_payload(tool: Tool) -> dict[str, Any]:
    return {
        "tool_id": tool.tool_id,
        "tool_uri": tool.tool_uri,
        "tool_name": tool.tool_name,
        "tool_code": tool.tool_code,
        "tool_type": tool.tool_type,
        "owner_type": tool.owner_type,
        "owner_uri": tool.owner_uri,
        "project_uri": tool.project_uri,
        "certificates": [item.model_dump(mode="json") for item in tool.certificates],
        "tool_energy": tool.tool_energy.model_dump(mode="json") if tool.tool_energy else None,
        "consumable_spec": tool.consumable_spec.model_dump(mode="json") if tool.consumable_spec else None,
        "reusable_spec": tool.reusable_spec.model_dump(mode="json") if tool.reusable_spec else None,
        "capability_spec": tool.capability_spec.model_dump(mode="json") if tool.capability_spec else None,
        "status": tool.status,
        "use_history": list(tool.use_history),
        "registration_proof": tool.registration_proof,
        "registered_at": tool.registered_at.isoformat(),
        "updated_at": tool.updated_at.isoformat(),
    }


def _list_tool_rows(sb: Any) -> list[dict[str, Any]]:
    rows = sb.table("san_tools").select("*").limit(5000).execute().data or []
    return [row for row in rows if isinstance(row, dict)]


def _get_tool_row_by_id(sb: Any, tool_id: str) -> dict[str, Any] | None:
    token = _to_text(tool_id).strip()
    if not token:
        return None
    rows = sb.table("san_tools").select("*").eq("tool_id", token).limit(1).execute().data or []
    if rows and isinstance(rows[0], dict):
        return rows[0]
    for row in _list_tool_rows(sb):
        if _to_text(row.get("tool_id")).strip() == token:
            return row
    return None


def _get_tool_row_by_uri(sb: Any, tool_uri: str) -> dict[str, Any] | None:
    token = _normalize_uri(tool_uri).strip()
    if not token:
        return None
    rows = sb.table("san_tools").select("*").eq("tool_uri", token).limit(1).execute().data or []
    if rows and isinstance(rows[0], dict):
        return rows[0]
    for row in _list_tool_rows(sb):
        if _normalize_uri(row.get("tool_uri")).strip() == token:
            return row
    return None


def _get_tool_by_id(sb: Any, tool_id: str) -> Tool:
    row = _get_tool_row_by_id(sb, tool_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"tool_not_found: {tool_id}")
    return _tool_from_row(row)


def _get_tool_by_uri(sb: Any, tool_uri: str) -> Tool:
    row = _get_tool_row_by_uri(sb, tool_uri)
    if not row:
        raise HTTPException(status_code=404, detail=f"tool_not_found: {tool_uri}")
    return _tool_from_row(row)


def _upsert_tool(sb: Any, tool: Tool) -> None:
    payload = _tool_to_payload(tool)
    sb.table("san_tools").upsert(payload, on_conflict="tool_uri").execute()


def _insert_tool_alert(
    sb: Any,
    *,
    tool_id: str,
    tool_uri: str,
    owner_uri: str,
    alert_type: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    try:
        sb.table("san_tool_alerts").insert(
            {
                "tool_id": tool_id,
                "tool_uri": tool_uri,
                "owner_uri": owner_uri,
                "alert_type": alert_type,
                "message": message,
                "data": data or {},
                "created_at": _utc_now().isoformat(),
            }
        ).execute()
    except Exception:
        return


def _insert_railpact_tool_entry(
    sb: Any,
    *,
    trip_uri: str,
    doc_id: str,
    owner_uri: str,
    amount: float,
    metadata: dict[str, Any],
) -> None:
    if float(amount) <= 0:
        return
    sb.table("railpact_settlements").insert(
        {
            "trip_uri": trip_uri,
            "executor_uri": owner_uri,
            "doc_id": doc_id,
            "amount": float(amount),
            "energy_delta": 1,
            "settled_at": _utc_now().isoformat(),
            "metadata": metadata,
        }
    ).execute()


def _tool_registration_proof(payload: dict[str, Any]) -> str:
    return _proof_id("PROOF-TOOL", payload)


def register_tool(sb: Any, body: ToolRegisterRequest) -> Tool:
    normalized_certs = _normalize_tool_certificates(body.certificates)
    _ensure_tool_certificates_valid(normalized_certs)
    tool_id = _new_tool_id()
    tool_uri = _build_tool_uri(owner_uri=body.owner_uri, tool_code=body.tool_code)
    registration_payload = {
        "tool_id": tool_id,
        "tool_uri": tool_uri,
        "tool_name": body.tool_name,
        "tool_code": body.tool_code,
        "tool_type": body.tool_type,
        "owner_type": body.owner_type,
        "owner_uri": body.owner_uri,
        "project_uri": body.project_uri,
        "certificates": [item.model_dump(mode="json") for item in normalized_certs],
    }
    registration_proof = _tool_registration_proof(registration_payload)
    tool = Tool(
        tool_id=tool_id,
        tool_uri=tool_uri,
        tool_name=body.tool_name,
        tool_code=body.tool_code,
        tool_type=body.tool_type,
        owner_type=body.owner_type,
        owner_uri=body.owner_uri,
        project_uri=body.project_uri,
        certificates=normalized_certs,
        tool_energy=body.tool_energy,
        consumable_spec=_normalize_consumable(body.consumable_spec),
        reusable_spec=_normalize_reusable(body.reusable_spec),
        capability_spec=_normalize_capability(body.capability_spec),
        status="available",
        use_history=[registration_proof],
        registration_proof=registration_proof,
        registered_at=_utc_now(),
        updated_at=_utc_now(),
    )
    _upsert_tool(sb, tool)
    return tool


def get_tool(sb: Any, tool_id: str) -> Tool:
    return _get_tool_by_id(sb, tool_id)


def get_tool_status(sb: Any, tool_id: str) -> ToolStatusResponse:
    tool = _get_tool_by_id(sb, tool_id)
    return ToolStatusResponse(
        tool_id=tool.tool_id,
        tool_uri=tool.tool_uri,
        status=tool.status,
        certificates_valid=tool.certificates_valid(),
        remaining_life=tool.reusable_spec.remaining_uses if tool.reusable_spec else None,
        remaining_qty=tool.consumable_spec.remaining_qty if tool.consumable_spec else None,
        quota_remaining=tool.capability_spec.quota_remaining if tool.capability_spec else None,
        expiring_soon=tool.expiring_certificates(within_days=30),
    )


def list_tools(
    sb: Any,
    *,
    project_uri: str = "",
    owner_uri: str = "",
    tool_type: str = "",
    status: str = "",
) -> ToolListResponse:
    p = _normalize_uri(project_uri).strip().rstrip("/")
    o = _normalize_uri(owner_uri).strip().rstrip("/")
    t = _to_text(tool_type).strip().lower()
    s = _to_text(status).strip().lower()
    items: list[ToolListItem] = []
    for row in _list_tool_rows(sb):
        tool = _tool_from_row(row)
        if p and _normalize_uri(tool.project_uri).strip().rstrip("/") != p:
            continue
        if o and _normalize_uri(tool.owner_uri).strip().rstrip("/") != o:
            continue
        if t and _to_text(tool.tool_type).strip().lower() != t:
            continue
        if s and _to_text(tool.status).strip().lower() != s:
            continue
        items.append(
            ToolListItem(
                tool_id=tool.tool_id,
                tool_uri=tool.tool_uri,
                tool_name=tool.tool_name,
                tool_type=tool.tool_type,
                status=tool.status,
                owner_uri=tool.owner_uri,
                project_uri=tool.project_uri,
                certificates_valid=tool.certificates_valid(),
                remaining_life=tool.reusable_spec.remaining_uses if tool.reusable_spec else None,
                remaining_qty=tool.consumable_spec.remaining_qty if tool.consumable_spec else None,
                quota_remaining=tool.capability_spec.quota_remaining if tool.capability_spec else None,
            )
        )
    items.sort(key=lambda item: (item.status not in {"available", "in_use"}, item.tool_name))
    return ToolListResponse(items=items)


def validate_tool(
    sb: Any,
    *,
    tool_uri: str,
    trip_role: str,
    consumed_qty: float = 0.0,
    tokens_used: int = 0,
) -> dict[str, Any]:
    tool = _get_tool_by_uri(sb, tool_uri)
    today = _utc_now().date()
    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "item": f"{tool.tool_name}状态",
            "check": _to_text(tool.status).strip().lower() in {"available", "in_use"},
            "message": f"工具状态：{tool.status}",
        }
    )

    for cert in tool.certificates:
        checks.append(
            {
                "item": cert.cert_type,
                "check": cert.is_valid_on(today),
                "message": f"{cert.cert_type}已于{cert.valid_until.isoformat()}过期",
            }
        )

    if tool.consumable_spec:
        required = max(float(consumed_qty or 0.0), 0.0)
        if required <= 0:
            required = 1.0
        checks.append(
            {
                "item": "余量检查",
                "check": float(tool.consumable_spec.remaining_qty) >= required,
                "message": "消耗品已耗尽或余量不足，请补充",
            }
        )

    if tool.reusable_spec:
        checks.append(
            {
                "item": "寿命检查",
                "check": int(tool.reusable_spec.remaining_uses) > 0,
                "message": "已达使用寿命上限，需要更换",
            }
        )
        checks.append(
            {
                "item": "维保检查",
                "check": int(tool.reusable_spec.current_uses) < int(tool.reusable_spec.next_maintenance_at or 0)
                if int(tool.reusable_spec.maintenance_cycle or 0) > 0
                else True,
                "message": "已到维保周期，请先完成维保",
            }
        )

    if tool.capability_spec:
        need_tokens = max(int(tokens_used or 0), 0)
        checks.append(
            {
                "item": "配额检查",
                "check": int(tool.capability_spec.quota_remaining) > need_tokens if need_tokens > 0 else int(tool.capability_spec.quota_remaining) > 0,
                "message": "API配额已耗尽，请充值",
            }
        )

    passed = all(bool(item.get("check")) for item in checks)
    return {
        "passed": passed,
        "checks": checks,
        "trip_role": _to_text(trip_role).strip(),
        "tool": tool,
    }


def _calc_tool_cost_entries(sb: Any, *, tool: Tool, req: ToolUseRequest) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    trip_ref = _to_text(req.trip_uri).strip() or _to_text(req.trip_id).strip() or f"v://tool/{tool.tool_id}/trip/{uuid4().hex[:8]}"
    doc_id = _to_text(req.trip_id).strip() or tool.tool_id

    if tool.tool_energy:
        unit = _to_text(tool.tool_energy.unit).strip().lower()
        units = float(req.shifts or 0.0)
        if unit in {"hour", "hours", "工时"}:
            units = float(req.duration_hours or 0.0)
        elif unit in {"token", "tokens"}:
            units = float(req.tokens_used or 0)
        elif units <= 0:
            units = 1.0
        amount = units * float(tool.tool_energy.rate or 0.0) * float(tool.tool_energy.cost_per_unit or 0.0)
        entry = {
            "smu_type": _to_text(tool.tool_energy.smu_type).strip() or "equipment",
            "amount": float(amount),
            "tool_uri": tool.tool_uri,
            "trip_id": doc_id,
            "direction": "DR",
            "status": "pending",
            "note": f"{tool.tool_name}能耗费",
            "kind": "tool_energy",
        }
        entries.append(entry)
        _insert_railpact_tool_entry(
            sb,
            trip_uri=trip_ref,
            doc_id=doc_id,
            owner_uri=tool.owner_uri,
            amount=float(amount),
            metadata={"kind": "tool_energy", "tool_uri": tool.tool_uri, "trip_role": req.trip_role},
        )

    if tool.reusable_spec:
        depreciation = float(tool.reusable_spec.depreciation_per_use or 0.0)
        if depreciation > 0:
            entry = {
                "smu_type": "depreciation",
                "amount": float(depreciation),
                "tool_uri": tool.tool_uri,
                "trip_id": doc_id,
                "direction": "DR",
                "status": "pending",
                "note": f"{tool.tool_name}折旧",
                "kind": "tool_depreciation",
            }
            entries.append(entry)
            _insert_railpact_tool_entry(
                sb,
                trip_uri=trip_ref,
                doc_id=doc_id,
                owner_uri=tool.owner_uri,
                amount=float(depreciation),
                metadata={"kind": "tool_depreciation", "tool_uri": tool.tool_uri, "trip_role": req.trip_role},
            )

    if tool.consumable_spec:
        consumed = max(float(req.consumed_qty or 0.0), 0.0)
        if consumed <= 0:
            consumed = 1.0
        unit_price = float(tool.consumable_spec.unit_price or 0.0)
        amount = consumed * unit_price
        entry = {
            "smu_type": "consumable",
            "amount": float(amount),
            "tool_uri": tool.tool_uri,
            "trip_id": doc_id,
            "direction": "DR",
            "status": "pending",
            "note": f"{tool.tool_name}消耗品",
            "kind": "tool_consumable",
            "consumed_qty": consumed,
            "unit_price": unit_price,
        }
        entries.append(entry)
        _insert_railpact_tool_entry(
            sb,
            trip_uri=trip_ref,
            doc_id=doc_id,
            owner_uri=tool.owner_uri,
            amount=float(amount),
            metadata={
                "kind": "tool_consumable",
                "tool_uri": tool.tool_uri,
                "trip_role": req.trip_role,
                "consumed_qty": consumed,
                "unit_price": unit_price,
            },
        )

    if tool.capability_spec and int(req.tokens_used or 0) > 0:
        tokens = max(int(req.tokens_used or 0), 0)
        amount = (float(tokens) / 1000.0) * float(tool.capability_spec.cost_per_1k_tokens or 0.0)
        entry = {
            "smu_type": "ai",
            "amount": float(amount),
            "tool_uri": tool.tool_uri,
            "trip_id": doc_id,
            "direction": "DR",
            "status": "pending",
            "note": f"{tool.tool_name}能力调用",
            "kind": "tool_capability",
            "tokens_used": tokens,
        }
        entries.append(entry)
        _insert_railpact_tool_entry(
            sb,
            trip_uri=trip_ref,
            doc_id=doc_id,
            owner_uri=tool.owner_uri,
            amount=float(amount),
            metadata={"kind": "tool_capability", "tool_uri": tool.tool_uri, "trip_role": req.trip_role, "tokens_used": tokens},
        )

    return entries


def use_tool(sb: Any, *, tool_id: str, body: ToolUseRequest) -> ToolUseResponse:
    tool = _get_tool_by_id(sb, tool_id)
    return use_tool_by_uri(
        sb,
        tool_uri=tool.tool_uri,
        body=body,
    )


def use_tool_by_uri(sb: Any, *, tool_uri: str, body: ToolUseRequest) -> ToolUseResponse:
    req = body if isinstance(body, ToolUseRequest) else ToolUseRequest.model_validate(body)
    gate = validate_tool(
        sb,
        tool_uri=tool_uri,
        trip_role=req.trip_role,
        consumed_qty=float(req.consumed_qty or 0.0),
        tokens_used=int(req.tokens_used or 0),
    )
    if not bool(gate.get("passed")):
        first = next((item for item in gate.get("checks") or [] if not bool(item.get("check"))), None)
        message = _to_text((first or {}).get("message")).strip() or "tool_gate_failed"
        raise HTTPException(status_code=409, detail=message)

    tool: Tool = gate["tool"]
    now = _utc_now()
    status = _to_text(tool.status).strip().lower() or "available"
    use_history = list(tool.use_history)
    trip_ref = _to_text(req.trip_uri).strip() or _to_text(req.trip_id).strip()
    if trip_ref:
        use_history.append(trip_ref)

    consumable = tool.consumable_spec
    reusable = tool.reusable_spec
    capability = tool.capability_spec

    if consumable:
        consumed = max(float(req.consumed_qty or 0.0), 0.0)
        if consumed <= 0:
            consumed = 1.0
        consumable = consumable.model_copy(update={"remaining_qty": max(float(consumable.remaining_qty) - consumed, 0.0)})
        if float(consumable.remaining_qty) <= 0:
            status = "depleted"

    if reusable:
        uses_delta = max(int(req.shifts or 0), 1)
        current_uses = max(int(reusable.current_uses) + uses_delta, 0)
        remaining_uses = max(int(reusable.expected_life) - current_uses, 0)
        next_maintenance_at = int(reusable.next_maintenance_at or 0)
        if next_maintenance_at <= 0 and int(reusable.maintenance_cycle or 0) > 0:
            next_maintenance_at = int(reusable.maintenance_cycle)
        reusable = reusable.model_copy(
            update={
                "current_uses": current_uses,
                "remaining_uses": remaining_uses,
                "next_maintenance_at": next_maintenance_at,
            }
        )
        if remaining_uses <= 0:
            status = "retired"
        elif int(reusable.maintenance_cycle or 0) > 0 and current_uses >= int(reusable.next_maintenance_at or 0):
            status = "maintenance"
        else:
            status = "in_use"

    if capability:
        used = max(int(capability.quota_used) + max(int(req.tokens_used or 0), 0), 0)
        remaining = max(int(capability.quota_total) - used, 0)
        capability = capability.model_copy(update={"quota_used": used, "quota_remaining": remaining})
        if remaining <= 0:
            status = "depleted"
        else:
            status = "in_use"

    updated = tool.model_copy(
        update={
            "consumable_spec": consumable,
            "reusable_spec": reusable,
            "capability_spec": capability,
            "status": status,
            "use_history": use_history,
            "updated_at": now,
        }
    )
    _upsert_tool(sb, updated)
    smu_entries = _calc_tool_cost_entries(sb, tool=updated, req=req)
    return ToolUseResponse(
        ok=True,
        tool=updated,
        smu_entries=smu_entries,
        gate_result={"passed": True, "checks": gate.get("checks") or []},
    )


def maintain_tool(sb: Any, *, tool_id: str, body: ToolMaintainRequest) -> dict[str, Any]:
    req = body if isinstance(body, ToolMaintainRequest) else ToolMaintainRequest.model_validate(body)
    tool = _get_tool_by_id(sb, tool_id)
    reusable = tool.reusable_spec
    if reusable:
        maintenance_cycle = max(int(reusable.maintenance_cycle), 0)
        next_maintenance_at = int(reusable.current_uses) + maintenance_cycle if maintenance_cycle > 0 else int(reusable.next_maintenance_at)
        reusable = reusable.model_copy(update={"last_maintenance": req.performed_at.date(), "next_maintenance_at": next_maintenance_at})
    updated = tool.model_copy(
        update={
            "reusable_spec": reusable,
            "status": "available" if _to_text(tool.status).strip().lower() != "retired" else "retired",
            "updated_at": _utc_now(),
        }
    )
    _upsert_tool(sb, updated)
    proof = _proof_id(
        "PROOF-TOOL-MAINT",
        {
            "tool_uri": updated.tool_uri,
            "performed_at": req.performed_at.isoformat(),
            "note": req.note,
        },
    )
    return {"ok": True, "tool": updated.model_dump(mode="json"), "maintenance_proof": proof}


def retire_tool(sb: Any, *, tool_id: str, body: ToolRetireRequest) -> dict[str, Any]:
    _ = body if isinstance(body, ToolRetireRequest) else ToolRetireRequest.model_validate(body)
    tool = _get_tool_by_id(sb, tool_id)
    updated = tool.model_copy(update={"status": "retired", "updated_at": _utc_now()})
    _upsert_tool(sb, updated)
    return {"ok": True, "tool": updated.model_dump(mode="json")}


def check_tool_status(sb: Any) -> dict[str, Any]:
    today = _utc_now().date()
    suspended: list[str] = []
    warnings: list[dict[str, Any]] = []
    for row in _list_tool_rows(sb):
        tool = _tool_from_row(row)
        changed = False

        updated_certs: list[ToolCertificate] = []
        for cert in tool.certificates:
            days = (cert.valid_until - today).days
            c = cert
            if days <= 0:
                c = cert.model_copy(update={"status": "expired"})
                if _to_text(tool.status).strip().lower() not in {"retired"}:
                    tool.status = "suspended"
                    changed = True
                suspended.append(tool.tool_uri)
                _insert_tool_alert(
                    sb,
                    tool_id=tool.tool_id,
                    tool_uri=tool.tool_uri,
                    owner_uri=tool.owner_uri,
                    alert_type="certificate_expired",
                    message=f"{tool.tool_name} {cert.cert_type}已过期",
                    data=cert.model_dump(mode="json"),
                )
                changed = True
            elif 0 < days <= 30 and cert.status == "active":
                warnings.append({"tool_uri": tool.tool_uri, "cert_type": cert.cert_type, "days_left": days})
                _insert_tool_alert(
                    sb,
                    tool_id=tool.tool_id,
                    tool_uri=tool.tool_uri,
                    owner_uri=tool.owner_uri,
                    alert_type="certificate_expiring",
                    message=f"{tool.tool_name} {cert.cert_type}将在{days}天后到期",
                    data=cert.model_dump(mode="json"),
                )
            updated_certs.append(c)
        tool.certificates = updated_certs

        if tool.consumable_spec:
            if float(tool.consumable_spec.remaining_qty) <= float(tool.consumable_spec.replenish_threshold):
                warnings.append({"tool_uri": tool.tool_uri, "type": "inventory_low", "remaining_qty": tool.consumable_spec.remaining_qty})
                _insert_tool_alert(
                    sb,
                    tool_id=tool.tool_id,
                    tool_uri=tool.tool_uri,
                    owner_uri=tool.owner_uri,
                    alert_type="inventory_low",
                    message=f"{tool.tool_name}库存不足：剩余{tool.consumable_spec.remaining_qty}{tool.consumable_spec.unit}",
                    data=tool.consumable_spec.model_dump(mode="json"),
                )

        if tool.reusable_spec and int(tool.reusable_spec.maintenance_cycle or 0) > 0:
            uses_to_maintenance = int(tool.reusable_spec.next_maintenance_at) - int(tool.reusable_spec.current_uses)
            if uses_to_maintenance <= 5:
                warnings.append({"tool_uri": tool.tool_uri, "type": "maintenance_due", "uses_to_maintenance": uses_to_maintenance})
                _insert_tool_alert(
                    sb,
                    tool_id=tool.tool_id,
                    tool_uri=tool.tool_uri,
                    owner_uri=tool.owner_uri,
                    alert_type="maintenance_due",
                    message=f"{tool.tool_name}即将到维保周期：还剩{uses_to_maintenance}次",
                    data=tool.reusable_spec.model_dump(mode="json"),
                )

        if changed:
            _upsert_tool(sb, tool.model_copy(update={"updated_at": _utc_now()}))

    return {"ok": True, "suspended": suspended, "warnings": warnings}


__all__ = [
    "register_tool",
    "get_tool",
    "get_tool_status",
    "list_tools",
    "validate_tool",
    "use_tool",
    "use_tool_by_uri",
    "maintain_tool",
    "retire_tool",
    "check_tool_status",
]
