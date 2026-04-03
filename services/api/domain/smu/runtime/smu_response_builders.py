"""Response and payload builders for SMU orchestration flows."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    to_float as _to_float,
    to_text as _to_text,
)
from services.api.domain.smu.runtime.smu_state_helpers import canonical_smu_status, legacy_smu_status
from services.api.domain.smu.runtime.smu_trip_helpers import (
    build_quality_payload,
    collect_qc_values,
    resolve_single_value,
)


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def build_genesis_preview_items(preview_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preview_items: list[dict[str, Any]] = []
    for row in preview_rows:
        sd = _as_dict(row.get("state_data"))
        if not bool(sd.get("is_leaf")):
            continue
        preview_items.append(
            {
                "boq_item_uri": _to_text(sd.get("boq_item_uri") or "").strip(),
                "item_no": _to_text(sd.get("item_no") or "").strip(),
                "item_name": _to_text(sd.get("item_name") or "").strip(),
                "unit": _to_text(sd.get("unit") or "").strip(),
                "design_quantity": _to_float(sd.get("design_quantity")),
                "approved_quantity": _to_float(sd.get("approved_quantity")),
                "settled_quantity": 0.0,
            }
        )
    return preview_items


def build_genesis_import_response(
    *,
    upload_file_name: str,
    item_count: int,
    commit: bool,
    boq_root_uri: str,
    norm_context_root_uri: str,
    hierarchy_root_hash: str,
    result: dict[str, Any],
    enrichment_warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "phase": "Genesis Trip",
        "role": {
            "identity_mode": "Role-Trip-Container",
            "executor_role": "SYSTEM",
        },
        "trip": {
            "name": "asset_initialization",
            "source_file": upload_file_name,
            "item_count": item_count,
            "commit": bool(commit),
        },
        "container": {
            "boq_root_uri": boq_root_uri,
            "norm_context_root_uri": norm_context_root_uri,
            "hierarchy_root_hash": hierarchy_root_hash,
        },
        "enrichment_warnings": enrichment_warnings[:20],
        "result": result,
    }


def build_genesis_preview_response(
    *,
    project_uri: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
    total_items: int,
    total_nodes: int,
    leaf_nodes: int,
    hierarchy_root_hash: str,
    preview_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "phase": "Genesis Preview",
        "project_uri": project_uri,
        "boq_root_uri": boq_root_uri,
        "norm_context_root_uri": norm_context_root_uri,
        "total_items": total_items,
        "total_nodes": total_nodes,
        "leaf_nodes": leaf_nodes,
        "hierarchy_root_hash": hierarchy_root_hash,
        "preview_items": preview_items,
    }


def build_governance_context_response(
    *,
    component_type: str,
    row: dict[str, Any],
    sd: dict[str, Any],
    item_no: str,
    item_name: str,
    docpeg_template: dict[str, Any],
    display_metadata: dict[str, Any],
    lab_status: dict[str, Any],
    norm_refs: list[str],
    formula_validation: dict[str, Any],
    spu: dict[str, Any],
    gate_id: str,
    threshold_pack: dict[str, Any],
    threshold_eval: dict[str, Any],
    freeze_state: dict[str, Any],
    gatekeeper: dict[str, Any],
    allowed_roles: list[str],
    container_status: str,
    container_stage: str,
    container_boq_item_uri: str,
    container_smu_id: str,
) -> dict[str, Any]:
    canonical_status = canonical_smu_status(container_status)
    legacy_status = legacy_smu_status(container_status)
    return {
        "ok": True,
        "phase": "Governance & QCGate",
        "role": {
            "executor_role": "CHIEF_ENGINEER",
            "did_gate_required": True,
            "allowed_dto_roles": allowed_roles,
        },
        "trip": {
            "name": "governance_context",
            "input_proof_id": _to_text(row.get("proof_id") or "").strip(),
        },
        "container": {
            "status": canonical_status,
            "status_legacy": legacy_status,
            "stage": container_stage,
            "boq_item_uri": container_boq_item_uri,
            "smu_id": container_smu_id,
        },
        "node": {
            "proof_id": _to_text(row.get("proof_id") or "").strip(),
            "proof_type": _to_text(row.get("proof_type") or "").strip(),
            "result": _to_text(row.get("result") or "").strip(),
            "item_no": item_no,
            "item_name": item_name,
            "unit": _to_text(sd.get("unit") or "").strip(),
            "design_quantity": _to_float(sd.get("design_quantity")),
            "approved_quantity": _to_float(sd.get("approved_quantity")),
            "linked_gate_id": gate_id,
            "linked_spec_uri": _to_text(sd.get("linked_spec_uri") or "").strip(),
            "docpeg_template": docpeg_template,
            "metadata": display_metadata,
            "lab_status": lab_status,
            "norm_refs": norm_refs,
            "formula_validation": formula_validation,
        },
        "spu": spu,
        "threshold": {
            "component_type": component_type,
            **_as_dict(threshold_pack),
            "evaluation": threshold_eval,
        },
        "freeze_state": freeze_state,
        "gatekeeper": gatekeeper,
    }


def build_execute_quality_bundle(
    *,
    project_uri: str,
    input_proof_id: str,
    boq_item_uri: str,
    smu_id: str,
    measurement_data: dict[str, Any],
    formula_validation: dict[str, Any],
    norm_refs: list[str],
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
    executor_did: str,
    evidence_hashes: list[str],
    component_type: str,
    is_contract_trip: bool,
) -> dict[str, Any]:
    snappeg_payload = {
        "project_uri": project_uri,
        "input_proof_id": input_proof_id,
        "boq_item_uri": boq_item_uri,
        "smu_id": smu_id,
        "measurement": measurement_data,
        "formula_validation": formula_validation,
        "norm_refs": norm_refs,
        "geo_location": geo_location,
        "server_timestamp_proof": server_timestamp_proof,
        "executor_did": executor_did,
        "evidence_hashes": evidence_hashes,
    }
    snappeg_hash = _sha(snappeg_payload)
    values_for_qc = collect_qc_values(measurement_data)
    single_value = resolve_single_value(measurement_data)
    formula_status = _to_text(formula_validation.get("status") or "").strip().upper()
    contract_formula_ok = is_contract_trip and formula_status == "PASS"
    quality_payload = build_quality_payload(
        component_type=component_type,
        measurement_data=measurement_data,
        snappeg_hash=snappeg_hash,
        values_for_qc=values_for_qc,
        single_value=single_value,
        contract_formula_ok=contract_formula_ok,
    )
    return {
        "snappeg_hash": snappeg_hash,
        "quality_payload": quality_payload,
        "contract_formula_ok": contract_formula_ok,
    }


def build_execute_trip_response(
    *,
    executor_uri: str,
    executor_did: str,
    executor_role: str,
    item_uri: str,
    smu_id: str,
    force_reject: bool,
    qc: dict[str, Any],
    current: dict[str, Any],
    out_id: str,
    snappeg_hash: str,
    formula_validation: dict[str, Any],
) -> dict[str, Any]:
    canonical_status = canonical_smu_status("Reviewing")
    legacy_status = legacy_smu_status("Reviewing")
    return {
        "ok": True,
        "phase": "Execution & SnapPeg",
        "role": {
            "executor_uri": executor_uri,
            "executor_did": executor_did,
            "executor_role": executor_role,
        },
        "trip": {
            "name": "execution_submit",
            "quality_check_output_proof_id": _to_text(qc.get("output_proof_id") or "").strip(),
            "output_proof_id": out_id,
            "result": _to_text(current.get("result") or "").strip(),
            "snappeg_hash": snappeg_hash,
            "force_reject": bool(force_reject),
        },
        "container": {
            "status": canonical_status,
            "status_legacy": legacy_status,
            "stage": "Execution & SnapPeg",
            "boq_item_uri": item_uri,
            "smu_id": smu_id,
        },
        "formula_validation": formula_validation,
        "raw": current,
    }


def build_sign_approval_response(
    *,
    supervisor_executor_uri: str,
    supervisor_did: str,
    in_id: str,
    out_id: str,
    settle: dict[str, Any],
    lineage_total_hash: str,
    item_uri: str,
    input_smu_id: str,
    docpeg: dict[str, Any],
    sm2_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canonical_status = canonical_smu_status("Approved")
    legacy_status = legacy_smu_status("Approved")
    return {
        "ok": True,
        "phase": "OrdoSign & DID",
        "role": {
            "executor_uri": supervisor_executor_uri,
            "executor_did": supervisor_did,
            "executor_role": "SUPERVISOR",
        },
        "trip": {
            "name": "approval_signature",
            "input_proof_id": in_id,
            "output_proof_id": out_id,
            "result": _to_text(settle.get("result") or "").strip(),
            "total_proof_hash": lineage_total_hash,
        },
        "container": {
            "status": canonical_status,
            "status_legacy": legacy_status,
            "stage": "OrdoSign & DID",
            "boq_item_uri": item_uri,
            "smu_id": input_smu_id,
        },
        "docpeg": docpeg,
        "sm2": _as_dict(sm2_summary),
        "raw": settle,
    }


__all__ = [
    "build_execute_quality_bundle",
    "build_execute_trip_response",
    "build_genesis_import_response",
    "build_genesis_preview_items",
    "build_genesis_preview_response",
    "build_governance_context_response",
    "build_sign_approval_response",
]

