"""SignPeg runtime: executor registry, signing, verification, status."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from fastapi import HTTPException

from services.api.domain.signpeg.models import (
    CapabilityDetail,
    CapacitySpec,
    Certificate,
    CertificateAddRequest,
    ConsumableDetail,
    Delegation,
    EnergyProfile,
    EnergySpec,
    ExecutorMaintainRequest,
    Executor,
    ExecutorCreateRequest,
    OrgMemberAddRequest,
    OrgProjectAddRequest,
    OrgSpec,
    ExecutorUseRequest,
    ExecutorListItem,
    ExecutorListResponse,
    ExecutorRecord,
    ExecutorRegisterRequest,
    ExecutorSearchRequest,
    ExecutorStatusResponse,
    ExecutorSummary,
    HolderChangeRequest,
    HolderHistoryItem,
    RailPactEntry,
    RequiresAddRequest,
    ReusableDetail,
    SignPegRequest,
    SignPegResult,
    SignStatusItem,
    SignStatusResponse,
    SkillAddRequest,
    ToolUseRequest,
    ToolSpec,
    VerifyRequest,
    VerifyResponse,
)
from services.api.domain.signpeg.runtime.scheduler import ExecutorScheduler, NoAvailableExecutorError
from services.api.domain.signpeg.runtime.toolpeg import (
    use_tool_by_uri,
    validate_tool as validate_tool_gate,
)


SIGN_FLOW_ROLES = ("inspector", "recorder", "reviewer", "constructor", "supervisor")
ROLE_TO_REQUIRED_SKILL = {
    "inspector": "inspection",
    "recorder": "record",
    "reviewer": "review",
    "constructor": "construction",
    "supervisor": "bridge-inspection",
}


def _validate_ca_requirement(*, signature_mode: str, ca_provider: str, ca_signature_id: str) -> None:
    mode = _to_text(signature_mode).strip().lower() or "process"
    if mode != "archive":
        return
    if not _to_text(ca_provider).strip():
        raise HTTPException(status_code=422, detail="ca_provider_required_for_archive")
    if not _to_text(ca_signature_id).strip():
        raise HTTPException(status_code=422, detail="ca_signature_id_required_for_archive")


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_uri(value: Any) -> str:
    raw = _to_text(value).strip()
    return unquote(raw) if "%" in raw else raw


def _normalize_org_uri(value: Any) -> str:
    uri = _normalize_uri(value).strip()
    if not uri:
        return ""
    if not uri.startswith("v://"):
        uri = f"v://{uri.lstrip('/')}"
    return uri.rstrip("/")


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _serialize(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _proof_id(prefix: str, payload: Any) -> str:
    digest = _sha256_text(_serialize(payload))[:8].upper()
    return f"{prefix}-{digest}"


def _slug_name(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return f"executor-{uuid4().hex[:8]}"
    try:
        from pypinyin import lazy_pinyin  # type: ignore

        py = "-".join([item for item in lazy_pinyin(text) if item]).strip("-")
        if py:
            text = py
    except Exception:
        pass
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii") or text
    text = re.sub(r"[^0-9a-zA-Z_-]+", "-", text).strip("-").lower()
    if not text:
        return f"executor-{_sha256_text(str(raw))[:8]}"
    return text


def _executor_status_default(value: str) -> str:
    status = str(value or "").strip().lower()
    if status in {"active", "available", "busy", "offline", "suspended", "inactive", "in_use", "maintenance", "depleted", "retired"}:
        return status
    return "available"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = _to_text(value).strip()
    if not text:
        return _utc_now()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _executor_from_row(row: dict[str, Any]) -> Executor:
    energy_payload = _as_dict(row.get("energy"))
    capacity_payload = _as_dict(row.get("capacity"))
    certificates_payload = _as_list(row.get("certificates"))
    proof_history_payload = [str(item).strip() for item in _as_list(row.get("proof_history")) if str(item).strip()]
    derived_id = _to_text(row.get("executor_id")).strip() or _to_text(row.get("id")).strip()
    if not derived_id:
        derived_id = f"EXEC-{_sha256_text(_to_text(row.get('executor_uri')).strip() or 'unknown')[:8].upper()}"
    payload = {
        "executor_id": derived_id,
        "executor_uri": _normalize_uri(_to_text(row.get("executor_uri")).strip()),
        "executor_type": _to_text(row.get("executor_type")).strip() or "human",
        "name": _to_text(row.get("name")).strip(),
        "org_uri": _normalize_org_uri(_to_text(row.get("org_uri")).strip()),
        "capacity": capacity_payload,
        "certificates": certificates_payload,
        "energy": energy_payload,
        "skills": _as_list(row.get("skills")),
        "requires": [_normalize_uri(x) for x in _as_list(row.get("requires")) if _to_text(x).strip()],
        "used_by": [_normalize_uri(x) for x in _as_list(row.get("used_by")) if _to_text(x).strip()],
        "tool_spec": _as_dict(row.get("tool_spec")) if row.get("tool_spec") is not None else None,
        "org_spec": _as_dict(row.get("org_spec")) if row.get("org_spec") is not None else None,
        "business_license_file": _to_text(row.get("business_license_file")).strip(),
        "status": _executor_status_default(_to_text(row.get("status")).strip()),
        "registration_proof": _to_text(row.get("registration_proof")).strip(),
        "proof_history": proof_history_payload,
        "registered_at": _to_text(row.get("registered_at")).strip() or _utc_now().isoformat(),
        "last_active": _to_text(row.get("last_active")).strip() or _utc_now().isoformat(),
        "trip_count": int(row.get("trip_count") or 0),
        "proof_count": int(row.get("proof_count") or 0),
        "holder_name": _to_text(row.get("holder_name")).strip(),
        "holder_id": _to_text(row.get("holder_id")).strip(),
        "holder_since": _to_text(row.get("holder_since")).strip() or _utc_now().isoformat(),
    }
    return Executor.model_validate(payload)


def _get_executor_row(sb: Any, executor_uri: str) -> dict[str, Any] | None:
    uri = _normalize_uri(executor_uri)
    if not uri:
        return None
    rows = (
        sb.table("san_executors")
        .select("*")
        .eq("executor_uri", uri)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        alt = uri.rstrip("/") if uri.endswith("/") else f"{uri}/"
        rows = (
            sb.table("san_executors")
            .select("*")
            .eq("executor_uri", alt)
            .limit(1)
            .execute()
            .data
            or []
        )
    if not rows:
        return None
    row = rows[0]
    return row if isinstance(row, dict) else None


def _get_executor_row_by_id(sb: Any, executor_id: str) -> dict[str, Any] | None:
    token = _to_text(executor_id).strip()
    if not token:
        return None
    rows = (
        sb.table("san_executors")
        .select("*")
        .eq("executor_id", token)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        for row in _list_executor_rows(sb):
            if not isinstance(row, dict):
                continue
            derived = _to_text(row.get("executor_id")).strip() or _to_text(row.get("id")).strip()
            if not derived:
                derived = f"EXEC-{_sha256_text(_to_text(row.get('executor_uri')).strip() or 'unknown')[:8].upper()}"
            if derived == token:
                return row
        return None
    row = rows[0]
    return row if isinstance(row, dict) else None


def _list_executor_rows(sb: Any) -> list[dict[str, Any]]:
    rows = sb.table("san_executors").select("*").limit(5000).execute().data or []
    return [row for row in rows if isinstance(row, dict)]


def _get_executor(sb: Any, executor_uri: str) -> Executor:
    normalized_uri = _normalize_uri(executor_uri)
    row = _get_executor_row(sb, normalized_uri)
    if not row:
        raise HTTPException(status_code=404, detail=f"executor_not_found: {normalized_uri}")
    return _executor_from_row(row)


def _upsert_executor(sb: Any, executor: Executor) -> None:
    executor_id = _to_text(executor.executor_id).strip() or f"EXEC-{_sha256_text(executor.executor_uri)[:8].upper()}"
    payload = {
        "executor_id": executor_id,
        "executor_uri": executor.executor_uri,
        "executor_type": executor.executor_type,
        "name": executor.name,
        "org_uri": executor.org_uri,
        "capacity": executor.capacity.model_dump(mode="json"),
        "certificates": [item.model_dump(mode="json") for item in executor.certificates],
        "energy": executor.energy.model_dump(mode="json"),
        "skills": [item.model_dump(mode="json") for item in executor.skills],
        "requires": list(executor.requires),
        "used_by": list(executor.used_by),
        "tool_spec": executor.tool_spec.model_dump(mode="json") if executor.tool_spec else None,
        "org_spec": executor.org_spec.model_dump(mode="json") if executor.org_spec else None,
        "business_license_file": _to_text(executor.business_license_file).strip(),
        "status": executor.status,
        "registration_proof": executor.registration_proof,
        "proof_history": list(executor.proof_history),
        "registered_at": executor.registered_at.isoformat(),
        "last_active": executor.last_active.isoformat(),
        "trip_count": int(executor.trip_count),
        "proof_count": int(executor.proof_count),
        "holder_name": executor.holder_name,
        "holder_id": executor.holder_id,
        "holder_since": executor.holder_since.isoformat(),
        "updated_at": _utc_now().isoformat(),
    }
    sb.table("san_executors").upsert(payload, on_conflict="executor_uri").execute()


def _insert_holder_history(
    sb: Any,
    *,
    executor_uri: str,
    holder_name: str,
    holder_id: str,
    holder_since: datetime,
    reason: str,
) -> None:
    sb.table("san_executor_holders").insert(
        {
            "executor_uri": executor_uri,
            "holder_name": holder_name,
            "holder_id": holder_id,
            "holder_since": holder_since.isoformat(),
            "changed_at": _utc_now().isoformat(),
            "reason": reason,
        }
    ).execute()


def _list_holder_history(sb: Any, executor_uri: str) -> list[HolderHistoryItem]:
    rows = (
        sb.table("san_executor_holders")
        .select("*")
        .eq("executor_uri", executor_uri)
        .order("changed_at", desc=True)
        .limit(200)
        .execute()
        .data
        or []
    )
    out: list[HolderHistoryItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            HolderHistoryItem(
                executor_uri=_to_text(row.get("executor_uri")).strip(),
                holder_name=_to_text(row.get("holder_name")).strip(),
                holder_id=_to_text(row.get("holder_id")).strip(),
                holder_since=_to_utc(row.get("holder_since")),
                changed_at=_to_utc(row.get("changed_at")),
                reason=_to_text(row.get("reason")).strip(),
            )
        )
    return out


def _make_sig_payload(
    doc_id: str,
    body_hash: str,
    executor_uri: str,
    dto_role: str,
    trip_role: str,
    signed_at: datetime,
) -> str:
    return ":".join(
        [
            _to_text(doc_id).strip(),
            _to_text(body_hash).strip(),
            _to_text(executor_uri).strip(),
            _to_text(dto_role).strip(),
            _to_text(trip_role).strip(),
            signed_at.isoformat(),
        ]
    )


def build_signpeg_signature(
    doc_id: str,
    body_hash: str,
    executor_uri: str,
    dto_role: str,
    trip_role: str,
    signed_at: datetime,
) -> str:
    payload = _make_sig_payload(doc_id, body_hash, executor_uri, dto_role, trip_role, signed_at)
    return f"signpeg:v1:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def verify_signature(
    sig_data: str,
    doc_id: str,
    body_hash: str,
    executor_uri: str,
    dto_role: str,
    trip_role: str,
    signed_at: datetime,
) -> bool:
    expected = build_signpeg_signature(doc_id, body_hash, executor_uri, dto_role, trip_role, signed_at)
    return _to_text(sig_data).strip() == expected


def _next_required_role(signatures: list[SignStatusItem]) -> str:
    signed_roles = {str(item.dto_role).strip().lower() for item in signatures}
    for role in SIGN_FLOW_ROLES:
        if role not in signed_roles:
            return role
    return ""


def _load_signatures(sb: Any, doc_id: str) -> list[SignStatusItem]:
    rows = (
        sb.table("gate_trips")
        .select("*")
        .eq("doc_id", doc_id)
        .order("signed_at", desc=False)
        .limit(300)
        .execute()
        .data
        or []
    )
    out: list[SignStatusItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            SignStatusItem(
                dto_role=_to_text(row.get("dto_role")).strip(),
                trip_role=_to_text(row.get("trip_role")).strip(),
                executor_uri=_to_text(row.get("executor_uri")).strip(),
                executor_name=_to_text(row.get("executor_name")).strip(),
                signed_at=_to_utc(row.get("signed_at")),
                sig_data=_to_text(row.get("sig_data")).strip(),
                trip_uri=_to_text(row.get("trip_uri")).strip(),
                verified=bool(row.get("verified", True)),
            )
        )
    return out


def _upsert_doc_state(
    sb: Any,
    *,
    doc_id: str,
    signatures: list[SignStatusItem],
    next_required: str,
    next_executor: str,
) -> None:
    all_signed = next_required == ""
    lifecycle_stage = "approved" if all_signed else "submitted"
    payload = {
        "doc_id": doc_id,
        "lifecycle_stage": lifecycle_stage,
        "all_signed": bool(all_signed),
        "next_required": next_required,
        "next_executor": next_executor,
        "state_data": {
            "signature_count": len(signatures),
            "roles_signed": [item.dto_role for item in signatures],
        },
        "updated_at": _utc_now().isoformat(),
    }
    sb.table("docpeg_states").upsert(payload, on_conflict="doc_id").execute()


def _insert_trip(
    sb: Any,
    result: SignPegResult,
    *,
    action: str,
    delegation_uri: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    sb.table("gate_trips").insert(
        {
            "trip_uri": result.trip_uri,
            "doc_id": result.doc_id,
            "body_hash": result.body_hash,
            "executor_uri": result.executor_uri,
            "executor_name": result.executor_name,
            "dto_role": result.dto_role,
            "trip_role": result.trip_role,
            "action": action,
            "sig_data": result.sig_data,
            "signed_at": result.signed_at.isoformat(),
            "verified": bool(result.verified),
            "delegation_uri": delegation_uri,
            "metadata": metadata or {},
            "created_at": _utc_now().isoformat(),
        }
    ).execute()


def _insert_railpact(sb: Any, entry: RailPactEntry) -> None:
    sb.table("railpact_settlements").insert(
        {
            "trip_uri": entry.trip_uri,
            "executor_uri": entry.executor_uri,
            "doc_id": entry.doc_id,
            "amount": float(entry.amount),
            "energy_delta": int(entry.energy_delta),
            "settled_at": entry.settled_at.isoformat(),
            "metadata": dict(entry.metadata),
        }
    ).execute()


def _insert_executor_alert(
    sb: Any,
    *,
    executor_id: str,
    executor_uri: str,
    org_uri: str,
    alert_type: str,
    message: str,
    certificate: dict[str, Any] | None = None,
) -> None:
    try:
        sb.table("san_executor_alerts").insert(
            {
                "executor_id": executor_id,
                "executor_uri": executor_uri,
                "org_uri": org_uri,
                "alert_type": alert_type,
                "message": message,
                "certificate": certificate or {},
                "created_at": _utc_now().isoformat(),
            }
        ).execute()
    except Exception:
        # Optional table for warning push; do not break runtime if missing.
        return


def _load_delegation(sb: Any, delegation_uri: str) -> Delegation:
    rows = (
        sb.table("san_delegations")
        .select("*")
        .eq("delegation_uri", delegation_uri)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=403, detail=f"delegation_not_found: {delegation_uri}")
    row = rows[0] if isinstance(rows[0], dict) else {}
    return Delegation(
        delegation_uri=_to_text(row.get("delegation_uri")).strip(),
        from_executor_uri=_to_text(row.get("from_executor_uri")).strip(),
        to_executor_uri=_to_text(row.get("to_executor_uri")).strip(),
        scope=[_to_text(x).strip().lower() for x in _as_list(row.get("scope")) if _to_text(x).strip()],
        valid_from=_to_utc(row.get("valid_from")),
        valid_until=_to_utc(row.get("valid_until")),
        proof_doc=_to_text(row.get("proof_doc")).strip(),
        status=_to_text(row.get("status")).strip() or "active",
        created_at=_to_utc(row.get("created_at")),
    )


def _ensure_certificates_valid(certificates: list[Certificate]) -> None:
    today = _utc_now().date()
    for cert in certificates:
        if cert.status == "revoked":
            raise HTTPException(status_code=422, detail=f"certificate_revoked: {cert.cert_no}")
        if cert.valid_until < today:
            raise HTTPException(status_code=422, detail=f"certificate_expired: {cert.cert_no}")


def _normalize_certificates(certificates: list[Certificate]) -> list[Certificate]:
    out: list[Certificate] = []
    for cert in certificates:
        scan_hash = _to_text(cert.scan_hash).strip()
        if not scan_hash:
            seed = f"{cert.cert_no}:{cert.issued_by}:{cert.valid_until.isoformat()}"
            scan_hash = f"sha256:{_sha256_text(seed)}"
        out.append(cert.model_copy(update={"scan_hash": scan_hash}))
    return out


def _normalize_executor_requires(requires: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in requires:
        uri = _normalize_uri(raw).strip()
        if not uri or uri in seen:
            continue
        seen.add(uri)
        out.append(uri)
    return out


def _normalize_tool_spec(tool_spec: ToolSpec | None) -> ToolSpec | None:
    if tool_spec is None:
        return None
    category = _to_text(tool_spec.tool_category).strip().lower()
    if category == "consumable":
        current = tool_spec.consumable or ConsumableDetail(sku_uri="")
        remaining = float(current.remaining_qty or 0.0)
        if remaining <= 0 and float(current.initial_qty or 0.0) > 0:
            remaining = float(current.initial_qty)
        return tool_spec.model_copy(
            update={
                "tool_category": "consumable",
                "consumable": current.model_copy(update={"remaining_qty": max(remaining, 0.0)}),
                "reusable": None,
                "capability": None,
            }
        )
    if category == "reusable":
        current = tool_spec.reusable or ReusableDetail()
        expected_life = max(int(current.expected_life or 0), 0)
        current_uses = max(int(current.current_uses or 0), 0)
        remaining_uses = int(current.remaining_uses or 0)
        if remaining_uses <= 0 and expected_life > 0:
            remaining_uses = max(expected_life - current_uses, 0)
        maintenance_cycle = max(int(current.maintenance_cycle or 0), 0)
        next_maintenance_at = int(current.next_maintenance_at or 0)
        if next_maintenance_at <= 0 and maintenance_cycle > 0:
            next_maintenance_at = maintenance_cycle
        dep = float(current.depreciation_per_use or 0.0)
        if dep <= 0 and expected_life > 0 and float(current.purchase_price or 0.0) > 0:
            dep = float(current.purchase_price) / float(expected_life)
        return tool_spec.model_copy(
            update={
                "tool_category": "reusable",
                "reusable": current.model_copy(
                    update={
                        "remaining_uses": max(remaining_uses, 0),
                        "next_maintenance_at": max(next_maintenance_at, 0),
                        "depreciation_per_use": dep,
                    }
                ),
                "consumable": None,
                "capability": None,
            }
        )
    current_cap = tool_spec.capability or CapabilityDetail()
    total = max(int(current_cap.quota_total or 0), 0)
    used = max(int(current_cap.quota_used or 0), 0)
    remaining = int(current_cap.quota_remaining or 0)
    if remaining <= 0 and total > 0:
        remaining = max(total - used, 0)
    return tool_spec.model_copy(
        update={
            "tool_category": "capability",
            "capability": current_cap.model_copy(update={"quota_total": total, "quota_used": used, "quota_remaining": max(remaining, 0)}),
            "consumable": None,
            "reusable": None,
        }
    )


def _normalize_org_spec(
    *,
    org_uri: str,
    org_spec: OrgSpec | None,
    business_license_file: str = "",
) -> OrgSpec | None:
    if org_spec is None:
        return None
    uri = _normalize_org_uri(org_uri)
    spec = org_spec
    branch_list = [item.strip() for item in list(spec.branches) if _to_text(item).strip()]
    if not branch_list and int(spec.branch_count or 0) > 0:
        branch_list = [f"{uri}/branch/{idx:03d}" for idx in range(1, int(spec.branch_count) + 1)]
    branch_count = max(int(spec.branch_count or 0), len(branch_list))
    members = _normalize_executor_requires(list(spec.member_executor_uris))
    projects = [_normalize_uri(item) for item in list(spec.project_uris) if _to_text(item).strip()]
    license_hash = _to_text(spec.business_license_scan_hash).strip()
    raw_file = _to_text(business_license_file).strip()
    if not license_hash and raw_file:
        license_hash = f"sha256:{_sha256_text(raw_file)}"
    return spec.model_copy(
        update={
            "branches": branch_list,
            "branch_count": branch_count,
            "member_executor_uris": members,
            "project_uris": projects,
            "business_license_scan_hash": license_hash,
        }
    )


def _ensure_requires_exist(sb: Any, *, requires: list[str]) -> None:
    for uri in requires:
        row = _get_executor_row(sb, uri)
        if not row:
            raise HTTPException(status_code=422, detail=f"required_executor_not_found: {uri}")
        token = _to_text(row.get("executor_type")).strip().lower()
        if token != "tool":
            raise HTTPException(status_code=422, detail=f"required_executor_not_tool: {uri}")


def _executor_registration_proof(executor_payload: dict[str, Any]) -> str:
    return _proof_id("PROOF-EXEC", executor_payload)


def _new_executor_id() -> str:
    return f"EXEC-{uuid4().hex[:8].upper()}"


def _build_executor_uri(
    *,
    org_uri: str,
    name: str,
    executor_type: str = "human",
    machine_code: str = "",
    tool_code: str = "",
    ai_version: str = "",
) -> str:
    base = _normalize_org_uri(org_uri)
    kind = _to_text(executor_type).strip().lower() or "human"
    if kind == "org":
        if base:
            return base
        token = _slug_name(name)
        return f"v://cn.{token}"
    if not base:
        raise HTTPException(status_code=422, detail="org_uri_required")
    if kind == "machine":
        token = _slug_name(machine_code or name)
    elif kind == "tool":
        token = _slug_name(tool_code or name)
    elif kind == "ai":
        seed = _to_text(name).strip()
        if _to_text(ai_version).strip():
            seed = f"{seed}-{_to_text(ai_version).strip()}"
        token = _slug_name(seed)
    else:
        token = _slug_name(name)
    return f"{base}/executor/{token}"


def _executor_display_status(executor: Executor) -> str:
    status = str(executor.status or "").strip().lower()
    if status in {"active", "available"}:
        return "available"
    if status == "busy":
        return "busy"
    if status == "in_use":
        return "in_use"
    if status == "maintenance":
        return "maintenance"
    if status == "depleted":
        return "depleted"
    if status == "retired":
        return "retired"
    if status == "offline":
        return "offline"
    if status == "suspended":
        return "suspended"
    return status or "available"


def register_executor(sb: Any, body: ExecutorRegisterRequest) -> Executor:
    if not body.executor_uri:
        raise HTTPException(status_code=422, detail="executor_uri_required")
    normalized_certificates = _normalize_certificates(body.certificates)
    _ensure_certificates_valid(normalized_certificates)
    requires = _normalize_executor_requires(body.requires)
    if _to_text(body.executor_type).strip().lower() != "org":
        _ensure_requires_exist(sb, requires=requires)
    normalized_tool_spec = _normalize_tool_spec(body.tool_spec)
    normalized_uri = _normalize_uri(body.executor_uri).strip()
    org_uri = _normalize_org_uri(body.org_uri)
    if _to_text(body.executor_type).strip().lower() == "org" and not org_uri:
        org_uri = _normalize_org_uri(normalized_uri)
    normalized_org_spec = _normalize_org_spec(
        org_uri=org_uri or normalized_uri,
        org_spec=body.org_spec,
        business_license_file=body.business_license_file,
    )
    normalized_business_license_file = _to_text(body.business_license_file).strip()
    if _to_text(body.executor_type).strip().lower() == "tool" and normalized_tool_spec is None:
        raise HTTPException(status_code=422, detail="tool_spec_required_for_tool_executor")
    if _to_text(body.executor_type).strip().lower() == "org" and normalized_org_spec is None:
        raise HTTPException(status_code=422, detail="org_spec_required_for_org_executor")
    executor_id = _to_text(body.executor_id).strip() or _new_executor_id()
    registration_payload = {
        "executor_id": executor_id,
        "executor_uri": normalized_uri,
        "name": body.name,
        "executor_type": body.executor_type,
        "org_uri": org_uri,
        "capacity": body.capacity.model_dump(mode="json"),
        "energy": body.energy.model_dump(mode="json"),
        "certificates": [item.model_dump(mode="json") for item in normalized_certificates],
        "skills": [item.model_dump(mode="json") for item in body.skills],
        "requires": requires,
        "tool_spec": normalized_tool_spec.model_dump(mode="json") if normalized_tool_spec else None,
        "org_spec": normalized_org_spec.model_dump(mode="json") if normalized_org_spec else None,
        "business_license_file": normalized_business_license_file,
    }
    registration_proof = _to_text(body.registration_proof).strip() or _executor_registration_proof(registration_payload)
    executor = Executor(
        executor_id=executor_id,
        executor_uri=normalized_uri,
        executor_type=body.executor_type,
        name=body.name,
        org_uri=org_uri,
        capacity=body.capacity,
        certificates=normalized_certificates,
        energy=body.energy,
        skills=body.skills,
        requires=requires,
        used_by=_normalize_executor_requires(body.used_by),
        tool_spec=normalized_tool_spec,
        org_spec=normalized_org_spec,
        business_license_file=normalized_business_license_file,
        status=_executor_status_default(body.status),
        registration_proof=registration_proof,
        proof_history=list(body.proof_history) + [registration_proof],
        registered_at=body.registered_at,
        last_active=body.last_active,
        trip_count=0,
        proof_count=0,
        holder_name=body.holder_name,
        holder_id=body.holder_id,
        holder_since=body.holder_since,
    )
    _upsert_executor(sb, executor)
    _insert_holder_history(
        sb,
        executor_uri=executor.executor_uri,
        holder_name=executor.holder_name,
        holder_id=executor.holder_id,
        holder_since=executor.holder_since,
        reason="register",
    )
    for req_uri in requires:
        try:
            dep = _get_executor(sb, req_uri)
        except HTTPException:
            continue
        if normalized_uri in dep.used_by:
            continue
        dep_updated = dep.model_copy(update={"used_by": list(dep.used_by) + [normalized_uri], "last_active": _utc_now()})
        _upsert_executor(sb, dep_updated)
    return executor


def register_executorpeg(sb: Any, body: ExecutorCreateRequest) -> Executor:
    holder_name = _to_text(body.holder_name).strip() or _to_text(body.name).strip()
    holder_id = _to_text(body.holder_id).strip() or _slug_name(holder_name)
    kind = _to_text(body.executor_type).strip().lower()
    derived_org_uri = _normalize_org_uri(body.org_uri)
    if kind == "org":
        derived_org_uri = _build_executor_uri(
            org_uri=body.org_uri,
            name=body.name,
            executor_type="org",
        )
    request = ExecutorRegisterRequest(
        executor_id=_new_executor_id(),
        executor_uri=_build_executor_uri(
            org_uri=derived_org_uri if kind == "org" else body.org_uri,
            name=body.name,
            executor_type=body.executor_type,
            machine_code=body.machine_code,
            tool_code=body.tool_code,
            ai_version=body.ai_version,
        ),
        executor_type=body.executor_type,
        name=body.name,
        org_uri=derived_org_uri if kind == "org" else body.org_uri,
        capacity=body.capacity,
        certificates=body.certificates,
        energy=body.energy,
        skills=body.skills,
        requires=body.requires,
        tool_spec=body.tool_spec,
        org_spec=body.org_spec,
        business_license_file=body.business_license_file,
        status=body.status,
        holder_name=holder_name,
        holder_id=holder_id,
    )
    return register_executor(sb=sb, body=request)


def update_executor_holder(sb: Any, executor_uri: str, body: HolderChangeRequest) -> Executor:
    executor = _get_executor(sb, _normalize_uri(executor_uri))
    _insert_holder_history(
        sb,
        executor_uri=executor.executor_uri,
        holder_name=executor.holder_name,
        holder_id=executor.holder_id,
        holder_since=executor.holder_since,
        reason=body.reason or "holder_change",
    )
    updated = executor.model_copy(
        update={
            "holder_name": body.holder_name,
            "holder_id": body.holder_id,
            "holder_since": body.holder_since,
        }
    )
    _upsert_executor(sb, updated)
    return updated


def get_executor_record(sb: Any, executor_uri: str) -> ExecutorRecord:
    executor = _get_executor(sb, _normalize_uri(executor_uri))
    history = _list_holder_history(sb, executor.executor_uri)
    return ExecutorRecord(executor=executor, holder_history=history)


def get_executor_record_by_id(sb: Any, executor_id: str) -> ExecutorRecord:
    row = _get_executor_row_by_id(sb, executor_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"executor_not_found: {executor_id}")
    executor = _executor_from_row(row)
    history = _list_holder_history(sb, executor.executor_uri)
    return ExecutorRecord(executor=executor, holder_history=history)


def get_executor_status(sb: Any, executor_id: str) -> ExecutorStatusResponse:
    record = get_executor_record_by_id(sb, executor_id)
    executor = record.executor
    remaining_life = None
    remaining_qty = None
    quota_remaining = None
    if executor.tool_spec and executor.executor_type == "tool":
        if executor.tool_spec.reusable:
            remaining_life = int(executor.tool_spec.reusable.remaining_uses)
        if executor.tool_spec.consumable:
            remaining_qty = float(executor.tool_spec.consumable.remaining_qty)
        if executor.tool_spec.capability:
            quota_remaining = int(executor.tool_spec.capability.quota_remaining)
    return ExecutorStatusResponse(
        executor_id=executor.executor_id,
        executor_uri=executor.executor_uri,
        status=_executor_display_status(executor),
        capacity=executor.capacity,
        certificates_valid=executor.cert_valid(),
        expiring_soon=executor.expiring_certificates(within_days=30),
        remaining_life=remaining_life,
        remaining_qty=remaining_qty,
        quota_remaining=quota_remaining,
    )


def list_executors(sb: Any, *, org_uri: str = "") -> ExecutorListResponse:
    rows = _list_executor_rows(sb)
    token = _normalize_uri(org_uri).strip().rstrip("/")
    items: list[ExecutorListItem] = []
    for row in rows:
        executor = _executor_from_row(row)
        if token and _normalize_uri(executor.org_uri).strip().rstrip("/") != token:
            continue
        items.append(
            ExecutorListItem(
                executor_id=executor.executor_id,
                executor_uri=executor.executor_uri,
                org_uri=executor.org_uri,
                name=executor.name,
                executor_type=executor.executor_type,
                status=_executor_display_status(executor),
                capacity=executor.capacity,
                certificates=executor.certificates,
                certificates_valid=executor.cert_valid(),
            )
        )
    items.sort(key=lambda item: (item.status != "available", item.name))
    return ExecutorListResponse(items=items)


def search_executors(sb: Any, query: ExecutorSearchRequest) -> ExecutorListResponse:
    token_skill = _to_text(query.skill_uri).strip().lower()
    token_org = _normalize_uri(query.org_uri).strip().rstrip("/")
    token_type = _to_text(query.type).strip().lower()
    out: list[ExecutorListItem] = []
    for item in list_executors(sb).items:
        if token_org and _normalize_uri(item.org_uri).strip().rstrip("/") != token_org:
            continue
        if token_type and _to_text(item.executor_type).strip().lower() != token_type:
            continue
        record = get_executor_record_by_id(sb, item.executor_id)
        executor = record.executor
        if token_skill and not any(token_skill in _to_text(skill.skill_uri).strip().lower() for skill in executor.skills):
            continue
        if bool(query.available):
            if not executor.status_available():
                continue
            if executor.capacity.current_load >= executor.capacity.max_concurrent:
                continue
        out.append(item)
    return ExecutorListResponse(items=out)


def _get_org_executor(sb: Any, org_uri: str) -> Executor:
    normalized = _normalize_org_uri(org_uri)
    org = _get_executor(sb, normalized)
    if org.executor_type != "org":
        raise HTTPException(status_code=422, detail=f"org_executor_required: {normalized}")
    return org


def get_org_members(sb: Any, *, org_uri: str) -> dict[str, Any]:
    org = _get_org_executor(sb, org_uri)
    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _list_executor_rows(sb):
        executor = _executor_from_row(row)
        if executor.executor_uri == org.executor_uri:
            continue
        if _normalize_org_uri(executor.org_uri) != _normalize_org_uri(org.executor_uri):
            continue
        seen.add(executor.executor_uri)
        members.append(
            {
                "executor_id": executor.executor_id,
                "executor_uri": executor.executor_uri,
                "name": executor.name,
                "executor_type": executor.executor_type,
                "status": executor.status,
            }
        )
    if org.org_spec:
        for uri in org.org_spec.member_executor_uris:
            if uri in seen:
                continue
            row = _get_executor_row(sb, uri)
            if not row:
                continue
            executor = _executor_from_row(row)
            members.append(
                {
                    "executor_id": executor.executor_id,
                    "executor_uri": executor.executor_uri,
                    "name": executor.name,
                    "executor_type": executor.executor_type,
                    "status": executor.status,
                }
            )
    members.sort(key=lambda item: (item.get("executor_type") == "org", _to_text(item.get("name")).strip()))
    return {"org_uri": org.executor_uri, "org_name": org.name, "members": members}


def get_org_branches(sb: Any, *, org_uri: str) -> dict[str, Any]:
    org = _get_org_executor(sb, org_uri)
    spec = org.org_spec or OrgSpec()
    branches = [item for item in spec.branches if _to_text(item).strip()]
    return {
        "org_uri": org.executor_uri,
        "org_name": org.name,
        "branch_count": max(int(spec.branch_count or 0), len(branches)),
        "branches": branches,
    }


def add_org_member(sb: Any, *, org_uri: str, body: OrgMemberAddRequest) -> dict[str, Any]:
    org = _get_org_executor(sb, org_uri)
    member = _get_executor(sb, _normalize_uri(body.member_executor_uri))
    if member.executor_type == "org":
        raise HTTPException(status_code=422, detail="org_member_must_not_be_org")
    spec = org.org_spec or OrgSpec()
    members = _normalize_executor_requires(list(spec.member_executor_uris) + [member.executor_uri])
    updated_spec = spec.model_copy(update={"member_executor_uris": members})
    updated_org = org.model_copy(update={"org_spec": updated_spec, "last_active": _utc_now()})
    _upsert_executor(sb, updated_org)
    updated_member = member.model_copy(update={"org_uri": org.executor_uri, "last_active": _utc_now()})
    _upsert_executor(sb, updated_member)
    return {"ok": True, "org_uri": org.executor_uri, "member_executor_uri": member.executor_uri}


def add_org_project(sb: Any, *, org_uri: str, body: OrgProjectAddRequest) -> dict[str, Any]:
    org = _get_org_executor(sb, org_uri)
    spec = org.org_spec or OrgSpec()
    project_uri = _normalize_uri(body.project_uri).strip()
    if not project_uri:
        raise HTTPException(status_code=422, detail="project_uri_required")
    projects = [_normalize_uri(item) for item in list(spec.project_uris)]
    if project_uri not in projects:
        projects.append(project_uri)
    updated_spec = spec.model_copy(update={"project_uris": projects})
    updated_org = org.model_copy(update={"org_spec": updated_spec, "last_active": _utc_now()})
    _upsert_executor(sb, updated_org)
    return {"ok": True, "org_uri": org.executor_uri, "project_uris": projects}


def add_executor_certificate(sb: Any, executor_id: str, body: CertificateAddRequest) -> Executor:
    record = get_executor_record_by_id(sb, executor_id)
    executor = record.executor
    normalized = _normalize_certificates([body.certificate])[0]
    certificates = [item for item in executor.certificates if item.cert_id != normalized.cert_id]
    certificates.append(normalized)
    _ensure_certificates_valid([normalized])
    status = executor.status
    if _executor_status_default(status) == "suspended" and all(item.is_valid_on(_utc_now().date()) for item in certificates):
        status = "available"
    updated = executor.model_copy(update={"certificates": certificates, "status": status, "last_active": _utc_now()})
    _upsert_executor(sb, updated)
    return updated


def add_executor_skill(sb: Any, executor_id: str, body: SkillAddRequest) -> Executor:
    record = get_executor_record_by_id(sb, executor_id)
    executor = record.executor
    skills = [item for item in executor.skills if item.skill_uri != body.skill.skill_uri]
    skills.append(body.skill)
    updated = executor.model_copy(update={"skills": skills, "last_active": _utc_now()})
    _upsert_executor(sb, updated)
    return updated


def add_executor_requires(sb: Any, executor_id: str, body: RequiresAddRequest) -> Executor:
    record = get_executor_record_by_id(sb, executor_id)
    executor = record.executor
    requires = _normalize_executor_requires(list(executor.requires) + list(body.tool_executor_uris))
    _ensure_requires_exist(sb, requires=requires)
    updated = executor.model_copy(update={"requires": requires, "last_active": _utc_now()})
    _upsert_executor(sb, updated)
    for req_uri in requires:
        dep = _get_executor(sb, req_uri)
        if updated.executor_uri in dep.used_by:
            continue
        dep_updated = dep.model_copy(update={"used_by": list(dep.used_by) + [updated.executor_uri], "last_active": _utc_now()})
        _upsert_executor(sb, dep_updated)
    return updated


def _insert_sku_ledger(
    sb: Any,
    *,
    sku_uri: str,
    quantity: float,
    trip_id: str,
    executor_uri: str,
    note: str,
) -> None:
    if not sku_uri or float(quantity) <= 0:
        return
    payload = {
        "sku_uri": sku_uri,
        "direction": "OUT",
        "quantity": float(quantity),
        "trip_id": trip_id,
        "executor_uri": executor_uri,
        "note": note,
        "created_at": _utc_now().isoformat(),
    }
    try:
        sb.table("sku_ledger").insert(payload).execute()
    except Exception:
        try:
            sb.table("proof_utxo").insert({"proof_id": _proof_id("SKU-LEDGER", payload), "state_data": payload, "created_at": _utc_now().isoformat()}).execute()
        except Exception:
            return


def use_executor(sb: Any, executor_id: str, body: ExecutorUseRequest) -> dict[str, Any]:
    record = get_executor_record_by_id(sb, executor_id)
    executor = record.executor
    now = _utc_now()
    capacity = executor.capacity.model_copy(update={"current": min(int(executor.capacity.current_load) + 1, int(executor.capacity.max_concurrent))})
    energy = executor.energy.model_copy(
        update={
            "consumed": int(executor.energy.consumed)
            + int(
                executor.energy.consume_delta(
                    duration_hours=float(body.duration_hours or 0.0),
                    shifts=float(body.shifts or 0.0),
                    tokens_used=int(body.tokens_used or 0),
                )
            )
        }
    )
    status = executor.status
    tool_spec = executor.tool_spec
    extra_entries: list[RailPactEntry] = []
    if executor.executor_type == "tool" and tool_spec:
        if tool_spec.consumable:
            consumed_qty = max(float(body.consumed_qty or 0.0), 0.0)
            remaining = max(float(tool_spec.consumable.remaining_qty) - consumed_qty, 0.0)
            tool_spec = tool_spec.model_copy(update={"consumable": tool_spec.consumable.model_copy(update={"remaining_qty": remaining})})
            if remaining <= 0:
                status = "depleted"
            _insert_sku_ledger(
                sb,
                sku_uri=_to_text(tool_spec.consumable.sku_uri).strip(),
                quantity=consumed_qty,
                trip_id=_to_text(body.trip_id).strip() or executor.executor_id,
                executor_uri=executor.executor_uri,
                note="executor_tool_consumption",
            )
        if tool_spec.reusable:
            uses_delta = max(int(body.shifts or 0), 1)
            current_uses = max(int(tool_spec.reusable.current_uses) + uses_delta, 0)
            remaining_uses = max(int(tool_spec.reusable.expected_life) - current_uses, 0)
            tool_spec = tool_spec.model_copy(
                update={
                    "reusable": tool_spec.reusable.model_copy(
                        update={
                            "current_uses": current_uses,
                            "remaining_uses": remaining_uses,
                        }
                    )
                }
            )
            if remaining_uses <= 0:
                status = "retired"
            elif int(tool_spec.reusable.maintenance_cycle or 0) > 0 and current_uses >= int(tool_spec.reusable.next_maintenance_at or 0):
                status = "maintenance"
            else:
                status = "in_use"
            dep = float(tool_spec.reusable.depreciation_per_use or 0.0)
            if dep > 0:
                extra_entries.append(
                    RailPactEntry(
                        trip_uri=_to_text(body.trip_uri).strip() or f"v://executor/{executor.executor_id}/use/{uuid4().hex[:8]}",
                        executor_uri=executor.executor_uri,
                        doc_id=_to_text(body.trip_id).strip() or executor.executor_id,
                        amount=float(dep),
                        energy_delta=0,
                        metadata={"smu_type": "depreciation", "kind": "executor_tool_depreciation"},
                    )
                )
        if tool_spec.capability:
            used = max(int(tool_spec.capability.quota_used) + max(int(body.tokens_used or 0), 0), 0)
            remaining = max(int(tool_spec.capability.quota_total) - used, 0)
            tool_spec = tool_spec.model_copy(
                update={"capability": tool_spec.capability.model_copy(update={"quota_used": used, "quota_remaining": remaining})}
            )
            status = "depleted" if remaining <= 0 else "in_use"

    updated = executor.model_copy(
        update={
            "capacity": capacity,
            "energy": energy,
            "tool_spec": _normalize_tool_spec(tool_spec),
            "status": _executor_status_default(status),
            "last_active": now,
            "proof_history": list(executor.proof_history) + ([_to_text(body.trip_uri).strip()] if _to_text(body.trip_uri).strip() else []),
        }
    )
    _upsert_executor(sb, updated)

    amount = updated.energy.bill_amount(
        duration_hours=float(body.duration_hours or 0.0),
        shifts=float(body.shifts or 0.0),
        tokens_used=int(body.tokens_used or 0),
    )
    base_entry = RailPactEntry(
        trip_uri=_to_text(body.trip_uri).strip() or f"v://executor/{updated.executor_id}/use/{uuid4().hex[:8]}",
        executor_uri=updated.executor_uri,
        doc_id=_to_text(body.trip_id).strip() or updated.executor_id,
        amount=float(amount),
        energy_delta=1,
        metadata={
            "smu_type": _to_text(updated.energy.smu_type).strip() or ("tool" if updated.executor_type == "tool" else "labor"),
            "kind": "executor_use",
            "trip_role": _to_text(body.trip_role).strip(),
        },
    )
    _insert_railpact(sb, base_entry)
    for item in extra_entries:
        _insert_railpact(sb, item)
    return {"ok": True, "executor": updated.model_dump(mode="json")}


def maintain_executor(sb: Any, executor_id: str, body: ExecutorMaintainRequest) -> dict[str, Any]:
    record = get_executor_record_by_id(sb, executor_id)
    executor = record.executor
    tool_spec = executor.tool_spec
    if executor.executor_type != "tool" or not tool_spec or not tool_spec.reusable:
        raise HTTPException(status_code=422, detail="executor_not_reusable_tool")
    reusable = tool_spec.reusable
    next_maintenance_at = (
        int(reusable.current_uses) + int(reusable.maintenance_cycle)
        if int(reusable.maintenance_cycle or 0) > 0
        else int(reusable.next_maintenance_at)
    )
    updated_spec = tool_spec.model_copy(
        update={
            "reusable": reusable.model_copy(
                update={
                    "purchase_date": reusable.purchase_date,
                    "next_maintenance_at": next_maintenance_at,
                }
            )
        }
    )
    updated = executor.model_copy(update={"tool_spec": updated_spec, "status": "available", "last_active": _utc_now()})
    _upsert_executor(sb, updated)
    proof = _proof_id(
        "PROOF-EXEC-MAINT",
        {
            "executor_uri": updated.executor_uri,
            "performed_at": body.performed_at.isoformat(),
            "note": body.note,
        },
    )
    return {"ok": True, "executor": updated.model_dump(mode="json"), "maintenance_proof": proof}


def check_executor_certificate_expiry(sb: Any) -> dict[str, Any]:
    today = _utc_now().date()
    suspended: list[str] = []
    warnings: list[dict[str, Any]] = []
    rows = _list_executor_rows(sb)
    for row in rows:
        executor = _executor_from_row(row)
        changed = False
        for cert in executor.certificates:
            days_left = (cert.valid_until - today).days
            if days_left <= 0:
                cert.status = "expired"
                changed = True
                if _executor_status_default(executor.status) != "suspended":
                    executor.status = "suspended"
                    changed = True
                suspended.append(executor.executor_uri)
                _insert_executor_alert(
                    sb,
                    executor_id=executor.executor_id,
                    executor_uri=executor.executor_uri,
                    org_uri=executor.org_uri,
                    alert_type="certificate_expired",
                    message=f"{executor.name} 证书已过期: {cert.cert_type}",
                    certificate=cert.model_dump(mode="json"),
                )
            elif 0 < days_left <= 30 and cert.status == "active":
                item = {
                    "executor_uri": executor.executor_uri,
                    "org_uri": executor.org_uri,
                    "name": executor.name,
                    "cert_type": cert.cert_type,
                    "cert_no": cert.cert_no,
                    "days_left": days_left,
                }
                warnings.append(
                    item
                )
                _insert_executor_alert(
                    sb,
                    executor_id=executor.executor_id,
                    executor_uri=executor.executor_uri,
                    org_uri=executor.org_uri,
                    alert_type="certificate_expiring",
                    message=f"{executor.name} 证书将在{days_left}天后到期: {cert.cert_type}",
                    certificate=cert.model_dump(mode="json"),
                )
        if executor.executor_type == "tool" and executor.tool_spec:
            if executor.tool_spec.consumable:
                c = executor.tool_spec.consumable
                if float(c.remaining_qty) <= float(c.replenish_threshold):
                    warnings.append(
                        {
                            "executor_uri": executor.executor_uri,
                            "org_uri": executor.org_uri,
                            "name": executor.name,
                            "alert_type": "tool_inventory_low",
                            "remaining_qty": c.remaining_qty,
                            "unit": c.unit,
                        }
                    )
                    _insert_executor_alert(
                        sb,
                        executor_id=executor.executor_id,
                        executor_uri=executor.executor_uri,
                        org_uri=executor.org_uri,
                        alert_type="tool_inventory_low",
                        message=f"{executor.name}库存不足：剩余{c.remaining_qty}{c.unit}",
                        certificate={"tool_spec": executor.tool_spec.model_dump(mode="json")},
                    )
            if executor.tool_spec.reusable:
                r = executor.tool_spec.reusable
                remaining_to_maintenance = int(r.next_maintenance_at) - int(r.current_uses)
                if remaining_to_maintenance <= 0:
                    if _executor_status_default(executor.status) not in {"retired", "suspended"}:
                        executor.status = "maintenance"
                        changed = True
                elif remaining_to_maintenance <= 5:
                    warnings.append(
                        {
                            "executor_uri": executor.executor_uri,
                            "org_uri": executor.org_uri,
                            "name": executor.name,
                            "alert_type": "tool_maintenance_due",
                            "remaining_uses": remaining_to_maintenance,
                        }
                    )
                    _insert_executor_alert(
                        sb,
                        executor_id=executor.executor_id,
                        executor_uri=executor.executor_uri,
                        org_uri=executor.org_uri,
                        alert_type="tool_maintenance_due",
                        message=f"{executor.name}即将到维保：还剩{remaining_to_maintenance}次",
                        certificate={"tool_spec": executor.tool_spec.model_dump(mode="json")},
                    )
            if executor.tool_spec.capability:
                cap = executor.tool_spec.capability
                if int(cap.quota_total or 0) > 0:
                    pct = float(cap.quota_remaining) / float(cap.quota_total)
                    if pct <= 0:
                        if _executor_status_default(executor.status) not in {"retired", "suspended"}:
                            executor.status = "depleted"
                            changed = True
                    elif pct <= 0.1:
                        warnings.append(
                            {
                                "executor_uri": executor.executor_uri,
                                "org_uri": executor.org_uri,
                                "name": executor.name,
                                "alert_type": "tool_quota_low",
                                "quota_remaining": cap.quota_remaining,
                            }
                        )
                        _insert_executor_alert(
                            sb,
                            executor_id=executor.executor_id,
                            executor_uri=executor.executor_uri,
                            org_uri=executor.org_uri,
                            alert_type="tool_quota_low",
                            message=f"{executor.name}配额不足10%：剩余{cap.quota_remaining}",
                            certificate={"tool_spec": executor.tool_spec.model_dump(mode="json")},
                        )
        if changed:
            _upsert_executor(sb, executor)
    return {"ok": True, "suspended": suspended, "warnings": warnings}


def validate_executor(
    sb: Any,
    *,
    executor_uri: str,
    required_skill: str = "",
    trip_role: str,
    _visited: set[str] | None = None,
) -> dict[str, Any]:
    executor = _get_executor(sb, executor_uri)
    today = _utc_now().date()
    visited = _visited or set()
    if executor.executor_uri in visited:
        return {"passed": True, "checks": [], "executor": executor}
    visited.add(executor.executor_uri)
    status_ok = executor.status_available()
    capacity_ok = executor.capacity.current_load < executor.capacity.max_concurrent
    cert_ok = executor.cert_valid(today)
    need_skill = _to_text(required_skill).strip().lower()
    if need_skill:
        skill_ok = executor.has_skill_for(need_skill or trip_role, when=today) or any(
            need_skill in _to_text(skill.skill_uri).strip().lower()
            for skill in executor.skills
            if skill.is_valid_on(today)
        )
    else:
        skill_ok = True
    checks = [
        {
            "item": "容器能力",
            "check": capacity_ok,
            "message": f"执行体当前承载已满 {executor.capacity.current_load}/{executor.capacity.max_concurrent}",
        },
        {
            "item": "证书有效",
            "check": cert_ok,
            "message": "执行体证书已过期或被吊销",
        },
        {
            "item": "技能匹配",
            "check": skill_ok,
            "message": f"执行体不具备{required_skill}技能",
        },
        {
            "item": "执行体状态",
            "check": status_ok,
            "message": f"执行体当前状态:{executor.status}",
        },
    ]

    if executor.executor_type != "org":
        org_uri = _normalize_org_uri(executor.org_uri)
        if not org_uri:
            checks.append(
                {
                    "item": "组织资质",
                    "check": False,
                    "message": "执行体未绑定组织执行体",
                }
            )
        else:
            org_row = _get_executor_row(sb, org_uri)
            if not org_row:
                checks.append(
                    {
                        "item": "组织资质",
                        "check": False,
                        "message": f"组织执行体未注册: {org_uri}",
                    }
                )
            else:
                org_executor = _executor_from_row(org_row)
                checks.append(
                    {
                        "item": "组织证书有效",
                        "check": org_executor.cert_valid(today),
                        "message": f"组织资质证书无效: {org_executor.name}",
                    }
                )
                checks.append(
                    {
                        "item": "组织状态",
                        "check": org_executor.status_available(),
                        "message": f"组织执行体状态不可用: {org_executor.status}",
                    }
                )

    if executor.executor_type == "tool" and executor.tool_spec:
        if executor.tool_spec.consumable:
            checks.append(
                {
                    "item": "消耗品余量",
                    "check": float(executor.tool_spec.consumable.remaining_qty) > 0,
                    "message": "消耗品已耗尽，请补充",
                }
            )
        if executor.tool_spec.reusable:
            checks.append(
                {
                    "item": "工具寿命",
                    "check": int(executor.tool_spec.reusable.remaining_uses) > 0,
                    "message": "已达使用寿命，需要更换",
                }
            )
            cycle = int(executor.tool_spec.reusable.maintenance_cycle or 0)
            checks.append(
                {
                    "item": "维保状态",
                    "check": int(executor.tool_spec.reusable.current_uses) < int(executor.tool_spec.reusable.next_maintenance_at or 0)
                    if cycle > 0
                    else True,
                    "message": "需要先完成维保",
                }
            )
        if executor.tool_spec.capability:
            checks.append(
                {
                    "item": "配额余量",
                    "check": int(executor.tool_spec.capability.quota_remaining) > 0,
                    "message": "API配额已耗尽",
                }
            )

    for tool_uri in executor.requires:
        try:
            tool_result = validate_executor(
                sb,
                executor_uri=tool_uri,
                required_skill="",
                trip_role=trip_role,
                _visited=visited,
            )
        except HTTPException as exc:
            checks.append(
                {
                    "item": f"依赖工具：{tool_uri}",
                    "check": False,
                    "message": _to_text(exc.detail).strip() or "依赖工具不可用",
                }
            )
            continue
        if not tool_result.get("passed"):
            first = next((item for item in tool_result.get("checks") or [] if not bool(item.get("check"))), None)
            reason = _to_text((first or {}).get("message")).strip() or "依赖工具不可用"
            dep_name = _to_text((tool_result.get("executor") or {}).name if tool_result.get("executor") else tool_uri).strip()
            checks.append(
                {
                    "item": f"依赖工具：{dep_name}",
                    "check": False,
                    "message": f"{dep_name}不可用：{reason}",
                }
            )

    passed = all(bool(item.get("check")) for item in checks)
    first_failure = next((item for item in checks if not bool(item.get("check"))), None)
    return {"passed": passed, "checks": checks, "executor": executor, "first_failure": _to_text((first_failure or {}).get("message")).strip()}


def _calculate_executor_cost(executor: Executor, req: SignPegRequest) -> tuple[float, int]:
    units = executor.energy.bill_units(
        duration_hours=float(req.duration_hours or 0.0),
        shifts=float(req.shifts or 0.0),
        tokens_used=int(req.tokens_used or 0),
    )
    amount = executor.energy.bill_amount(
        duration_hours=float(req.duration_hours or 0.0),
        shifts=float(req.shifts or 0.0),
        tokens_used=int(req.tokens_used or 0),
    )
    delta = executor.energy.consume_delta(
        duration_hours=float(req.duration_hours or 0.0),
        shifts=float(req.shifts or 0.0),
        tokens_used=int(req.tokens_used or 0),
    )
    if units <= 0:
        return 0.0, max(int(delta), 1)
    return float(amount), max(int(delta), 1)


def sign(sb: Any, req: SignPegRequest, executor: Executor) -> SignPegResult:
    executor_uri = _normalize_uri(req.executor_uri)
    actor_uri = _normalize_uri(req.actor_executor_uri)
    delegation_uri = _normalize_uri(req.delegation_uri)

    if executor.executor_uri != executor_uri:
        raise HTTPException(status_code=400, detail="executor_uri_mismatch")

    validation = validate_executor(
        sb,
        executor_uri=executor_uri,
        required_skill=ROLE_TO_REQUIRED_SKILL.get(_to_text(req.dto_role).strip().lower(), _to_text(req.dto_role).strip().lower()),
        trip_role=req.trip_role,
    )
    if not validation["passed"]:
        first = next((item for item in validation["checks"] if not bool(item.get("check"))), None)
        reason = _to_text((first or {}).get("message")).strip() or "executor_gate_rejected"
        raise HTTPException(status_code=409, detail=reason)
    if executor.energy.consumed >= executor.energy.credit_limit:
        raise HTTPException(status_code=409, detail="energy_credit_exhausted")

    tool_usages = [item for item in list(req.tool_usages or []) if _to_text(getattr(item, "tool_uri", "")).strip()]
    for usage in tool_usages:
        usage_uri = _normalize_uri(usage.tool_uri)
        dep_row = _get_executor_row(sb, usage_uri)
        if dep_row:
            dep_gate = validate_executor(
                sb,
                executor_uri=usage_uri,
                required_skill="",
                trip_role=_to_text(usage.trip_role).strip() or _to_text(req.trip_role).strip(),
            )
            if not bool(dep_gate.get("passed")):
                first = next((item for item in dep_gate.get("checks") or [] if not bool(item.get("check"))), None)
                reason = _to_text((first or {}).get("message")).strip() or "tool_executor_gate_rejected"
                raise HTTPException(status_code=409, detail=reason)
        else:
            gate = validate_tool_gate(
                sb,
                tool_uri=usage_uri,
                trip_role=_to_text(usage.trip_role).strip() or _to_text(req.trip_role).strip(),
                consumed_qty=float(usage.consumed_qty or 0.0),
                tokens_used=int(usage.tokens_used or 0),
            )
            if not bool(gate.get("passed")):
                first = next((item for item in gate.get("checks") or [] if not bool(item.get("check"))), None)
                reason = _to_text((first or {}).get("message")).strip() or "tool_gate_rejected"
                raise HTTPException(status_code=409, detail=reason)

    _validate_ca_requirement(
        signature_mode=req.signature_mode,
        ca_provider=req.ca_provider,
        ca_signature_id=req.ca_signature_id,
    )
    if actor_uri and actor_uri != executor_uri:
        if not delegation_uri:
            raise HTTPException(status_code=403, detail="delegation_required")
        delegation = _load_delegation(sb, delegation_uri)
        if delegation.from_executor_uri != executor_uri or delegation.to_executor_uri != actor_uri:
            raise HTTPException(status_code=403, detail="delegation_mismatch")
        if not delegation.allows(req.action, _utc_now()):
            raise HTTPException(status_code=403, detail="delegation_invalid_or_expired")

    signed_at = _utc_now()
    sig_data = build_signpeg_signature(
        req.doc_id,
        req.body_hash,
        executor_uri,
        req.dto_role,
        req.trip_role,
        signed_at,
    )
    date_str = signed_at.strftime("%Y/%m%d")
    trip_id = f"TRIP-{uuid4().hex[:8].upper()}"
    trip_root = _to_text(req.project_trip_root).strip().rstrip("/") or "v://cn.大锦/DJGS"
    trip_uri = f"{trip_root}/trip/{date_str}/{trip_id}"

    result = SignPegResult(
        sig_data=sig_data,
        signed_at=signed_at,
        executor_uri=executor_uri,
        executor_name=executor.holder_name,
        dto_role=req.dto_role,
        trip_role=req.trip_role,
        doc_id=req.doc_id,
        body_hash=req.body_hash,
        trip_uri=trip_uri,
        verified=True,
        delegation_uri=delegation_uri,
        signature_mode=_to_text(req.signature_mode).strip().lower() or "process",
        ca_provider=_to_text(req.ca_provider).strip(),
        ca_signature_id=_to_text(req.ca_signature_id).strip(),
    )

    _insert_trip(
        sb,
        result,
        action=req.action,
        delegation_uri=delegation_uri,
        metadata={
            "signature_mode": result.signature_mode,
            "ca_provider": result.ca_provider,
            "ca_signature_id": result.ca_signature_id,
            "ca_signed_payload_hash": _to_text(req.ca_signed_payload_hash).strip(),
            "tool_usages": [
                {
                    "tool_uri": _normalize_uri(item.tool_uri),
                    "trip_role": _to_text(item.trip_role).strip() or _to_text(req.trip_role).strip(),
                    "shifts": float(item.shifts or 0.0),
                    "duration_hours": float(item.duration_hours or 0.0),
                    "tokens_used": int(item.tokens_used or 0),
                    "consumed_qty": float(item.consumed_qty or 0.0),
                }
                for item in tool_usages
            ],
        },
    )

    amount, energy_delta = _calculate_executor_cost(executor, req)
    updated_executor = executor.model_copy(
        update={
            "trip_count": int(executor.trip_count) + 1,
            "proof_count": int(executor.proof_count) + 1,
            "energy": EnergyProfile(
                billing_unit=_to_text(executor.energy.billing_unit).strip() or "trip",
                rate=float(executor.energy.rate),
                currency=_to_text(executor.energy.currency).strip() or "CNY",
                billing_formula=_to_text(executor.energy.billing_formula).strip() or "trip.units * rate",
                time_cost=float(executor.energy.time_cost),
                fee_rate=float(executor.energy.fee_rate),
                credit_limit=int(executor.energy.credit_limit),
                consumed=int(executor.energy.consumed) + int(energy_delta),
            ),
            "capacity": executor.capacity.model_copy(
                update={"current": int(executor.capacity.current_load) + 1}
            ),
            "last_active": _utc_now(),
            "proof_history": list(executor.proof_history) + [trip_uri],
        }
    )
    _upsert_executor(sb, updated_executor)

    _insert_railpact(
        sb,
        RailPactEntry(
            trip_uri=trip_uri,
            executor_uri=executor_uri,
            doc_id=req.doc_id,
            amount=amount,
            energy_delta=int(energy_delta),
            metadata={
                "sig_data": sig_data,
                "dto_role": req.dto_role,
                "trip_role": req.trip_role,
                "smu_type": "labor" if executor.executor_type == "human" else ("equipment" if executor.executor_type == "machine" else "ai"),
                "billing_unit": executor.energy.billing_unit,
                "rate": executor.energy.rate,
                "duration_hours": req.duration_hours,
                "shifts": req.shifts,
                "tokens_used": req.tokens_used,
            },
        ),
    )

    consumed_tool_uris: set[str] = set()
    for usage in tool_usages:
        t_uri = _normalize_uri(usage.tool_uri)
        if not t_uri:
            continue
        consumed_tool_uris.add(t_uri)
        tool_row = _get_executor_row(sb, t_uri)
        if tool_row:
            tool_exec = _executor_from_row(tool_row)
            use_executor(
                sb,
                tool_exec.executor_id,
                ExecutorUseRequest(
                    trip_id=req.doc_id,
                    trip_uri=trip_uri,
                    trip_role=_to_text(usage.trip_role).strip() or _to_text(req.trip_role).strip(),
                    shifts=float(usage.shifts or req.shifts or 0.0),
                    duration_hours=float(usage.duration_hours or req.duration_hours or 0.0),
                    tokens_used=int(usage.tokens_used or req.tokens_used or 0),
                    consumed_qty=float(usage.consumed_qty or 0.0),
                    note=_to_text(usage.note).strip(),
                ),
            )
            continue
        # Backward compatibility with legacy ToolPeg table.
        use_tool_by_uri(
            sb,
            tool_uri=t_uri,
            body=ToolUseRequest(
                trip_id=req.doc_id,
                trip_uri=trip_uri,
                trip_role=_to_text(usage.trip_role).strip() or _to_text(req.trip_role).strip(),
                shifts=float(usage.shifts or 0.0),
                duration_hours=float(usage.duration_hours or 0.0),
                tokens_used=int(usage.tokens_used or 0),
                consumed_qty=float(usage.consumed_qty or 0.0),
                note=_to_text(usage.note).strip(),
            ),
        )

    for dep_uri in executor.requires:
        dep_uri_n = _normalize_uri(dep_uri)
        if not dep_uri_n or dep_uri_n in consumed_tool_uris:
            continue
        dep_row = _get_executor_row(sb, dep_uri_n)
        if not dep_row:
            continue
        dep_exec = _executor_from_row(dep_row)
        use_executor(
            sb,
            dep_exec.executor_id,
            ExecutorUseRequest(
                trip_id=req.doc_id,
                trip_uri=trip_uri,
                trip_role=req.trip_role,
                shifts=float(req.shifts or 0.0),
                duration_hours=float(req.duration_hours or 0.0),
                tokens_used=int(req.tokens_used or 0),
                consumed_qty=0.0,
                note="required_dependency_auto_use",
            ),
        )

    signatures = _load_signatures(sb, req.doc_id)
    next_required = _next_required_role(signatures)
    next_executor = ""
    if next_required:
        scheduler = ExecutorScheduler(sb=sb)
        try:
            picked = _run_sync_assign(scheduler, dto_role=next_required, doc_id=req.doc_id)
            next_executor = picked.executor_uri
        except NoAvailableExecutorError:
            next_executor = ""
    _upsert_doc_state(
        sb,
        doc_id=req.doc_id,
        signatures=signatures,
        next_required=next_required,
        next_executor=next_executor,
    )
    return result


def verify(sb: Any, body: VerifyRequest) -> VerifyResponse:
    executor_uri = _normalize_uri(body.executor_uri)
    verified = verify_signature(
        body.sig_data,
        body.doc_id,
        body.body_hash,
        executor_uri,
        body.dto_role,
        body.trip_role,
        body.signed_at,
    )
    summary: ExecutorSummary | None = None
    try:
        executor = _get_executor(sb, executor_uri)
        summary = ExecutorSummary.from_executor(executor)
    except HTTPException:
        summary = None

    trip_uri = ""
    rows = (
        sb.table("gate_trips")
        .select("trip_uri")
        .eq("doc_id", body.doc_id)
        .eq("sig_data", body.sig_data)
        .limit(1)
        .execute()
        .data
        or []
    )
    if rows and isinstance(rows[0], dict):
        trip_uri = _to_text(rows[0].get("trip_uri")).strip()

    return VerifyResponse(
        verified=verified,
        executor=summary,
        trip_uri=trip_uri,
    )


def status(sb: Any, doc_id: str) -> SignStatusResponse:
    signatures = _load_signatures(sb, doc_id)
    next_required = _next_required_role(signatures)
    next_executor = ""
    if next_required:
        scheduler = ExecutorScheduler(sb=sb)
        try:
            picked = _run_sync_assign(scheduler, dto_role=next_required, doc_id=doc_id)
            next_executor = picked.executor_uri
        except NoAvailableExecutorError:
            next_executor = ""
    all_signed = next_required == ""
    return SignStatusResponse(
        signatures=signatures,
        all_signed=all_signed,
        next_required=next_required,
        next_executor=next_executor,
    )


def _run_sync_assign(scheduler: ExecutorScheduler, *, dto_role: str, doc_id: str) -> Executor:
    import asyncio

    required_skill = ROLE_TO_REQUIRED_SKILL.get(dto_role, dto_role)
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running and running.is_running():
        # Use deterministic fallback in async context to avoid nested loops.
        # The underlying call path is CPU-light and table-read only.
        rows = _as_list(
            scheduler.sb.table("san_executors").select("*").limit(2000).execute().data  # type: ignore[attr-defined]
        )
        executors = [
            _executor_from_row(row)
            for row in rows
            if isinstance(row, dict) and _executor_status_default(_to_text(row.get("status")).strip()) in {"active", "available", "in_use"}
        ]
        candidates = [
            item
            for item in executors
            if item.has_skill_for(dto_role) and item.capacity.current_load < item.capacity.max_concurrent and item.energy.consumed < item.energy.credit_limit
        ]
        if not candidates:
            raise NoAvailableExecutorError(f"no_available_executor: {dto_role} ({doc_id})")
        return min(candidates, key=lambda item: int(item.capacity.current_load))
    return asyncio.run(scheduler.assign(dto_role=dto_role, required_skill=required_skill, doc_id=doc_id))

