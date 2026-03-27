"""
QCSpec inspection routes
services/api/routers/inspections.py
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
import hashlib
import json
import os
import re
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from postgrest.exceptions import APIError
from supabase import Client, create_client

from specir_engine import (
    derive_spec_uri as specir_derive_spec_uri,
    evaluate_measurements as specir_evaluate_measurements,
    resolve_spec_rule as specir_resolve_spec_rule,
    spec_excerpt as specir_spec_excerpt,
    threshold_text as specir_threshold_text,
)

from .erpnext import (
    evaluate_erpnext_gate_for_inspection,
    load_erpnext_custom,
    notify_erpnext_for_inspection,
)
from .proof_utxo_engine import ProofUTXOEngine

router = APIRouter()

@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


class InspectionCreate(BaseModel):
    project_id: str
    location: str
    type: str
    type_name: str
    value: Optional[float] = None
    standard: Optional[float] = None
    unit: str = ""
    result: str  # pass / warn / fail
    person: Optional[str] = None
    remark: Optional[str] = None
    inspected_at: Optional[str] = None
    photo_ids: Optional[List[str]] = []
    # Live rebar fields (Proof UTXO compatible state_data payload).
    design: Optional[float] = None
    limit: Optional[str] = None
    values: Optional[List[float]] = None
    # SpecIR optional inputs.
    spec_uri: Optional[str] = None
    norm_uri: Optional[str] = None
    component_type: Optional[str] = None
    structure_type: Optional[str] = None


class InspectionFilter(BaseModel):
    result: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _run_with_retry(fn, retries: int = 1):
    last_err = None
    for _ in range(retries + 1):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout) as e:
            last_err = e
            continue
    if last_err:
        raise last_err


def _gen_proof(v_uri: str, data: dict) -> str:
    payload = json.dumps(
        {
            "uri": v_uri,
            "data": data,
            "ts": datetime.utcnow().isoformat(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    h = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
    return f"GP-PROOF-{h}"


def _guess_owner_uri(project_uri: str, person: Optional[str]) -> str:
    person_name = str(person or "").strip()
    root = str(project_uri or "").strip()
    for marker in ("/highway/", "/bridge/", "/urban/", "/road/", "/tunnel/"):
        idx = root.find(marker)
        if idx > 0:
            root = root[: idx + 1]
            break
    if not root.endswith("/"):
        root += "/"
    if person_name:
        return f"{root}executor/{person_name}/"
    return f"{root}executor/system/"


def _to_utxo_result(result: str) -> str:
    text = str(result or "").strip().lower()
    if text == "pass":
        return "PASS"
    if text == "fail":
        return "FAIL"
    if text == "warn":
        return "OBSERVE"
    return "PENDING"


def _parse_limit_value(limit_text: Optional[str]) -> Optional[float]:
    text = str(limit_text or "").strip()
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return abs(float(m.group(0)))
    except Exception:
        return None


def _evaluate_design_limit_result(
    *,
    design: Optional[float],
    limit_text: Optional[str],
    values: Optional[list[float]],
) -> Optional[str]:
    if design is None:
        return None
    limit_value = _parse_limit_value(limit_text)
    if limit_value is None:
        return None
    clean_values = [float(v) for v in (values or [])]
    if not clean_values:
        return None
    lower = float(design) - float(limit_value)
    upper = float(design) + float(limit_value)
    out_of_range = any(v < lower or v > upper for v in clean_values)
    return "fail" if out_of_range else "pass"


def _extract_photo_hash(photo: dict[str, Any]) -> str:
    for key in ("evidence_hash", "sha256", "file_sha256", "hash"):
        text = str(photo.get(key) or "").strip().lower()
        if text:
            return text
    return ""


def _extract_photo_media_type(photo: dict[str, Any]) -> str:
    ctype = str(photo.get("content_type") or "").strip().lower()
    if ctype.startswith("image/"):
        return "image"
    if ctype.startswith("video/"):
        return "video"
    name = str(photo.get("file_name") or "").lower()
    if name.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic")):
        return "image"
    if name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")):
        return "video"
    return "file"


def _utxo_anchor_config(custom: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": custom.get("proof_utxo_gitpeg_anchor_enabled"),
        "base_url": custom.get("gitpeg_registrar_base_url"),
        "anchor_path": custom.get("gitpeg_proof_anchor_path") or "/api/v1/proof/anchor",
        "anchor_endpoint": custom.get("gitpeg_proof_anchor_endpoint"),
        "auth_token": custom.get("gitpeg_anchor_token")
        or custom.get("gitpeg_token")
        or custom.get("gitpeg_client_secret"),
        "timeout_s": custom.get("gitpeg_proof_anchor_timeout_s") or 6,
    }


def _utxo_auto_consume_enabled(custom: dict[str, Any]) -> bool:
    value = custom.get("proof_utxo_auto_consume")
    if isinstance(value, bool):
        return value
    text = str(value or os.getenv("PROOF_UTXO_AUTO_CONSUME") or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


@router.get("/")
async def list_inspections(
    project_id: str,
    result: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    sb: Client = Depends(get_supabase),
):
    """List inspections by project."""
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    def _query():
        q = (
            sb.table("inspections")
            .select("*")
            .eq("project_id", project_id)
            .order("inspected_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if result:
            q = q.eq("result", result)
        if type:
            q = q.eq("type", type)
        return q.execute()

    try:
        res = _run_with_retry(_query, retries=1)
        rows = res.data or []
        return {"data": rows, "count": len(rows)}
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        raise HTTPException(502, "Failed to query inspections from database.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        # Avoid breaking the whole page for transient upstream disconnects.
        return {"data": [], "count": 0}


@router.post("/", status_code=201)
async def create_inspection(
    body: InspectionCreate,
    sb: Client = Depends(get_supabase),
):
    """Create an inspection and append proof-chain record."""
    if not _is_uuid(body.project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    try:
        proj = _run_with_retry(
            lambda: sb.table("projects")
            .select("id, v_uri, enterprise_id, name, contract_no, erp_project_code, erp_project_name")
            .eq("id", body.project_id)
            .single()
            .execute(),
            retries=1,
        )
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        raise HTTPException(502, "Failed to query project.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(503, "Database temporarily unavailable. Please retry.")

    if not proj.data:
        raise HTTPException(404, "Project not found")

    proj_uri = proj.data["v_uri"]
    ent_id = proj.data["enterprise_id"]
    custom = load_erpnext_custom(sb, ent_id)

    values_for_eval = [float(v) for v in (body.values or [])]
    if not values_for_eval and body.value is not None:
        values_for_eval = [float(body.value)]

    spec_uri = specir_derive_spec_uri(
        {
            "spec_uri": body.spec_uri,
            "norm_uri": body.norm_uri,
            "norm_ref": body.spec_uri,
            "type": body.type,
            "type_name": body.type_name,
            "component_type": body.component_type,
            "structure_type": body.structure_type,
        },
        row_norm_uri=body.norm_uri,
        fallback_norm_ref=body.spec_uri,
    )
    spec_rule = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=body.type_name or body.type,
        test_type=body.type,
        test_name=body.type_name,
        context={
            "component_type": body.component_type,
            "structure_type": body.structure_type,
            "stake": body.location,
        },
        sb=sb,
    )
    rule_operator = str(spec_rule.get("operator") or "").strip()
    rule_threshold = (
        float(spec_rule["threshold"])
        if spec_rule.get("threshold") is not None
        else (body.standard if body.standard is not None else body.design)
    )
    rule_tolerance = (
        float(spec_rule["tolerance"])
        if spec_rule.get("tolerance") is not None
        else _parse_limit_value(body.limit)
    )
    eval_result = specir_evaluate_measurements(
        values=values_for_eval,
        operator=rule_operator,
        threshold=rule_threshold,
        tolerance=rule_tolerance,
        fallback_result="PENDING",
    )
    spec_auto_result = str(eval_result.get("result") or "").upper()
    auto_result = _evaluate_design_limit_result(
        design=body.design,
        limit_text=body.limit,
        values=values_for_eval,
    )
    if spec_auto_result in {"PASS", "FAIL"}:
        final_result = spec_auto_result.lower()
        result_source = "specir_dynamic"
    elif auto_result in {"pass", "fail"}:
        final_result = auto_result
        result_source = "auto_design_limit"
    else:
        final_result = str(body.result or "").strip().lower()
        result_source = "manual"
    if final_result not in {"pass", "warn", "fail"}:
        raise HTTPException(400, "result must be one of pass/warn/fail")

    measured_value = body.value
    if measured_value is None and values_for_eval:
        measured_value = round(sum(values_for_eval) / len(values_for_eval), 4)
    if measured_value is None:
        raise HTTPException(400, "value is required")

    standard_value = body.standard
    if standard_value is None and body.design is not None:
        standard_value = body.design
    if standard_value is None and rule_threshold is not None:
        standard_value = float(rule_threshold)

    effective_spec_uri = str(spec_rule.get("effective_spec_uri") or spec_uri or "")
    spec_snapshot = str(spec_rule.get("excerpt") or specir_spec_excerpt(effective_spec_uri))
    spec_meta = {
        "spec_uri": effective_spec_uri,
        "spec_version": str(spec_rule.get("version") or ""),
        "spec_snapshot": spec_snapshot,
        "captured_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "operator": rule_operator or "",
        "threshold": rule_threshold,
        "tolerance": rule_tolerance,
    }

    photo_ids = [pid for pid in (body.photo_ids or []) if _is_uuid(pid)]
    evidence_list: list[dict[str, Any]] = []
    evidence_hashes: list[str] = []
    evidence_proof_ids: list[str] = []
    if photo_ids:
        try:
            photo_rows = _run_with_retry(
                lambda: sb.table("photos")
                .select("*")
                .eq("project_id", body.project_id)
                .in_("id", photo_ids)
                .execute(),
                retries=1,
            )
            for photo in photo_rows.data or []:
                if not isinstance(photo, dict):
                    continue
                ehash = _extract_photo_hash(photo)
                ppid = str(photo.get("proof_id") or "").strip()
                item = {
                    "id": str(photo.get("id") or ""),
                    "file_name": str(photo.get("file_name") or ""),
                    "media_type": _extract_photo_media_type(photo),
                    "url": str(photo.get("storage_url") or ""),
                    "proof_id": ppid,
                    "proof_hash": str(photo.get("proof_hash") or ""),
                    "evidence_hash": ehash,
                    "size": photo.get("file_size"),
                    "taken_at": str(photo.get("taken_at") or photo.get("created_at") or datetime.utcnow().isoformat()),
                }
                evidence_list.append(item)
                if ehash:
                    evidence_hashes.append(ehash)
                if ppid:
                    evidence_proof_ids.append(ppid)
        except Exception:
            evidence_list = []
            evidence_hashes = []
            evidence_proof_ids = []

    gate_pack = await evaluate_erpnext_gate_for_inspection(
        custom,
        project_code=str(proj.data.get("erp_project_code") or "").strip() or None,
        stake=str(body.location or "").strip(),
        subitem=str(body.type_name or body.type or "").strip(),
        result=final_result,
    )
    gate = gate_pack.get("gate") if isinstance(gate_pack.get("gate"), dict) else {}
    gate_soft_override_reason: Optional[str] = None
    if bool(gate.get("enabled")) and not bool(gate.get("allow_submit")):
        reason = str(gate.get("reason") or "erpnext_gate_blocked")
        # Save inspection first when ERP metering lookup is temporarily unavailable.
        # ERP release remains blocked by gate.action/can_release in notify payload.
        if reason == "metering_lookup_failed":
            gate_soft_override_reason = reason
        else:
            raise HTTPException(
                409,
                f"erpnext_gate_blocked:{reason}",
            )
    now = body.inspected_at or datetime.utcnow().isoformat()

    rec = {
        "project_id": body.project_id,
        "enterprise_id": ent_id,
        "location": body.location,
        "type": body.type,
        "type_name": body.type_name,
        "value": measured_value,
        "standard": standard_value,
        "unit": body.unit,
        "result": final_result,
        "person": body.person,
        "remark": body.remark,
        "inspected_at": now,
    }

    try:
        ins = _run_with_retry(lambda: sb.table("inspections").insert(rec).execute(), retries=1)
    except APIError:
        raise HTTPException(502, "Failed to write inspection.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(503, "Database temporarily unavailable. Please retry.")

    if not ins.data:
        raise HTTPException(500, "Failed to write inspection")

    insp = ins.data[0]
    v_uri = insp.get("v_uri") or f"{proj_uri}inspection/{insp['id']}/"

    proof_id = _gen_proof(
        v_uri,
        {
            "value": measured_value,
            "result": final_result,
            "location": body.location,
        },
    )

    try:
        _run_with_retry(
            lambda: sb.table("inspections")
            .update({"proof_id": proof_id, "proof_status": "confirmed"})
            .eq("id", insp["id"])
            .execute(),
            retries=1,
        )
    except Exception:
        pass

    try:
        _run_with_retry(
            lambda: sb.table("proof_chain").insert(
                {
                    "proof_id": proof_id,
                    "proof_hash": proof_id.replace("GP-PROOF-", "").lower(),
                    "enterprise_id": ent_id,
                    "project_id": body.project_id,
                    "v_uri": v_uri,
                    "object_type": "inspection",
                    "object_id": insp["id"],
                    "action": "create",
                    "summary": f"质检录入·{body.type_name}·{body.location}·{final_result}",
                    "status": "confirmed",
                }
            ).execute(),
            retries=1,
        )
    except Exception:
        pass

    utxo_row: dict[str, Any] | None = None
    remediation_task: dict[str, Any] | None = None
    utxo_auto_consume: dict[str, Any] = {"attempted": False, "success": False, "reason": "not_triggered"}
    try:
        rule_threshold_text = specir_threshold_text(
            rule_operator,
            rule_threshold,
            rule_tolerance,
            spec_rule.get("unit") or body.unit or "",
        )
        engine = ProofUTXOEngine(sb)
        utxo_row = engine.create(
            proof_id=proof_id,
            owner_uri=_guess_owner_uri(proj_uri, body.person),
            project_id=body.project_id,
            project_uri=proj_uri,
            proof_type="inspection",
            result=_to_utxo_result(final_result),
            state_data={
                "inspection_id": insp["id"],
                "v_uri": v_uri,
                "location": body.location,
                "type": body.type,
                "type_name": body.type_name,
                "value": measured_value,
                "standard": standard_value,
                "unit": body.unit,
                "result": final_result,
                "remark": body.remark,
                "design": body.design,
                "limit": body.limit,
                "values": values_for_eval,
                "spec_uri": effective_spec_uri,
                "norm_uri": effective_spec_uri,
                "norm_ref": effective_spec_uri,
                "spec_excerpt": spec_snapshot,
                "spec_version": spec_rule.get("version"),
                "component_type": body.component_type,
                "structure_type": body.structure_type,
                "standard_op": rule_operator or None,
                "standard_value": rule_threshold,
                "standard_tolerance": rule_tolerance,
                "threshold_text": rule_threshold_text,
                "deviation_percent": eval_result.get("deviation_percent"),
                "evidence": evidence_list,
                "evidence_hashes": evidence_hashes,
                "evidence_proof_ids": evidence_proof_ids,
                "meta": spec_meta,
            },
            signer_uri=_guess_owner_uri(proj_uri, body.person),
            signer_role="AI",
            conditions=[],
            parent_proof_id=None,
            norm_uri=effective_spec_uri or None,
            anchor_config=_utxo_anchor_config(custom),
        )
        if _to_utxo_result(final_result) == "FAIL":
            issue_seed = hashlib.sha256(f"{proof_id}|rectify".encode("utf-8")).hexdigest()[:8].upper()
            issue_id = f"RC-{issue_seed}"
            remediation_task = engine.create(
                proof_id=f"GP-RECT-{issue_seed}",
                owner_uri=_guess_owner_uri(proj_uri, body.person),
                project_id=body.project_id,
                project_uri=proj_uri,
                proof_type="rectification_task",
                result="PENDING",
                state_data={
                    "issue_id": issue_id,
                    "source_proof_id": proof_id,
                    "remediation_of": proof_id,
                    "status": "open",
                    "gate_action": "hold_metering",
                    "reason": "inspection_fail_auto_trigger",
                    "location": body.location,
                    "stake": body.location,
                    "type": body.type,
                    "type_name": body.type_name,
                    "spec_uri": effective_spec_uri,
                },
                signer_uri=_guess_owner_uri(proj_uri, body.person),
                signer_role="AI",
                conditions=[],
                parent_proof_id=proof_id,
                norm_uri=effective_spec_uri or None,
                anchor_config=_utxo_anchor_config(custom),
            )
        if _to_utxo_result(final_result) == "PASS" and _utxo_auto_consume_enabled(custom):
            utxo_auto_consume = engine.auto_consume_inspection_pass(
                inspection_proof_id=proof_id,
                executor_uri=_guess_owner_uri(proj_uri, body.person),
                executor_role="AI",
                trigger_action="railpact.settle",
                anchor_config=_utxo_anchor_config(custom),
            )
    except Exception:
        # Keep backward compatibility when proof_utxo migration is not yet applied.
        pass

    linked_photo_count = 0
    if photo_ids:
        try:
            linked = _run_with_retry(
                lambda: sb.table("photos")
                .update({"inspection_id": insp["id"]})
                .eq("project_id", body.project_id)
                .in_("id", photo_ids)
                .execute(),
                retries=1,
            )
            linked_photo_count = len(linked.data or [])
        except Exception:
            linked_photo_count = 0

    erpnext_notify: dict = {"attempted": False, "success": False, "reason": "not_triggered"}
    try:
        erpnext_notify = await notify_erpnext_for_inspection(
            custom,
            project={
                "id": proj.data.get("id"),
                "enterprise_id": ent_id,
                "v_uri": proj_uri,
                "name": proj.data.get("name"),
                "erp_project_code": proj.data.get("erp_project_code"),
                "erp_project_name": proj.data.get("erp_project_name"),
                "contract_no": proj.data.get("contract_no"),
            },
            inspection={
                "id": insp.get("id"),
                "location": body.location,
                "type": body.type,
                "type_name": body.type_name,
                "result": final_result,
                "value": measured_value,
                "standard": standard_value,
                "unit": body.unit,
            },
            proof_id=proof_id,
        )
    except Exception as exc:
        erpnext_notify = {
            "attempted": True,
            "success": False,
            "reason": f"notify_exception:{exc.__class__.__name__}",
        }

    return {
        "inspection_id": insp["id"],
        "v_uri": v_uri,
        "proof_id": proof_id,
        "result": final_result,
        "result_source": result_source,
        "computed_value": measured_value,
        "design": body.design,
        "limit": body.limit,
        "values": values_for_eval,
        "spec_uri": str(spec_rule.get("effective_spec_uri") or spec_uri or ""),
        "spec_version": str(spec_rule.get("version") or ""),
        "rule_operator": rule_operator or "",
        "rule_threshold": rule_threshold,
        "rule_tolerance": rule_tolerance,
        "deviation_percent": eval_result.get("deviation_percent"),
        "spec_snapshot": spec_snapshot,
        "action_item_id": (
            ((remediation_task.get("state_data") or {}).get("issue_id") if isinstance(remediation_task, dict) else "")
            or ""
        ),
        "evidence": evidence_list,
        "linked_photo_count": linked_photo_count,
        "utxo_proof": {
            "proof_id": utxo_row.get("proof_id") if isinstance(utxo_row, dict) else proof_id,
            "proof_hash": utxo_row.get("proof_hash") if isinstance(utxo_row, dict) else None,
            "gitpeg_anchor": utxo_row.get("gitpeg_anchor") if isinstance(utxo_row, dict) else None,
        },
        "utxo_auto_consume": utxo_auto_consume,
        "remediation_task": {
            "proof_id": remediation_task.get("proof_id"),
            "issue_id": (remediation_task.get("state_data") or {}).get("issue_id"),
            "status": (remediation_task.get("state_data") or {}).get("status"),
        } if isinstance(remediation_task, dict) else None,
        "gate": gate,
        "gate_soft_override": bool(gate_soft_override_reason),
        "gate_soft_override_reason": gate_soft_override_reason,
        "metering_lookup": gate_pack.get("metering_lookup"),
        "erpnext_notify": erpnext_notify,
    }


@router.get("/stats/{project_id}")
async def project_stats(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    """Inspection stats for a project."""
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    try:
        res = _run_with_retry(
            lambda: sb.table("inspections").select("result").eq("project_id", project_id).execute(),
            retries=1,
        )
        rows = res.data or []
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        rows = []
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        rows = []

    total = len(rows)
    passed = sum(1 for r in rows if r["result"] == "pass")
    warned = sum(1 for r in rows if r["result"] == "warn")
    failed = sum(1 for r in rows if r["result"] == "fail")

    return {
        "total": total,
        "pass": passed,
        "warn": warned,
        "fail": failed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
    }


@router.delete("/{inspection_id}")
async def delete_inspection(
    inspection_id: str,
    sb: Client = Depends(get_supabase),
):
    """Delete inspection."""
    sb.table("inspections").delete().eq("id", inspection_id).execute()
    return {"ok": True}

