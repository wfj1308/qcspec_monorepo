"""Execution-phase helper functions for SMU flow orchestration."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_float as _to_float,
    to_text as _to_text,
)


def _round4(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except Exception:
        return None


def resolve_execute_context(
    *,
    sb: Any,
    project_uri: str,
    input_proof_id: str,
    measurement: dict[str, Any],
    get_proof_by_id: Callable[[Any, str], dict[str, Any] | None],
    smu_id_from_item_code: Callable[[str], str],
    is_smu_frozen: Callable[..., dict[str, Any]],
    resolve_spu_template: Callable[[str, str], dict[str, Any]],
    build_spu_formula_audit: Callable[..., dict[str, Any]],
    resolve_norm_refs: Callable[..., list[str]],
    is_contract_payload: Callable[[str, dict[str, Any]], bool],
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    in_id = _to_text(input_proof_id).strip()
    if not p_uri or not in_id:
        raise HTTPException(400, "project_uri and input_proof_id are required")
    measurement_data = _as_dict(measurement)

    input_row = get_proof_by_id(sb, in_id) or {}
    if not input_row:
        raise HTTPException(404, "input_proof_id not found")
    input_state = _as_dict(input_row.get("state_data"))
    item_uri = _to_text(input_state.get("boq_item_uri") or input_row.get("segment_uri") or "").strip()
    if not item_uri:
        raise HTTPException(409, "input proof has no boq_item_uri")

    item_no = _to_text(input_state.get("item_no") or item_uri.rstrip("/").split("/")[-1]).strip()
    smu_id = smu_id_from_item_code(item_no)
    freeze_state = _as_dict(is_smu_frozen(sb=sb, project_uri=p_uri, smu_id=smu_id))
    if bool(freeze_state.get("frozen")):
        raise HTTPException(409, f"smu_frozen: {smu_id} is immutable")

    item_name = _to_text(input_state.get("item_name") or "").strip()
    spu = resolve_spu_template(item_no, item_name)
    template = {"formula": _as_dict(spu.get("spu_formula"))}
    formula_validation = build_spu_formula_audit(
        template=template,
        measurement=measurement_data,
        design_quantity=_to_float(input_state.get("design_quantity")),
        approved_quantity=_to_float(input_state.get("approved_quantity")),
    )
    norm_refs = resolve_norm_refs(
        item_no,
        item_name,
        template_norm_refs=[str(x).strip() for x in _as_list(spu.get("spu_normpeg_refs")) if str(x).strip()],
    )
    is_contract_trip = is_contract_payload(item_name, measurement_data)
    return {
        "project_uri": p_uri,
        "input_proof_id": in_id,
        "measurement_data": measurement_data,
        "input_row": input_row,
        "item_uri": item_uri,
        "item_no": item_no,
        "item_name": item_name,
        "smu_id": smu_id,
        "spu": spu,
        "formula_validation": formula_validation,
        "norm_refs": norm_refs,
        "is_contract_trip": is_contract_trip,
    }


def enforce_execute_guards(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    measurement_data: dict[str, Any],
    is_contract_trip: bool,
    resolve_lab_pass_for_sample: Callable[..., dict[str, Any]],
    resolve_dual_pass_gate: Callable[..., dict[str, Any]],
    resolve_boq_balance: Callable[..., dict[str, float]],
    verify_conservation: Callable[..., dict[str, Any]],
) -> None:
    if not is_contract_trip:
        sample_id = _to_text(measurement_data.get("sample_id") or measurement_data.get("utxo_identifier") or "").strip()
        if sample_id:
            lab_sample_gate = _as_dict(
                resolve_lab_pass_for_sample(
                    sb=sb,
                    project_uri=project_uri,
                    boq_item_uri=boq_item_uri,
                    sample_id=sample_id,
                )
            )
            if not bool(lab_sample_gate.get("pass")):
                raise HTTPException(409, "evidence_chain_incomplete: missing lab PASS proof for sample_id")
        lab_gate = _as_dict(resolve_dual_pass_gate(sb=sb, project_uri=project_uri, boq_item_uri=boq_item_uri))
        if not bool(lab_gate.get("lab_pass_count")):
            raise HTTPException(409, "evidence_chain_incomplete: missing lab PASS proof")

    claim_qty = _round4(_to_float(measurement_data.get("claim_quantity"))) or 0.0
    if claim_qty <= 0:
        return
    balance = _as_dict(resolve_boq_balance(sb=sb, project_uri=project_uri, boq_item_uri=boq_item_uri))
    baseline = float(balance.get("baseline") or 0.0)
    settled = float(balance.get("settled") or 0.0)
    conservation = _as_dict(verify_conservation(baseline=baseline, settled=settled, claim=claim_qty))
    if bool(conservation.get("ok")):
        return
    required_delta = max(0.0, (settled + claim_qty) - baseline)
    gap_ratio = float(conservation.get("gap_ratio") or 0.0)
    raise HTTPException(
        409,
        f"deviation_warning: gap_ratio={gap_ratio:.4f}, require variation trip (delta>= {required_delta:.6f})",
    )


def build_execute_state_patch(
    *,
    item_uri: str,
    smu_id: str,
    measurement_data: dict[str, Any],
    formula_validation: dict[str, Any],
    norm_refs: list[str],
    snappeg_hash: str,
    evidence_hashes: list[str],
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
    executor_did: str,
    captured_at: str,
) -> dict[str, Any]:
    return {
        "snappeg": {
            "hash": snappeg_hash,
            "evidence_hashes": evidence_hashes,
            "geo_location": geo_location,
            "server_timestamp_proof": server_timestamp_proof,
            "executor_did": executor_did,
            "captured_at": captured_at,
        },
        "container": {
            "status": "Reviewing",
            "stage": "Execution & SnapPeg",
            "boq_item_uri": item_uri,
            "smu_id": smu_id,
        },
        "trip": {
            "phase": "Execution & SnapPeg",
            "measurement": measurement_data,
        },
        "formula_validation": formula_validation,
        "norm_refs": norm_refs,
    }


__all__ = [
    "build_execute_state_patch",
    "enforce_execute_guards",
    "resolve_execute_context",
]

