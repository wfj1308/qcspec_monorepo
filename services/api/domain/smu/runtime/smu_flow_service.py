"""
SMU lifecycle orchestration service.

Six-stage flow:
1) Genesis Trip (BOQ import -> hierarchical UTXO)
2) Governance & QCGate (dynamic form + threshold context)
3) Execution & SnapPeg (TripRole execution + evidence fingerprint)
4) OrdoSign & DID (multi-party sovereign sign)
5) DocPeg Execution (approved trigger -> report bundle context)
6) SMU Risk Audit & Freeze (validate_logic + freeze proof)
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.boq.integrations import (
    build_did_reputation_summary,
    build_unit_merkle_snapshot,
    resolve_dynamic_threshold,
)
from services.api.domain.execution.integrations import resolve_dual_pass_gate
from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.domain.execution.flows import (
    get_boq_realtime_status,
)
from services.api.domain.boqpeg.integrations import parse_boq_upload
from services.api.domain.smu.runtime.smu_docpeg_helpers import run_auto_docpeg_after_sign
from services.api.domain.smu.runtime.smu_evidence_helpers import (
    resolve_boq_balance as _resolve_boq_balance,
    resolve_lab_pass_for_sample as _resolve_lab_pass_for_sample,
    resolve_lab_status as _resolve_lab_status,
    verify_conservation,
)
from services.api.domain.smu.runtime.smu_execute_helpers import (
    build_execute_state_patch as _build_execute_state_patch,
    enforce_execute_guards as _enforce_execute_guards,
    resolve_execute_context as _resolve_execute_context,
)
from services.api.domain.smu.runtime.smu_genesis_helpers import (
    enrich_genesis_preview_rows as _enrich_genesis_preview_rows,
    initialize_genesis_chain as _initialize_genesis_chain,
    persist_genesis_created_enrichment as _persist_genesis_created_enrichment,
    resolve_genesis_roots as _resolve_genesis_roots,
)
from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_float as _to_float,
    to_text as _to_text,
    utc_iso as _utc_iso,
)
from services.api.domain.smu.runtime.smu_erp_helpers import (
    create_erpnext_receipt_proof as _create_erpnext_receipt_proof,
    push_docpeg_to_erpnext as _push_docpeg_to_erpnext,
    queue_erpnext_push as _queue_erpnext_push,
    retry_erpnext_push_queue as _retry_erpnext_push_queue,
)
from services.api.domain.smu.runtime.smu_freeze_helpers import (
    build_freeze_payloads_from_context as _build_freeze_payloads_from_context,
    build_freeze_proof_create_payload as _build_freeze_proof_create_payload,
    build_freeze_response,
    resolve_freeze_context as _resolve_freeze_context,
)
from services.api.domain.smu.runtime.smu_governance_helpers import (
    build_gatekeeper,
    container_status_from_stage,
    derive_display_metadata,
    eval_threshold,
)
from services.api.domain.smu.runtime.smu_governance_context_helpers import (
    build_governance_context_response_from_payload as _build_governance_context_response_from_payload,
    resolve_governance_payload as _resolve_governance_payload_impl,
)
from services.api.domain.smu.runtime.smu_rules import (
    _build_spu_formula_audit,
    _is_contract_payload,
    _resolve_allowed_roles,
    _resolve_docpeg_template,
    _resolve_norm_refs,
    _resolve_spu_template,
    list_spu_template_library,
)
from services.api.domain.specir.runtime.registry import ensure_specir_object
from services.api.domain.specir.runtime.spu_schema import build_spu_ultimate_content
from services.api.domain.smu.runtime.smu_state_helpers import (
    collect_smu_qualification as _collect_smu_qualification,
    is_smu_frozen as _is_smu_frozen,
    mark_smu_scope_immutable as _mark_smu_scope_immutable,
    smu_id_from_item_code as _smu_id_from_item_code,
)
from services.api.domain.smu.runtime.smu_storage_helpers import (
    boq_rows as _boq_rows,
    latest_unspent_leaf as _latest_unspent_leaf,
    patch_state_data as _patch_state_data,
)
from services.api.domain.smu.runtime.smu_response_builders import (
    build_execute_quality_bundle as _build_execute_quality_bundle,
    build_execute_trip_response as _build_execute_trip_response,
    build_genesis_import_response as _build_genesis_import_response,
    build_genesis_preview_items as _build_genesis_preview_items,
    build_genesis_preview_response as _build_genesis_preview_response,
    build_governance_context_response as _build_governance_context_response,
    build_sign_approval_response as _build_sign_approval_response,
)
from services.api.domain.smu.runtime.smu_sign_helpers import (
    normalize_docpeg_bundle as _normalize_docpeg_bundle,
    normalize_sign_context as _normalize_sign_context,
    normalize_sign_inputs as _normalize_sign_inputs,
    resolve_sign_docpeg_bundle as _resolve_sign_docpeg_bundle,
    build_sign_output_patch as _build_sign_output_patch,
    resolve_sign_context as _resolve_sign_context,
)
from services.api.domain.smu.runtime.smu_trip_helpers import (
    build_sign_inputs,
    run_execute_actions as _run_execute_actions,
    run_settlement_confirm,
)
from services.api.domain.smu.runtime.smu_validation_helpers import (
    resolve_validate_logic as _resolve_validate_logic,
)


def _build_genesis_enrichment_patch(
    *,
    sb: Any,
    code: str,
    name: str,
    sd: dict[str, Any],
    upload_file_name: str,
    owner_uri: str,
) -> dict[str, Any]:
    spu = _resolve_spu_template(code, name)
    template = {"formula": _as_dict(spu.get("spu_formula"))}
    norm_refs = _resolve_norm_refs(
        code,
        name,
        template_norm_refs=[str(x).strip() for x in _as_list(spu.get("spu_normpeg_refs")) if str(x).strip()],
    )
    design_qty = _to_float(sd.get("design_quantity"))
    approved_qty = _to_float(sd.get("approved_quantity"))
    formula_audit = _build_spu_formula_audit(
        template=template,
        measurement={},
        design_quantity=design_qty,
        approved_quantity=approved_qty,
    )
    docpeg_template = _resolve_docpeg_template(code, name)
    ref_spu_uri = _to_text(spu.get("ref_spu_uri") or "").strip()
    ref_quota_uri = _to_text(spu.get("ref_quota_uri") or "").strip()
    ref_meter_rule_uri = _to_text(spu.get("ref_meter_rule_uri") or "").strip()
    quantity_unit = _to_text(_as_dict(spu.get("spu_formula")).get("quantity_unit") or "").strip()
    try:
        if ref_spu_uri:
            ensure_specir_object(
                sb=sb,
                uri=ref_spu_uri,
                kind="spu",
                title=_to_text(spu.get("spu_label") or name or code).strip(),
                content=build_spu_ultimate_content(
                    spu_uri=ref_spu_uri,
                    title=_to_text(spu.get("spu_label") or name or code).strip(),
                    content={
                        "industry": "Highway",
                        "standard_codes": _as_list(spu.get("spu_normpeg_refs")),
                        "unit": quantity_unit,
                        "measure_statement": "Auto-registered from SMU genesis context; refine in SpecIR editor.",
                        "measure_operator": _to_text(_as_dict(spu.get("spu_formula")).get("formula_key") or "smu-auto-register").strip(),
                        "measure_expression": _to_text(_as_dict(spu.get("spu_formula")).get("expression") or "approved_quantity").strip(),
                        "quota_ref": ref_quota_uri,
                        "meter_rule_ref": ref_meter_rule_uri,
                        "gate_refs": [],
                        "extensions": {
                            "template_id": _to_text(spu.get("spu_template_id") or "").strip(),
                            "library_uri": _to_text(spu.get("spu_library_uri") or "").strip(),
                            "contexts": _as_list(spu.get("spu_contexts")),
                        },
                    },
                ),
                metadata={"source": "smu.genesis", "item_code": code},
            )
        if ref_quota_uri:
            ensure_specir_object(
                sb=sb,
                uri=ref_quota_uri,
                kind="quota",
                title=f"Quota {code}",
                content={"spu_ref": ref_spu_uri, "item_code": code},
                metadata={"source": "smu.genesis"},
            )
        if ref_meter_rule_uri:
            ensure_specir_object(
                sb=sb,
                uri=ref_meter_rule_uri,
                kind="meter_rule",
                title=f"Meter Rule {code}",
                content={
                    "spu_ref": ref_spu_uri,
                    "quantity_unit": quantity_unit,
                },
                metadata={"source": "smu.genesis"},
            )
    except Exception:
        pass
    return {
        "spu_template_id": _to_text(spu.get("spu_template_id") or "").strip(),
        "spu_label": _to_text(spu.get("spu_label") or "").strip(),
        "spu_library_uri": _to_text(spu.get("spu_library_uri") or "").strip(),
        "spu_contexts": _as_list(spu.get("spu_contexts")),
        "match_hints": _as_list(spu.get("match_hints")),
        "ref_spu_uri": ref_spu_uri,
        "ref_quota_uri": ref_quota_uri,
        "ref_meter_rule_uri": ref_meter_rule_uri,
        "formula_validation": formula_audit,
        "norm_refs": norm_refs,
        "docpeg_template": docpeg_template,
        "genesis_amount": approved_qty or design_qty,
        "container": {
            "status": "Unspent",
            "stage": "Genesis Trip",
            "smu_id": _smu_id_from_item_code(code),
        },
        "trip": {
            "phase": "Genesis Trip",
            "source_file": upload_file_name,
            "formula_validation": formula_audit,
        },
        "role": {
            "identity_mode": "Role-Trip-Container",
            "owner_uri": owner_uri,
        },
        "metadata": {
            "unit_project": _to_text(sd.get("division") or "").strip(),
            "subdivision_project": _to_text(sd.get("subdivision") or "").strip(),
            "wbs_path": _to_text(_as_dict(sd.get("hierarchy")).get("wbs_path") or "").strip(),
        },
    }


def retry_erpnext_push_queue(
    *,
    sb: Any,
    limit: int = 20,
) -> dict[str, Any]:
    return _retry_erpnext_push_queue(sb=sb, limit=limit)


def _emit_progress(
    progress_hook: Callable[[str, int, str], None] | None,
    stage: str,
    percent: int,
    message: str,
) -> None:
    if progress_hook:
        progress_hook(stage, percent, message)


def _prepare_genesis_input(
    *,
    project_uri: str,
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str,
    norm_context_root_uri: str,
) -> tuple[list[Any], str, str]:
    items = parse_boq_upload(upload_file_name, upload_content)
    root_uri, norm_root = _resolve_genesis_roots(
        project_uri=project_uri,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
    )
    return items, root_uri, norm_root


def import_genesis_trip(
    *,
    sb: Any,
    project_uri: str,
    project_id: str = "",
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str = "",
    norm_context_root_uri: str = "",
    owner_uri: str = "",
    bridge_mappings: dict[str, Any] | None = None,
    commit: bool = True,
    progress_hook: Callable[[str, int, str], None] | None = None,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    _emit_progress(progress_hook, "parsing", 12, "解析上传文件")
    items, root_uri, norm_root = _prepare_genesis_input(
        project_uri=p_uri,
        upload_file_name=upload_file_name,
        upload_content=upload_content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
    )
    _emit_progress(progress_hook, "parsed", 22, f"解析完成：识别细目 {len(items)} 条")
    _emit_progress(progress_hook, "writing_chain", 38, "初始化主权树并写链")
    result = _initialize_genesis_chain(
        sb=sb,
        project_uri=p_uri,
        project_id=project_id,
        boq_items=items,
        root_uri=root_uri,
        norm_root=norm_root,
        owner_uri=owner_uri,
        upload_file_name=upload_file_name,
        bridge_mappings=bridge_mappings,
        commit=bool(commit),
    )
    total_nodes = int(result.get("total_nodes") or 0)
    _emit_progress(progress_hook, "chain_written", 78, f"写链完成：节点 {total_nodes}")

    _emit_progress(progress_hook, "enriching_preview", 84, "补充 SPU 与模板绑定")
    effective_owner_uri = _to_text(result.get("owner_uri") or "").strip()
    _enrich_genesis_preview_rows(
        sb=sb,
        result=result,
        upload_file_name=upload_file_name,
        owner_uri=effective_owner_uri,
        build_genesis_enrichment_patch=_build_genesis_enrichment_patch,
    )

    enrichment_warnings: list[dict[str, Any]] = []
    if bool(commit):
        enrichment_warnings = _persist_genesis_created_enrichment(
            sb=sb,
            result=result,
            upload_file_name=upload_file_name,
            owner_uri=effective_owner_uri,
            build_genesis_enrichment_patch=_build_genesis_enrichment_patch,
            patch_state_data=_patch_state_data,
        )
        _emit_progress(progress_hook, "enriched", 96, "后处理完成")

    _emit_progress(progress_hook, "finalizing", 99, "正在整理导入结果")

    return _build_genesis_import_response(
        upload_file_name=upload_file_name,
        item_count=len(items),
        commit=bool(commit),
        boq_root_uri=root_uri,
        norm_context_root_uri=norm_root,
        hierarchy_root_hash=_to_text(result.get("hierarchy_root_hash") or "").strip(),
        result=result,
        enrichment_warnings=enrichment_warnings,
    )


def preview_genesis_tree(
    *,
    sb: Any,
    project_uri: str,
    project_id: str = "",
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str = "",
    norm_context_root_uri: str = "",
    owner_uri: str = "",
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    items, root_uri, norm_root = _prepare_genesis_input(
        project_uri=p_uri,
        upload_file_name=upload_file_name,
        upload_content=upload_content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
    )
    result = _initialize_genesis_chain(
        sb=sb,
        project_uri=p_uri,
        project_id=project_id,
        boq_items=items,
        root_uri=root_uri,
        norm_root=norm_root,
        owner_uri=owner_uri,
        upload_file_name=upload_file_name,
        commit=False,
    )
    preview_items = _build_genesis_preview_items(_as_list(result.get("preview")))
    return _build_genesis_preview_response(
        project_uri=p_uri,
        boq_root_uri=root_uri,
        norm_context_root_uri=norm_root,
        total_items=len(items),
        total_nodes=int(result.get("total_nodes") or 0),
        leaf_nodes=int(result.get("leaf_nodes") or 0),
        hierarchy_root_hash=_to_text(result.get("hierarchy_root_hash") or "").strip(),
        preview_items=preview_items,
    )


def _resolve_governance_payload(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    component_type: str,
    measured_value: float | None,
) -> dict[str, Any]:
    payload = _resolve_governance_payload_impl(
        sb=sb,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
        component_type=component_type,
        measured_value=measured_value,
        latest_unspent_leaf=_latest_unspent_leaf,
        resolve_spu_template=_resolve_spu_template,
        resolve_norm_refs=_resolve_norm_refs,
        build_spu_formula_audit=_build_spu_formula_audit,
        resolve_allowed_roles=_resolve_allowed_roles,
        resolve_docpeg_template=_resolve_docpeg_template,
        resolve_dynamic_threshold=resolve_dynamic_threshold,
        eval_threshold=eval_threshold,
        container_status_from_stage=container_status_from_stage,
        smu_id_from_item_code=_smu_id_from_item_code,
        is_smu_frozen=_is_smu_frozen,
        derive_display_metadata=derive_display_metadata,
        resolve_lab_status=_resolve_lab_status,
        resolve_dual_pass_gate=resolve_dual_pass_gate,
        build_gatekeeper=build_gatekeeper,
    )
    if not payload:
        raise HTTPException(404, "No unspent UTXO found for boq_item_uri")
    return payload


def get_governance_context(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    component_type: str = "generic",
    measured_value: float | None = None,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    b_uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not p_uri or not b_uri:
        raise HTTPException(400, "project_uri and boq_item_uri are required")
    payload = _resolve_governance_payload(
        sb=sb,
        project_uri=p_uri,
        boq_item_uri=b_uri,
        component_type=component_type,
        measured_value=measured_value,
    )
    return _build_governance_context_response_from_payload(
        payload=payload,
        boq_item_uri=b_uri,
        component_type=component_type,
        smu_id_from_item_code=_smu_id_from_item_code,
        build_governance_context_response=_build_governance_context_response,
    )


def execute_smu_trip(
    *,
    sb: Any,
    project_uri: str,
    input_proof_id: str,
    executor_uri: str,
    executor_did: str,
    executor_role: str,
    component_type: str,
    measurement: dict[str, Any],
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
    evidence_hashes: list[str],
    credentials_vc: list[dict[str, Any]],
    force_reject: bool = False,
) -> dict[str, Any]:
    exec_ctx = _resolve_execute_context(
        sb=sb,
        project_uri=project_uri,
        input_proof_id=input_proof_id,
        measurement=measurement,
        get_proof_by_id=lambda client, proof_id: ProofUTXOEngine(client).get_by_id(proof_id),
        smu_id_from_item_code=_smu_id_from_item_code,
        is_smu_frozen=_is_smu_frozen,
        resolve_spu_template=_resolve_spu_template,
        build_spu_formula_audit=_build_spu_formula_audit,
        resolve_norm_refs=_resolve_norm_refs,
        is_contract_payload=_is_contract_payload,
    )
    p_uri = _to_text(exec_ctx.get("project_uri") or "").strip()
    in_id = _to_text(exec_ctx.get("input_proof_id") or "").strip()
    measurement_data = _as_dict(exec_ctx.get("measurement_data"))
    item_uri = _to_text(exec_ctx.get("item_uri") or "").strip()
    smu_id = _to_text(exec_ctx.get("smu_id") or "").strip()
    formula_validation = _as_dict(exec_ctx.get("formula_validation"))
    norm_refs = [str(x).strip() for x in _as_list(exec_ctx.get("norm_refs")) if str(x).strip()]
    is_contract_trip = bool(exec_ctx.get("is_contract_trip"))

    _enforce_execute_guards(
        sb=sb,
        project_uri=p_uri,
        boq_item_uri=item_uri,
        measurement_data=measurement_data,
        is_contract_trip=is_contract_trip,
        resolve_lab_pass_for_sample=_resolve_lab_pass_for_sample,
        resolve_dual_pass_gate=resolve_dual_pass_gate,
        resolve_boq_balance=lambda **kwargs: _resolve_boq_balance(
            get_boq_realtime_status=get_boq_realtime_status,
            **kwargs,
        ),
        verify_conservation=verify_conservation,
    )

    execute_bundle = _build_execute_quality_bundle(
        project_uri=p_uri,
        input_proof_id=in_id,
        boq_item_uri=item_uri,
        smu_id=smu_id,
        measurement_data=measurement_data,
        formula_validation=formula_validation,
        norm_refs=norm_refs,
        geo_location=geo_location,
        server_timestamp_proof=server_timestamp_proof,
        executor_did=executor_did,
        evidence_hashes=evidence_hashes,
        component_type=component_type,
        is_contract_trip=is_contract_trip,
    )
    snappeg_hash = _to_text(execute_bundle.get("snappeg_hash") or "").strip()
    quality_payload = _as_dict(execute_bundle.get("quality_payload"))
    contract_formula_ok = bool(execute_bundle.get("contract_formula_ok"))

    qc, current = _run_execute_actions(
        sb=sb,
        in_id=in_id,
        item_uri=item_uri,
        executor_uri=executor_uri,
        executor_did=executor_did,
        executor_role=executor_role,
        force_reject=force_reject,
        force_pass=contract_formula_ok,
        quality_payload=quality_payload,
        credentials_vc=credentials_vc,
        geo_location=geo_location,
        server_timestamp_proof=server_timestamp_proof,
        component_type=component_type,
        measurement_data=measurement_data,
        snappeg_hash=snappeg_hash,
    )
    out_id = _to_text(current.get("output_proof_id") or "").strip()
    if out_id:
        patch = _build_execute_state_patch(
            item_uri=item_uri,
            smu_id=smu_id,
            measurement_data=measurement_data,
            formula_validation=formula_validation,
            norm_refs=norm_refs,
            snappeg_hash=snappeg_hash,
            evidence_hashes=evidence_hashes,
            geo_location=geo_location,
            server_timestamp_proof=server_timestamp_proof,
            executor_did=executor_did,
            captured_at=_utc_iso(),
        )
        patched_state = _patch_state_data(sb, out_id, patch) or {}
        if patched_state:
            current["state_data"] = patched_state

    return _build_execute_trip_response(
        executor_uri=executor_uri,
        executor_did=executor_did,
        executor_role=executor_role,
        item_uri=item_uri,
        smu_id=smu_id,
        force_reject=force_reject,
        qc=qc,
        current=current,
        out_id=out_id,
        snappeg_hash=snappeg_hash,
        formula_validation=formula_validation,
    )


def sign_smu_approval(
    *,
    sb: Any,
    input_proof_id: str,
    boq_item_uri: str,
    supervisor_executor_uri: str,
    supervisor_did: str,
    contractor_did: str,
    owner_did: str,
    signer_metadata: dict[str, Any],
    consensus_values: list[dict[str, Any]] | None = None,
    allowed_deviation: float | None = None,
    allowed_deviation_percent: float | None = None,
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
    auto_docpeg: bool = True,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: str = "",
) -> dict[str, Any]:
    sign_ctx = _resolve_sign_context(
        sb=sb,
        input_proof_id=input_proof_id,
        boq_item_uri=boq_item_uri,
        template_path=template_path,
        get_proof_by_id=lambda client, proof_id: ProofUTXOEngine(client).get_by_id(proof_id),
        smu_id_from_item_code=_smu_id_from_item_code,
        is_smu_frozen=_is_smu_frozen,
        resolve_docpeg_template=_resolve_docpeg_template,
        utc_iso=_utc_iso,
    )
    sign_values = _normalize_sign_context(sign_ctx)
    in_id = _to_text(sign_values.get("in_id") or "").strip()
    item_uri = _to_text(sign_values.get("item_uri") or "").strip()
    now = _to_text(sign_values.get("now") or "").strip()
    input_row = _as_dict(sign_values.get("input_row"))
    input_item_no = _to_text(sign_values.get("input_item_no") or "").strip()
    input_item_name = _to_text(sign_values.get("input_item_name") or "").strip()
    input_smu_id = _to_text(sign_values.get("input_smu_id") or "").strip()
    template_binding = _as_dict(sign_values.get("template_binding"))
    selected_template_path = _to_text(sign_values.get("selected_template_path") or "").strip()

    sign_inputs = build_sign_inputs(
        in_id=in_id,
        now_iso=now,
        contractor_did=contractor_did,
        supervisor_did=supervisor_did,
        owner_did=owner_did,
        signer_metadata=signer_metadata,
        consensus_values=consensus_values,
        allowed_deviation=allowed_deviation,
        allowed_deviation_percent=allowed_deviation_percent,
    )
    sign_inputs_values = _normalize_sign_inputs(_as_dict(sign_inputs))
    signatures = _as_list(sign_inputs_values.get("signatures"))
    biometric = _as_dict(sign_inputs_values.get("biometric"))
    payload = _as_dict(sign_inputs_values.get("payload"))
    sm2_summary = {
        "required": bool(biometric.get("sm2_required")),
        "attached_roles": [
            _to_text(sig.get("role") or "").strip()
            for sig in signatures
            if _to_text(sig.get("sm2_verify_mode") or "").strip() not in {"", "not_provided"}
        ],
        "verified_roles": [
            _to_text(sig.get("role") or "").strip()
            for sig in signatures
            if bool(sig.get("sm2_verified"))
        ],
        "verify_modes": {
            _to_text(sig.get("role") or "").strip(): _to_text(sig.get("sm2_verify_mode") or "").strip()
            for sig in signatures
        },
    }

    settle = run_settlement_confirm(
        sb=sb,
        in_id=in_id,
        item_uri=item_uri,
        supervisor_executor_uri=supervisor_executor_uri,
        supervisor_did=supervisor_did,
        signatures=signatures,
        signer_metadata=biometric,
        payload=payload,
        geo_location=geo_location,
        server_timestamp_proof=server_timestamp_proof,
    )
    out_id = _to_text(settle.get("output_proof_id") or "").strip()
    lineage_total_hash = _to_text(_as_dict(settle.get("provenance")).get("total_proof_hash") or "").strip()

    settle_result = _to_text(settle.get("result") or "").strip()
    docpeg_bundle = _resolve_sign_docpeg_bundle(
        auto_docpeg=auto_docpeg,
        settle_result=settle_result,
        run_auto_docpeg_after_sign=run_auto_docpeg_after_sign,
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
        push_docpeg_to_erpnext=_push_docpeg_to_erpnext,
        create_erpnext_receipt_proof=_create_erpnext_receipt_proof,
        queue_erpnext_push=_queue_erpnext_push,
    )
    docpeg_values = _normalize_docpeg_bundle(_as_dict(docpeg_bundle))
    docpeg = _as_dict(docpeg_values.get("docpeg"))
    docpeg_document = _as_dict(docpeg_values.get("docpeg_document"))
    risk_audit = _as_dict(docpeg_values.get("risk_audit"))
    erpnext_push = _as_dict(docpeg_values.get("erpnext_push"))
    erpnext_receipt = _as_dict(docpeg_values.get("erpnext_receipt"))

    if out_id:
        sign_patch = _build_sign_output_patch(
            item_uri=item_uri,
            input_smu_id=input_smu_id,
            lineage_total_hash=lineage_total_hash,
            docpeg_document=docpeg_document,
            risk_audit=risk_audit,
            erpnext_push=erpnext_push,
            erpnext_receipt=erpnext_receipt,
        )
        _patch_state_data(sb, out_id, sign_patch)

    return _build_sign_approval_response(
        supervisor_executor_uri=supervisor_executor_uri,
        supervisor_did=supervisor_did,
        in_id=in_id,
        out_id=out_id,
        settle=settle,
        lineage_total_hash=lineage_total_hash,
        item_uri=item_uri,
        input_smu_id=input_smu_id,
        docpeg=docpeg,
        sm2_summary=sm2_summary,
    )


def validate_logic(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
) -> dict[str, Any]:
    return _resolve_validate_logic(
        sb=sb,
        project_uri=project_uri,
        smu_id=smu_id,
        boq_rows=_boq_rows,
        build_did_reputation_summary=build_did_reputation_summary,
        collect_smu_qualification=lambda **kwargs: _collect_smu_qualification(
            get_boq_realtime_status=get_boq_realtime_status,
            **kwargs,
        ),
    )


def freeze_smu(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
    executor_uri: str,
    min_risk_score: float = 60.0,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    s_id = _to_text(smu_id).strip()
    if not p_uri or not s_id:
        raise HTTPException(400, "project_uri and smu_id are required")
    freeze_ctx = _resolve_freeze_context(
        sb=sb,
        project_uri=p_uri,
        smu_id=s_id,
        min_risk_score=min_risk_score,
        is_smu_frozen=_is_smu_frozen,
        validate_logic=validate_logic,
        build_unit_merkle_snapshot=build_unit_merkle_snapshot,
    )
    freeze_values = _build_freeze_payloads_from_context(
        freeze_ctx=_as_dict(freeze_ctx),
        project_uri=p_uri,
        smu_id=s_id,
        executor_uri=executor_uri,
    )
    audit = _as_dict(freeze_values.get("audit"))
    risk_score = _to_float(freeze_values.get("risk_score")) or 0.0
    merkle = _as_dict(freeze_values.get("merkle"))
    total_proof_hash = _to_text(freeze_values.get("total_proof_hash") or "").strip()
    status = _to_text(freeze_values.get("status") or "").strip().upper() or "FAIL"
    freeze_proof_id = _to_text(freeze_values.get("freeze_proof_id") or "").strip()
    state_data = _as_dict(freeze_values.get("state_data"))
    create_payload = _build_freeze_proof_create_payload(
        executor_uri=executor_uri,
        project_uri=p_uri,
        smu_id=s_id,
        freeze_proof_id=freeze_proof_id,
        status=status,
        state_data=state_data,
    )
    row = ProofUTXOEngine(sb).create(**create_payload)
    immutable_result = {"touched": 0, "skipped": 0}
    if status == "PASS":
        immutable_result = _mark_smu_scope_immutable(
            sb=sb,
            project_uri=p_uri,
            smu_id=s_id,
            freeze_proof_id=freeze_proof_id,
            total_proof_hash=total_proof_hash,
            boq_rows=_boq_rows,
            utc_iso=_utc_iso,
        )
    return build_freeze_response(
        executor_uri=executor_uri,
        status=status,
        risk_score=risk_score,
        min_risk_score=min_risk_score,
        smu_id=s_id,
        row=_as_dict(row),
        total_proof_hash=total_proof_hash,
        audit=audit,
        immutable_result=immutable_result,
        merkle=merkle,
        state_data=state_data,
    )




