"""Acceptance runtime: bridge final acceptance (桥施64表) lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from fastapi import HTTPException

from services.api.domain.signpeg.models import (
    AcceptanceCondition,
    AcceptanceConditionSignRequest,
    AcceptanceConditionSignResponse,
    AcceptanceRecord,
    AcceptanceSubmitRequest,
    AcceptanceSubmitResponse,
    RailPactEntry,
)
from services.api.domain.signpeg.runtime.signpeg import _get_executor, build_signpeg_signature


ACTION_TO_RESULT = {
    "approve": "qualified",
    "reject": "rejected",
    "conditional_approve": "conditional",
}


def _validate_ca_requirement(*, ca_provider: str, ca_signature_id: str) -> None:
    if not _to_text(ca_provider).strip():
        raise HTTPException(status_code=422, detail="ca_provider_required_for_acceptance")
    if not _to_text(ca_signature_id).strip():
        raise HTTPException(status_code=422, detail="ca_signature_id_required_for_acceptance")


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_uri(value: Any) -> str:
    raw = _to_text(value).strip()
    return unquote(raw) if "%" in raw else raw


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


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


def _build_trip_uri(project_trip_root: str, signed_at: datetime) -> str:
    root = _normalize_uri(project_trip_root).rstrip("/") or "v://cn.大锦/DJGS"
    trip_id = f"TRIP-{uuid4().hex[:8].upper()}"
    date_str = signed_at.strftime("%Y/%m%d")
    return f"{root}/trip/{date_str}/{trip_id}"


def _build_final_proof_uri(component_uri: str, doc_id: str, signed_at: datetime) -> str:
    base = _normalize_uri(component_uri).rstrip("/")
    date_seg = signed_at.strftime("%Y/%m%d")
    short = hashlib.sha256(f"{base}:{doc_id}:{signed_at.isoformat()}".encode("utf-8")).hexdigest()[:10]
    return f"{base}/final-proof/{date_seg}/{short}"


def _insert_trip(
    sb: Any,
    *,
    trip_uri: str,
    doc_id: str,
    body_hash: str,
    executor_uri: str,
    executor_name: str,
    dto_role: str,
    trip_role: str,
    action: str,
    sig_data: str,
    signed_at: datetime,
    metadata: dict[str, Any] | None = None,
) -> None:
    sb.table("gate_trips").insert(
        {
            "trip_uri": trip_uri,
            "doc_id": doc_id,
            "body_hash": body_hash,
            "executor_uri": executor_uri,
            "executor_name": executor_name,
            "dto_role": dto_role,
            "trip_role": trip_role,
            "action": action,
            "sig_data": sig_data,
            "signed_at": signed_at.isoformat(),
            "verified": True,
            "delegation_uri": "",
            "created_at": _utc_now().isoformat(),
            "metadata": metadata or {},
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


def _upsert_doc_state(
    sb: Any,
    *,
    doc_id: str,
    lifecycle_stage: str,
    all_signed: bool,
    state_data: dict[str, Any],
) -> None:
    sb.table("docpeg_states").upsert(
        {
            "doc_id": doc_id,
            "lifecycle_stage": lifecycle_stage,
            "all_signed": bool(all_signed),
            "next_required": "",
            "next_executor": "",
            "state_data": state_data,
            "updated_at": _utc_now().isoformat(),
        },
        on_conflict="doc_id",
    ).execute()


def _row_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).strip().lower()
    return text in {"1", "t", "true", "yes", "y"}


def _load_state_row(sb: Any, doc_id: str) -> dict[str, Any] | None:
    rows = sb.table("docpeg_states").select("*").eq("doc_id", doc_id).limit(1).execute().data or []
    if not rows:
        return None
    row = rows[0]
    return row if isinstance(row, dict) else None


def _validate_preconditions(sb: Any, pre_doc_ids: list[str]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for doc_id in [str(item).strip() for item in pre_doc_ids if str(item).strip()]:
        row = _load_state_row(sb, doc_id)
        if not row:
            missing.append(f"{doc_id}:missing_state")
            continue
        stage = _to_text(row.get("lifecycle_stage")).strip().lower()
        all_signed = _row_bool(row.get("all_signed"))
        if stage != "approved" or not all_signed:
            missing.append(f"{doc_id}:stage={stage},all_signed={all_signed}")
            continue
        trips = sb.table("gate_trips").select("verified").eq("doc_id", doc_id).limit(200).execute().data or []
        if any(isinstance(item, dict) and not _row_bool(item.get("verified", True)) for item in trips):
            missing.append(f"{doc_id}:unverified_trip_exists")
    return len(missing) == 0, missing


def _upsert_acceptance_row(
    sb: Any,
    *,
    acceptance_id: str,
    component_uri: str,
    doc_id: str,
    status: str,
    latest_trip_uri: str,
    pre_doc_ids: list[str],
    conclusion: dict[str, Any],
    on_approved: dict[str, Any],
    pre_conditions_passed: bool,
    final_proof_uri: str,
    boq_status: str,
    archived_to_docfinal: bool,
    component_locked: bool,
    pre_rejection_trip_uri: str,
) -> None:
    sb.table("docpeg_acceptances").upsert(
        {
            "acceptance_id": acceptance_id,
            "component_uri": component_uri,
            "doc_id": doc_id,
            "status": status,
            "latest_trip_uri": latest_trip_uri,
            "pre_doc_ids": pre_doc_ids,
            "conclusion": conclusion,
            "on_approved": on_approved,
            "pre_conditions_passed": bool(pre_conditions_passed),
            "final_proof_uri": final_proof_uri,
            "boq_status": boq_status,
            "archived_to_docfinal": bool(archived_to_docfinal),
            "component_locked": bool(component_locked),
            "pre_rejection_trip_uri": pre_rejection_trip_uri,
            "updated_at": _utc_now().isoformat(),
        },
        on_conflict="acceptance_id",
    ).execute()


def _save_conditions(sb: Any, acceptance_id: str, conditions: list[str]) -> list[AcceptanceCondition]:
    out: list[AcceptanceCondition] = []
    for idx, text in enumerate([str(item).strip() for item in conditions if str(item).strip()], start=1):
        condition_id = f"COND-{idx:03d}"
        model = AcceptanceCondition(condition_id=condition_id, content=text, status="pending")
        out.append(model)
        sb.table("docpeg_acceptance_conditions").upsert(
            {
                "acceptance_id": acceptance_id,
                "condition_id": condition_id,
                "content": text,
                "status": "pending",
                "signed_by": "",
                "signed_at": None,
                "updated_at": _utc_now().isoformat(),
            },
            on_conflict="acceptance_id,condition_id",
        ).execute()
    return out


def _apply_approved_actions(
    sb: Any,
    *,
    acceptance_id: str,
    component_uri: str,
    doc_id: str,
    trip_uri: str,
    executor_uri: str,
    on_approved: dict[str, Any],
    payment_amount: float,
) -> tuple[str, str, bool, bool]:
    final_proof_uri = ""
    boq_status = ""
    archived_to_docfinal = False
    component_locked = False

    if bool(on_approved.get("generate_final_proof", True)):
        final_proof_uri = _build_final_proof_uri(component_uri, doc_id, _utc_now())
    if _to_text(on_approved.get("update_boq")).strip():
        boq_status = "PROOF_VERIFIED"
        sb.table("docpeg_boq_status").upsert(
            {
                "acceptance_id": acceptance_id,
                "doc_id": doc_id,
                "boq_item_code": _to_text(on_approved.get("update_boq")).strip(),
                "status": boq_status,
                "updated_at": _utc_now().isoformat(),
            },
            on_conflict="acceptance_id,boq_item_code",
        ).execute()
    if bool(on_approved.get("trigger_railpact", True)):
        _insert_railpact(
            sb,
            RailPactEntry(
                trip_uri=trip_uri,
                executor_uri=executor_uri,
                doc_id=doc_id,
                amount=float(max(payment_amount, 0.0)),
                energy_delta=0,
                metadata={"kind": "acceptance_release", "acceptance_id": acceptance_id},
            ),
        )
    if bool(on_approved.get("archive_to_docfinal", True)):
        archived_to_docfinal = True
        sb.table("docfinal_archives").upsert(
            {
                "acceptance_id": acceptance_id,
                "component_uri": component_uri,
                "doc_id": doc_id,
                "final_proof_uri": final_proof_uri,
                "archived_at": _utc_now().isoformat(),
                "docfinal_uri": f"v://docfinal.com/archive/{acceptance_id}",
            },
            on_conflict="acceptance_id",
        ).execute()
    if bool(on_approved.get("lock_component_uri", True)):
        component_locked = True
        sb.table("docpeg_component_locks").upsert(
            {
                "component_uri": component_uri,
                "acceptance_id": acceptance_id,
                "locked_at": _utc_now().isoformat(),
                "lock_reason": "acceptance_approved",
            },
            on_conflict="component_uri",
        ).execute()
    return final_proof_uri, boq_status, archived_to_docfinal, component_locked


def submit_acceptance(sb: Any, body: AcceptanceSubmitRequest) -> AcceptanceSubmitResponse:
    executor_uri = _normalize_uri(body.executor_uri)
    component_uri = _normalize_uri(body.component_uri)
    if not component_uri:
        raise HTTPException(status_code=400, detail="component_uri_required")
    executor = _get_executor(sb, executor_uri)
    if not executor.status_available():
        raise HTTPException(status_code=409, detail=f"executor_not_active: {executor.status}")
    if not executor.cert_valid():
        raise HTTPException(status_code=403, detail="executor_cert_invalid")
    if body.dto_role and not executor.has_skill_for(body.dto_role):
        raise HTTPException(status_code=403, detail=f"skill_mismatch_for_role: {body.dto_role}")
    _validate_ca_requirement(ca_provider=body.ca_provider, ca_signature_id=body.ca_signature_id)

    expected_result = ACTION_TO_RESULT.get(body.action)
    if not expected_result:
        raise HTTPException(status_code=400, detail=f"unsupported_action: {body.action}")
    if body.conclusion.result != expected_result:
        raise HTTPException(
            status_code=400,
            detail=f"conclusion_result_mismatch: action={body.action}, result={body.conclusion.result}",
        )

    pre_ok, pre_missing = _validate_preconditions(sb, body.pre_doc_ids)
    if not pre_ok:
        raise HTTPException(status_code=409, detail=f"pre_conditions_failed: {'; '.join(pre_missing)}")

    if body.conclusion.result == "conditional" and not body.conclusion.conditions:
        raise HTTPException(status_code=400, detail="conditional_result_requires_conditions")

    signed_at = _utc_now()
    sig_data = build_signpeg_signature(
        body.doc_id,
        body.body_hash,
        executor_uri,
        body.dto_role,
        body.trip_role,
        signed_at,
    )
    trip_uri = _build_trip_uri(body.project_trip_root, signed_at)
    action_label = f"acceptance.{body.action}"
    _insert_trip(
        sb,
        trip_uri=trip_uri,
        doc_id=body.doc_id,
        body_hash=body.body_hash,
        executor_uri=executor_uri,
        executor_name=executor.holder_name,
        dto_role=body.dto_role,
        trip_role=body.trip_role,
        action=action_label,
        sig_data=sig_data,
        signed_at=signed_at,
        metadata={
            "acceptance_id": body.acceptance_id,
            "component_uri": component_uri,
            "ca_provider": _to_text(body.ca_provider).strip(),
            "ca_signature_id": _to_text(body.ca_signature_id).strip(),
            "ca_signed_payload_hash": _to_text(body.ca_signed_payload_hash).strip(),
            "signature_mode": "archive",
        },
    )

    final_proof_uri = ""
    boq_status = ""
    railpact_triggered = False
    archived_to_docfinal = False
    component_locked = False

    if body.conclusion.result == "qualified":
        final_proof_uri, boq_status, archived_to_docfinal, component_locked = _apply_approved_actions(
            sb,
            acceptance_id=body.acceptance_id,
            component_uri=component_uri,
            doc_id=body.doc_id,
            trip_uri=trip_uri,
            executor_uri=executor_uri,
            on_approved=body.on_approved.model_dump(mode="json"),
            payment_amount=body.payment_amount,
        )
        railpact_triggered = bool(body.on_approved.trigger_railpact)
        _upsert_doc_state(
            sb,
            doc_id=body.doc_id,
            lifecycle_stage="approved",
            all_signed=True,
            state_data={
                "acceptance_id": body.acceptance_id,
                "component_uri": component_uri,
                "status": "qualified",
                "trip_uri": trip_uri,
                "final_proof_uri": final_proof_uri,
            },
        )
    elif body.conclusion.result == "rejected":
        for pre_doc_id in body.pre_doc_ids:
            _upsert_doc_state(
                sb,
                doc_id=pre_doc_id,
                lifecycle_stage="draft",
                all_signed=False,
                state_data={
                    "acceptance_rejected_by": body.acceptance_id,
                    "acceptance_rejection_trip_uri": trip_uri,
                    "reason": body.conclusion.remarks,
                },
            )
        sb.table("docpeg_rectification_notices").insert(
            {
                "acceptance_id": body.acceptance_id,
                "doc_id": body.doc_id,
                "component_uri": component_uri,
                "rejection_trip_uri": trip_uri,
                "reason": body.conclusion.remarks,
                "created_at": _utc_now().isoformat(),
            }
        ).execute()
        _upsert_doc_state(
            sb,
            doc_id=body.doc_id,
            lifecycle_stage="rejected",
            all_signed=False,
            state_data={
                "acceptance_id": body.acceptance_id,
                "component_uri": component_uri,
                "status": "rejected",
                "trip_uri": trip_uri,
            },
        )
    else:
        _save_conditions(sb, body.acceptance_id, body.conclusion.conditions)
        _upsert_doc_state(
            sb,
            doc_id=body.doc_id,
            lifecycle_stage="conditional",
            all_signed=False,
            state_data={
                "acceptance_id": body.acceptance_id,
                "component_uri": component_uri,
                "status": "conditional",
                "trip_uri": trip_uri,
                "conditions_total": len(body.conclusion.conditions),
            },
        )

    _upsert_acceptance_row(
        sb,
        acceptance_id=body.acceptance_id,
        component_uri=component_uri,
        doc_id=body.doc_id,
        status=body.conclusion.result,
        latest_trip_uri=trip_uri,
        pre_doc_ids=body.pre_doc_ids,
        conclusion=body.conclusion.model_dump(mode="json"),
        on_approved=body.on_approved.model_dump(mode="json"),
        pre_conditions_passed=pre_ok,
        final_proof_uri=final_proof_uri,
        boq_status=boq_status,
        archived_to_docfinal=archived_to_docfinal,
        component_locked=component_locked,
        pre_rejection_trip_uri=body.pre_rejection_trip_uri,
    )

    return AcceptanceSubmitResponse(
        acceptance_id=body.acceptance_id,
        component_uri=component_uri,
        result=body.conclusion.result,
        trip_uri=trip_uri,
        sig_data=sig_data,
        signed_at=signed_at,
        pre_conditions_passed=pre_ok,
        final_proof_uri=final_proof_uri,
        boq_status=boq_status,
        railpact_triggered=railpact_triggered,
        archived_to_docfinal=archived_to_docfinal,
        component_locked=component_locked,
        pre_rejection_trip_uri=body.pre_rejection_trip_uri,
        ca_provider=_to_text(body.ca_provider).strip(),
        ca_signature_id=_to_text(body.ca_signature_id).strip(),
    )


def _load_acceptance_row(sb: Any, acceptance_id: str) -> dict[str, Any]:
    rows = sb.table("docpeg_acceptances").select("*").eq("acceptance_id", acceptance_id).limit(1).execute().data or []
    if not rows or not isinstance(rows[0], dict):
        raise HTTPException(status_code=404, detail=f"acceptance_not_found: {acceptance_id}")
    return rows[0]


def _load_conditions(sb: Any, acceptance_id: str) -> list[AcceptanceCondition]:
    rows = (
        sb.table("docpeg_acceptance_conditions")
        .select("*")
        .eq("acceptance_id", acceptance_id)
        .order("condition_id", desc=False)
        .limit(500)
        .execute()
        .data
        or []
    )
    out: list[AcceptanceCondition] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            AcceptanceCondition(
                condition_id=_to_text(row.get("condition_id")).strip(),
                content=_to_text(row.get("content")).strip(),
                status=_to_text(row.get("status")).strip() or "pending",
                signed_by=_to_text(row.get("signed_by")).strip(),
                signed_at=_to_utc(row.get("signed_at")) if row.get("signed_at") else None,
            )
        )
    return out


def get_acceptance(sb: Any, acceptance_id: str) -> AcceptanceRecord:
    row = _load_acceptance_row(sb, acceptance_id)
    return AcceptanceRecord(
        acceptance_id=_to_text(row.get("acceptance_id")).strip(),
        component_uri=_to_text(row.get("component_uri")).strip(),
        doc_id=_to_text(row.get("doc_id")).strip(),
        status=_to_text(row.get("status")).strip() or "conditional",
        latest_trip_uri=_to_text(row.get("latest_trip_uri")).strip(),
        pre_rejection_trip_uri=_to_text(row.get("pre_rejection_trip_uri")).strip(),
        final_proof_uri=_to_text(row.get("final_proof_uri")).strip(),
        boq_status=_to_text(row.get("boq_status")).strip(),
        archived_to_docfinal=_row_bool(row.get("archived_to_docfinal")),
        component_locked=_row_bool(row.get("component_locked")),
        conditions=_load_conditions(sb, acceptance_id),
        updated_at=_to_utc(row.get("updated_at")),
    )


def sign_acceptance_condition(sb: Any, body: AcceptanceConditionSignRequest) -> AcceptanceConditionSignResponse:
    acceptance = _load_acceptance_row(sb, body.acceptance_id)
    if _to_text(acceptance.get("status")).strip() != "conditional":
        raise HTTPException(status_code=409, detail="acceptance_not_conditional")

    executor = _get_executor(sb, _normalize_uri(body.executor_uri))
    if not executor.status_available():
        raise HTTPException(status_code=409, detail=f"executor_not_active: {executor.status}")
    _validate_ca_requirement(ca_provider=body.ca_provider, ca_signature_id=body.ca_signature_id)

    rows = (
        sb.table("docpeg_acceptance_conditions")
        .select("*")
        .eq("acceptance_id", body.acceptance_id)
        .eq("condition_id", body.condition_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows or not isinstance(rows[0], dict):
        raise HTTPException(status_code=404, detail=f"condition_not_found: {body.condition_id}")
    condition_row = rows[0]
    if _to_text(condition_row.get("status")).strip() == "signed":
        raise HTTPException(status_code=409, detail="condition_already_signed")

    signed_at = _utc_now()
    trip_uri = _build_trip_uri(body.project_trip_root, signed_at)
    trip_role = "acceptance.condition.sign"
    sig_data = build_signpeg_signature(
        _to_text(acceptance.get("doc_id")).strip(),
        body.body_hash,
        executor.executor_uri,
        body.dto_role,
        trip_role,
        signed_at,
    )
    _insert_trip(
        sb,
        trip_uri=trip_uri,
        doc_id=_to_text(acceptance.get("doc_id")).strip(),
        body_hash=body.body_hash,
        executor_uri=executor.executor_uri,
        executor_name=executor.holder_name,
        dto_role=body.dto_role,
        trip_role=trip_role,
        action="acceptance.condition.sign",
        sig_data=sig_data,
        signed_at=signed_at,
        metadata={
            "acceptance_id": body.acceptance_id,
            "condition_id": body.condition_id,
            "ca_provider": _to_text(body.ca_provider).strip(),
            "ca_signature_id": _to_text(body.ca_signature_id).strip(),
            "signature_mode": "archive",
        },
    )

    sb.table("docpeg_acceptance_conditions").update(
        {
            "status": "signed",
            "signed_by": executor.executor_uri,
            "signed_at": signed_at.isoformat(),
            "updated_at": _utc_now().isoformat(),
        }
    ).eq("acceptance_id", body.acceptance_id).eq("condition_id", body.condition_id).execute()

    all_rows = (
        sb.table("docpeg_acceptance_conditions")
        .select("status")
        .eq("acceptance_id", body.acceptance_id)
        .limit(1000)
        .execute()
        .data
        or []
    )
    all_signed = all_rows and all(
        isinstance(item, dict) and _to_text(item.get("status")).strip() in {"signed", "waived"} for item in all_rows
    )

    acceptance_promoted = False
    final_proof_uri = ""
    if all_signed:
        on_approved = _as_dict(acceptance.get("on_approved"))
        final_proof_uri, boq_status, archived_to_docfinal, component_locked = _apply_approved_actions(
            sb,
            acceptance_id=body.acceptance_id,
            component_uri=_to_text(acceptance.get("component_uri")).strip(),
            doc_id=_to_text(acceptance.get("doc_id")).strip(),
            trip_uri=trip_uri,
            executor_uri=executor.executor_uri,
            on_approved=on_approved,
            payment_amount=0.0,
        )
        acceptance_promoted = True
        sb.table("docpeg_acceptances").update(
            {
                "status": "qualified",
                "latest_trip_uri": trip_uri,
                "final_proof_uri": final_proof_uri,
                "boq_status": boq_status,
                "archived_to_docfinal": bool(archived_to_docfinal),
                "component_locked": bool(component_locked),
                "updated_at": _utc_now().isoformat(),
            }
        ).eq("acceptance_id", body.acceptance_id).execute()
        _upsert_doc_state(
            sb,
            doc_id=_to_text(acceptance.get("doc_id")).strip(),
            lifecycle_stage="approved",
            all_signed=True,
            state_data={
                "acceptance_id": body.acceptance_id,
                "status": "qualified",
                "promoted_from": "conditional",
                "trip_uri": trip_uri,
                "final_proof_uri": final_proof_uri,
            },
        )

    return AcceptanceConditionSignResponse(
        acceptance_id=body.acceptance_id,
        condition_id=body.condition_id,
        signed=True,
        signed_at=signed_at,
        trip_uri=trip_uri,
        acceptance_promoted=acceptance_promoted,
        final_proof_uri=final_proof_uri,
    )
