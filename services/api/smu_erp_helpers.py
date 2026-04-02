"""Shared ERP push/receipt helpers for SMU flows."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.erpnext_http_utils import erp_request_sync
from services.api.erpnext_service import load_erpnext_custom
from services.api.smu_primitives import (
    as_dict as _as_dict,
    to_text as _to_text,
    utc_iso as _utc_iso,
)


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _smu_id_from_item_code(item_code: str) -> str:
    token = _to_text(item_code).strip().rstrip("/").split("/")[-1]
    if "-" in token:
        return token.split("-")[0]
    return token


def load_project_for_erpnext(sb: Any, project_id: str, project_uri: str) -> dict[str, Any]:
    if project_id:
        res = (
            sb.table("projects")
            .select("id,enterprise_id,erp_project_code,erp_project_name,name,contract_no,v_uri")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        data = res.data or []
        if data:
            return data[0]
    if project_uri:
        res = (
            sb.table("projects")
            .select("id,enterprise_id,erp_project_code,erp_project_name,name,contract_no,v_uri")
            .eq("v_uri", project_uri)
            .limit(1)
            .execute()
        )
        data = res.data or []
        if data:
            return data[0]
    return {}


def push_docpeg_to_erpnext(
    *,
    sb: Any,
    project_id: str,
    project_uri: str,
    item_no: str,
    item_name: str,
    report_no: str,
    report_url: str,
    docpeg_document: dict[str, Any],
    docpeg_context: dict[str, Any],
    risk_audit: dict[str, Any],
) -> dict[str, Any]:
    proj = load_project_for_erpnext(sb, project_id, project_uri)
    enterprise_id = _to_text(proj.get("enterprise_id") or "").strip()
    if not enterprise_id:
        return {"attempted": False, "success": False, "reason": "enterprise_id_missing"}
    custom = load_erpnext_custom(sb, enterprise_id)
    if not _to_text(custom.get("erpnext_url") or "").strip():
        return {"attempted": False, "success": False, "reason": "erpnext_url_not_configured"}
    path = str(custom.get("erpnext_notify_path") or "").strip() or "/api/method/qcspec_notify"
    payload = {
        "enterprise_id": enterprise_id,
        "project_id": proj.get("id"),
        "project_name": proj.get("name"),
        "erp_project_code": proj.get("erp_project_code"),
        "erp_project_name": proj.get("erp_project_name") or proj.get("name"),
        "contract_no": proj.get("contract_no"),
        "project_uri": proj.get("v_uri") or project_uri,
        "stake": _to_text(docpeg_context.get("stake") or ""),
        "subitem": item_no,
        "subitem_name": item_name,
        "smu_id": _smu_id_from_item_code(item_no),
        "result": "pass",
        "quality_passed": True,
        "metering_action": "docpeg_report",
        "reason": "",
        "docpeg": {
            "report_no": report_no,
            "report_url": report_url,
            "docpeg_document_proof_id": docpeg_document.get("proof_id"),
            "docpeg_document_proof_hash": docpeg_document.get("proof_hash"),
            "artifact_uri": docpeg_context.get("artifact_uri"),
            "verify_uri": docpeg_context.get("verify_uri"),
            "smu_id": _smu_id_from_item_code(item_no),
            "total_proof_hash": risk_audit.get("total_proof_hash"),
            "risk_score": risk_audit.get("risk_score"),
            "risk_issue_count": len(risk_audit.get("issues") or []),
        },
    }
    res = erp_request_sync(custom, method="POST", path=path, body=payload, timeout_s=12.0)
    res["payload"] = payload
    return res


def _erpnext_receipt_proof_id(
    project_uri: str,
    boq_item_uri: str,
    payload: dict[str, Any],
    response: dict[str, Any],
) -> str:
    docpeg = _as_dict(payload.get("docpeg"))
    seed = {
        "project_uri": _to_text(project_uri).strip(),
        "boq_item_uri": _to_text(boq_item_uri).strip(),
        "report_no": _to_text(docpeg.get("report_no") or "").strip(),
        "docpeg_document_proof_id": _to_text(docpeg.get("docpeg_document_proof_id") or "").strip(),
        "docpeg_document_proof_hash": _to_text(docpeg.get("docpeg_document_proof_hash") or "").strip(),
        "success": bool(response.get("success")),
    }
    return f"GP-ERP-{_sha(seed)[:16].upper()}"


def create_erpnext_receipt_proof(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    payload: dict[str, Any],
    response: dict[str, Any],
    source_utxo_id: str = "",
    executor_uri: str = "v://executor/erpnext/system/",
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    b_uri = _to_text(boq_item_uri).strip()
    if not p_uri or not b_uri:
        return {"ok": False, "error": "missing_project_or_boq_uri"}

    proof_id = _erpnext_receipt_proof_id(p_uri, b_uri, payload, response)
    engine = ProofUTXOEngine(sb)
    existing = engine.get_by_id(proof_id)
    if isinstance(existing, dict):
        return {"ok": True, "proof_id": proof_id, "already_exists": True}

    docpeg = _as_dict(payload.get("docpeg"))
    docpeg_proof_id = _to_text(docpeg.get("docpeg_document_proof_id") or "").strip()
    parent_id = docpeg_proof_id or _to_text(source_utxo_id).strip() or None
    result = "PASS" if bool(response.get("success")) else "FAIL"
    state_data = {
        "doc_type": "erpnext_receipt",
        "status": "sent" if result == "PASS" else "failed",
        "project_uri": p_uri,
        "boq_item_uri": b_uri,
        "item_no": _to_text(payload.get("subitem") or "").strip(),
        "item_name": _to_text(payload.get("subitem_name") or "").strip(),
        "report_no": _to_text(docpeg.get("report_no") or "").strip(),
        "report_url": _to_text(docpeg.get("report_url") or "").strip(),
        "verify_uri": _to_text(docpeg.get("verify_uri") or "").strip(),
        "total_proof_hash": _to_text(docpeg.get("total_proof_hash") or "").strip(),
        "risk_score": docpeg.get("risk_score"),
        "risk_issue_count": docpeg.get("risk_issue_count"),
        "docpeg_document_proof_id": docpeg_proof_id,
        "docpeg_document_proof_hash": _to_text(docpeg.get("docpeg_document_proof_hash") or "").strip(),
        "payload": payload,
        "response": response,
        "source_utxo_id": _to_text(source_utxo_id).strip(),
        "created_at": _utc_iso(),
    }
    try:
        engine.create(
            proof_id=proof_id,
            owner_uri=_to_text(executor_uri).strip() or "v://executor/erpnext/system/",
            project_uri=p_uri,
            project_id=_to_text(payload.get("project_id") or "").strip() or None,
            segment_uri=b_uri,
            proof_type="erpnext_receipt",
            result=result,
            state_data=state_data,
            conditions=[],
            parent_proof_id=parent_id,
            norm_uri="v://norm/CoordOS/ERPNext/1.0#receipt",
            signer_uri=_to_text(executor_uri).strip() or "v://executor/erpnext/system/",
            signer_role="ERP",
        )
        return {"ok": True, "proof_id": proof_id, "result": result}
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}


def queue_erpnext_push(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    payload: dict[str, Any],
    response: dict[str, Any],
) -> None:
    try:
        sb.table("erpnext_push_queue").insert(
            {
                "project_uri": project_uri,
                "boq_item_uri": boq_item_uri,
                "payload": payload,
                "response": response,
                "attempts": 1,
                "status": "queued",
            }
        ).execute()
    except Exception:
        pass


def retry_erpnext_push_queue(
    *,
    sb: Any,
    limit: int = 20,
) -> dict[str, Any]:
    try:
        rows = (
            sb.table("erpnext_push_queue")
            .select("*")
            .eq("status", "queued")
            .order("created_at", desc=False)
            .limit(max(1, min(limit, 100)))
            .execute()
            .data
            or []
        )
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}", "attempted": 0, "success": 0}

    attempted = 0
    success = 0
    for row in rows:
        attempted += 1
        payload = _as_dict(row.get("payload"))
        project_uri = _to_text(row.get("project_uri") or "").strip()
        boq_item_uri = _to_text(row.get("boq_item_uri") or "").strip()
        project_id = _to_text(payload.get("project_id") or "").strip()
        proj = load_project_for_erpnext(sb, project_id, project_uri)
        enterprise_id = _to_text(proj.get("enterprise_id") or "").strip()
        if not enterprise_id:
            continue
        custom = load_erpnext_custom(sb, enterprise_id)
        path = str(custom.get("erpnext_notify_path") or "").strip() or "/api/method/qcspec_notify"
        res = erp_request_sync(custom, method="POST", path=path, body=payload, timeout_s=12.0)
        ok = bool(res.get("success"))
        status = "sent" if ok else "queued"
        if ok:
            success += 1
            try:
                create_erpnext_receipt_proof(
                    sb=sb,
                    project_uri=project_uri,
                    boq_item_uri=boq_item_uri,
                    payload=payload,
                    response=res,
                )
            except Exception:
                pass
        try:
            sb.table("erpnext_push_queue").update(
                {
                    "response": res,
                    "attempts": int(row.get("attempts") or 0) + 1,
                    "status": status,
                }
            ).eq("id", row.get("id")).execute()
        except Exception:
            pass

    return {"ok": True, "attempted": attempted, "success": success}


__all__ = [
    "create_erpnext_receipt_proof",
    "load_project_for_erpnext",
    "push_docpeg_to_erpnext",
    "queue_erpnext_push",
    "retry_erpnext_push_queue",
]
