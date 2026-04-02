"""Signing-phase helper functions for SMU flow orchestration."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)


def resolve_sign_context(
    *,
    sb: Any,
    input_proof_id: str,
    boq_item_uri: str,
    template_path: str,
    get_proof_by_id: Callable[[Any, str], dict[str, Any] | None],
    smu_id_from_item_code: Callable[[str], str],
    is_smu_frozen: Callable[..., dict[str, Any]],
    resolve_docpeg_template: Callable[[str, str], dict[str, Any]],
    utc_iso: Callable[[], str],
) -> dict[str, Any]:
    in_id = _to_text(input_proof_id).strip()
    item_uri = _to_text(boq_item_uri).strip()
    if not in_id or not item_uri:
        raise HTTPException(400, "input_proof_id and boq_item_uri are required")

    now = _to_text(utc_iso() or "").strip()
    input_row = get_proof_by_id(sb, in_id) or {}
    input_sd = _as_dict(_as_dict(input_row).get("state_data"))
    input_item_no = _to_text(input_sd.get("item_no") or item_uri.rstrip("/").split("/")[-1]).strip()
    input_smu_id = smu_id_from_item_code(input_item_no)
    project_uri_for_freeze = _to_text(_as_dict(input_row).get("project_uri") or "").strip()
    if project_uri_for_freeze and input_smu_id:
        freeze_state = _as_dict(is_smu_frozen(sb=sb, project_uri=project_uri_for_freeze, smu_id=input_smu_id))
        if bool(freeze_state.get("frozen")):
            raise HTTPException(409, f"smu_frozen: {input_smu_id} is immutable")

    input_item_name = _to_text(input_sd.get("item_name") or "").strip()
    template_binding = _as_dict(input_sd.get("docpeg_template"))
    if not template_binding:
        template_binding = _as_dict(resolve_docpeg_template(input_item_no, input_item_name))
    auto_template_path = _to_text(template_binding.get("template_path") or "").strip()
    selected_template_path = _to_text(template_path).strip() or auto_template_path
    return {
        "input_proof_id": in_id,
        "boq_item_uri": item_uri,
        "now": now,
        "input_row": input_row,
        "input_item_no": input_item_no,
        "input_item_name": input_item_name,
        "input_smu_id": input_smu_id,
        "template_binding": template_binding,
        "selected_template_path": selected_template_path,
    }


def build_sign_output_patch(
    *,
    item_uri: str,
    input_smu_id: str,
    lineage_total_hash: str,
    docpeg_document: dict[str, Any],
    risk_audit: dict[str, Any],
    erpnext_push: dict[str, Any],
    erpnext_receipt: dict[str, Any],
) -> dict[str, Any]:
    return {
        "container": {
            "status": "Approved",
            "stage": "OrdoSign & DID",
            "boq_item_uri": item_uri,
            "smu_id": input_smu_id,
        },
        "trip": {
            "phase": "OrdoSign & DID",
            "consensus": "complete",
        },
        "total_proof_hash": lineage_total_hash,
        "docpeg_document": docpeg_document or {},
        "risk_audit": risk_audit or {},
        "erpnext_push": erpnext_push or {},
        "erpnext_receipt": erpnext_receipt or {},
        "smu_id": input_smu_id,
    }


def normalize_sign_context(sign_ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "in_id": _to_text(sign_ctx.get("input_proof_id") or "").strip(),
        "item_uri": _to_text(sign_ctx.get("boq_item_uri") or "").strip(),
        "now": _to_text(sign_ctx.get("now") or "").strip(),
        "input_row": _as_dict(sign_ctx.get("input_row")),
        "input_item_no": _to_text(sign_ctx.get("input_item_no") or "").strip(),
        "input_item_name": _to_text(sign_ctx.get("input_item_name") or "").strip(),
        "input_smu_id": _to_text(sign_ctx.get("input_smu_id") or "").strip(),
        "template_binding": _as_dict(sign_ctx.get("template_binding")),
        "selected_template_path": _to_text(sign_ctx.get("selected_template_path") or "").strip(),
    }


def normalize_sign_inputs(sign_inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "signatures": _as_list(sign_inputs.get("signatures")),
        "biometric": _as_dict(sign_inputs.get("biometric")),
        "payload": _as_dict(sign_inputs.get("approval_payload")),
    }


def normalize_docpeg_bundle(docpeg_bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "docpeg": _as_dict(docpeg_bundle.get("docpeg")),
        "docpeg_document": _as_dict(docpeg_bundle.get("docpeg_document")),
        "risk_audit": _as_dict(docpeg_bundle.get("risk_audit")),
        "erpnext_push": _as_dict(docpeg_bundle.get("erpnext_push")),
        "erpnext_receipt": _as_dict(docpeg_bundle.get("erpnext_receipt")),
    }


def resolve_sign_docpeg_bundle(
    *,
    auto_docpeg: bool,
    settle_result: str,
    run_auto_docpeg_after_sign: Any,
    sb: Any,
    item_uri: str,
    in_id: str,
    out_id: str,
    input_row: dict[str, Any],
    input_item_no: str,
    input_item_name: str,
    input_smu_id: str,
    template_binding: dict[str, Any],
    selected_template_path: str,
    verify_base_url: str,
    supervisor_executor_uri: str,
    push_docpeg_to_erpnext: Any,
    create_erpnext_receipt_proof: Any,
    queue_erpnext_push: Any,
) -> dict[str, Any]:
    if (not auto_docpeg) or _to_text(settle_result).strip().upper() != "PASS":
        return {}
    return _as_dict(
        run_auto_docpeg_after_sign(
            sb=sb,
            item_uri=item_uri,
            in_id=in_id,
            out_id=out_id,
            input_row=input_row,
            input_item_no=input_item_no,
            input_item_name=input_item_name,
            input_smu_id=input_smu_id,
            template_binding=template_binding,
            selected_template_path=selected_template_path,
            verify_base_url=verify_base_url,
            supervisor_executor_uri=supervisor_executor_uri,
            push_docpeg_to_erpnext=push_docpeg_to_erpnext,
            create_erpnext_receipt_proof=create_erpnext_receipt_proof,
            queue_erpnext_push=queue_erpnext_push,
        )
    )


__all__ = [
    "build_sign_output_patch",
    "normalize_docpeg_bundle",
    "normalize_sign_context",
    "normalize_sign_inputs",
    "resolve_sign_docpeg_bundle",
    "resolve_sign_context",
]

