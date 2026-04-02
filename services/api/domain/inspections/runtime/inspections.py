"""
Inspection business service helpers.
services/api/inspections_service.py
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
import hashlib
import httpx
from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client
from services.api.domain.erpnext.runtime.service import (
    evaluate_erpnext_gate_for_inspection,
    load_erpnext_custom,
    notify_erpnext_for_inspection,
)
from services.api.domain.inspections.runtime.create_utils import (
    build_inspection_create_response as _build_inspection_create_response,
    compute_spec_eval_pack as _compute_spec_eval_pack,
    load_evidence_from_photos as _load_evidence_from_photos,
)
from services.api.domain.inspections.runtime.utils import (
    gen_proof as _gen_proof,
    guess_owner_uri as _guess_owner_uri,
    is_uuid,
    run_with_retry,
    to_utxo_result as _to_utxo_result,
    utxo_anchor_config as _utxo_anchor_config,
    utxo_auto_consume_enabled as _utxo_auto_consume_enabled,
)
from services.api.domain.utxo.integrations import ProofUTXOEngine
async def list_inspections_flow(
    *,
    project_id: str,
    result: Optional[str],
    kind: Optional[str],
    limit: int,
    offset: int,
    sb: Client,
) -> dict[str, Any]:
    if not is_uuid(project_id):
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
        if kind:
            q = q.eq("type", kind)
        return q.execute()
    try:
        res = run_with_retry(_query, retries=1)
        rows = res.data or []
        return {"data": rows, "count": len(rows)}
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        raise HTTPException(502, "Failed to query inspections from database.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        return {"data": [], "count": 0}
async def create_inspection_flow(
    *,
    body: Any,
    sb: Client,
) -> dict[str, Any]:
    if not is_uuid(body.project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")
    try:
        proj = run_with_retry(
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
        raise HTTPException(502, "Database temporarily unavailable. Please retry.")
    if not proj.data:
        raise HTTPException(404, "Project not found")
    proj_uri = proj.data["v_uri"]
    ent_id = proj.data["enterprise_id"]
    custom = load_erpnext_custom(sb, ent_id)
    spec_eval = _compute_spec_eval_pack(body=body, sb=sb)
    values_for_eval = spec_eval["values_for_eval"]
    spec_uri = spec_eval["spec_uri"]
    spec_rule = spec_eval["spec_rule"]
    rule_operator = spec_eval["rule_operator"]
    rule_threshold = spec_eval["rule_threshold"]
    rule_tolerance = spec_eval["rule_tolerance"]
    eval_result = spec_eval["eval_result"]
    final_result = spec_eval["final_result"]
    result_source = spec_eval["result_source"]
    measured_value = spec_eval["measured_value"]
    standard_value = spec_eval["standard_value"]
    effective_spec_uri = spec_eval["effective_spec_uri"]
    spec_snapshot = spec_eval["spec_snapshot"]
    spec_meta = spec_eval["spec_meta"]
    rule_threshold_text = spec_eval["rule_threshold_text"]
    evidence_list, evidence_hashes, evidence_proof_ids, photo_ids = _load_evidence_from_photos(
        sb=sb,
        project_id=body.project_id,
        photo_ids_raw=body.photo_ids,
    )
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
        ins = run_with_retry(lambda: sb.table("inspections").insert(rec).execute(), retries=1)
    except APIError:
        raise HTTPException(502, "Failed to write inspection.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(502, "Database temporarily unavailable. Please retry.")
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
        run_with_retry(
            lambda: sb.table("inspections")
            .update({"proof_id": proof_id, "proof_status": "confirmed"})
            .eq("id", insp["id"])
            .execute(),
            retries=1,
        )
    except Exception:
        pass
    try:
        run_with_retry(
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
        pass
    linked_photo_count = 0
    if photo_ids:
        try:
            linked = run_with_retry(
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
    return _build_inspection_create_response(
        insp=insp,
        v_uri=v_uri,
        proof_id=proof_id,
        final_result=final_result,
        result_source=result_source,
        measured_value=measured_value,
        body=body,
        values_for_eval=values_for_eval,
        spec_rule=spec_rule,
        spec_uri=spec_uri,
        rule_operator=rule_operator,
        rule_threshold=rule_threshold,
        rule_tolerance=rule_tolerance,
        eval_result=eval_result,
        spec_snapshot=spec_snapshot,
        remediation_task=remediation_task,
        evidence_list=evidence_list,
        linked_photo_count=linked_photo_count,
        utxo_row=utxo_row,
        utxo_auto_consume=utxo_auto_consume,
        gate=gate,
        gate_soft_override_reason=gate_soft_override_reason,
        gate_pack=gate_pack,
        erpnext_notify=erpnext_notify,
    )
async def project_stats_flow(
    *,
    project_id: str,
    sb: Client,
) -> dict[str, Any]:
    if not is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")
    try:
        res = run_with_retry(
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
async def delete_inspection_flow(
    *,
    inspection_id: str,
    sb: Client,
) -> dict[str, Any]:
    sb.table("inspections").delete().eq("id", inspection_id).execute()
    return {"ok": True}
