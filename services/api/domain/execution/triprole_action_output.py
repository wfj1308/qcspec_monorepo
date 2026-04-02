"""Execution I/O helpers for TripRole action orchestration."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_float as _to_float,
    to_text as _to_text,
)
from services.api.domain.execution.triprole_lineage import _resolve_boq_item_uri


def consume_triprole_transition(
    *,
    engine: Any,
    input_row: dict[str, Any],
    input_sd: dict[str, Any],
    input_proof_id: str,
    owner_uri: str,
    project_id: Any,
    project_uri: str,
    segment_uri: str,
    next_proof_type: str,
    next_result: str,
    next_state: dict[str, Any],
    executor_uri: str,
    executor_role: str,
    action: str,
    boq_item_uri: str,
    executor_did: str,
    did_gate: dict[str, Any],
    anchor: dict[str, Any],
    geo_compliance: dict[str, Any],
    biometric_check: dict[str, Any],
    offline_packet_id: str,
    tx_type: str,
) -> dict[str, Any]:
    tx = engine.consume(
        input_proof_ids=[input_proof_id],
        output_states=[
            {
                "owner_uri": owner_uri,
                "project_id": project_id,
                "project_uri": project_uri,
                "segment_uri": segment_uri,
                "proof_type": next_proof_type,
                "result": next_result,
                "state_data": next_state,
                "conditions": _as_list(input_row.get("conditions")),
                "parent_proof_id": input_proof_id,
                "norm_uri": _to_text(input_row.get("norm_uri") or input_sd.get("norm_uri") or None) or None,
            }
        ],
        executor_uri=executor_uri,
        executor_role=executor_role,
        trigger_action=f"TripRole({action})",
        trigger_data={
            "action": action,
            "input_proof_id": input_proof_id,
            "boq_item_uri": boq_item_uri,
            "executor_did": executor_did,
            "did_gate_hash": _to_text(did_gate.get("did_gate_hash") or "").strip(),
            "required_credential": _to_text(did_gate.get("required_credential") or "").strip(),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "geo_compliance_trust_level": _to_text(geo_compliance.get("trust_level") or "").strip(),
            "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
            "biometric_metadata_hash": _to_text(biometric_check.get("metadata_hash") or "").strip(),
            "offline_packet_id": offline_packet_id,
        },
        tx_type=tx_type,
    )

    output_ids = [_to_text(x).strip() for x in _as_list(tx.get("output_proofs")) if _to_text(x).strip()]
    if not output_ids:
        raise HTTPException(500, "triprole execution produced no outputs")

    output_proof_id = output_ids[0]
    output_row = engine.get_by_id(output_proof_id)
    if not output_row:
        raise HTTPException(500, "output proof_utxo not found after execution")
    return {
        "tx": tx,
        "output_proof_id": output_proof_id,
        "output_row": output_row,
    }


def build_triprole_action_response(
    *,
    action: str,
    input_proof_id: str,
    output_proof_id: str,
    parent_hash: str,
    output_row: dict[str, Any],
    did_gate: dict[str, Any],
    credit_endorsement: dict[str, Any],
    mirror_sync: dict[str, Any],
    quality_chain_writeback: dict[str, Any],
    remediation: dict[str, Any],
    offline_packet_id: str,
    tx: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    state_data = _as_dict(output_row.get("state_data"))
    return {
        "ok": True,
        "action": action,
        "input_proof_id": input_proof_id,
        "output_proof_id": output_proof_id,
        "parent_hash": parent_hash,
        "proof_hash": _to_text(output_row.get("proof_hash") or "").strip(),
        "proof_type": _to_text(output_row.get("proof_type") or "").strip(),
        "result": _to_text(output_row.get("result") or "").strip(),
        "segment_uri": _to_text(output_row.get("segment_uri") or "").strip(),
        "boq_item_uri": _resolve_boq_item_uri(output_row),
        "did_gate": did_gate,
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "quality_chain_writeback": quality_chain_writeback,
        "remediation": remediation,
        "spatiotemporal_anchor_hash": _to_text(state_data.get("spatiotemporal_anchor_hash") or "").strip(),
        "geo_compliance": _as_dict(state_data.get("geo_compliance")),
        "biometric_verification": _as_dict(state_data.get("biometric_verification")),
        "offline_packet_id": offline_packet_id,
        "available_balance": _to_float(_as_dict(output_row.get("state_data")).get("available_quantity")),
        "artifact_uri": _to_text(state_data.get("artifact_uri") or "").strip(),
        "gitpeg_anchor": _to_text(output_row.get("gitpeg_anchor") or "").strip(),
        "tx": tx,
        "provenance": provenance,
    }


__all__ = [
    "consume_triprole_transition",
    "build_triprole_action_response",
]
