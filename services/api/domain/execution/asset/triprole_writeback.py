"""Gate write-back helpers for TripRole execution."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict,
    as_list,
    sha256_json,
    to_text,
    utc_iso,
)
from services.api.domain.execution.integrations import ProofUTXOEngine
from services.api.domain.execution.lineage.triprole_lineage import _resolve_boq_item_uri
from services.api.domain.utxo.common import normalize_result


def _patch_state_data_fields(*, sb: Any, proof_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    normalized_proof_id = to_text(proof_id).strip()
    if not normalized_proof_id:
        return {}
    engine = ProofUTXOEngine(sb)
    row = engine.get_by_id(normalized_proof_id)
    if not isinstance(row, dict):
        return {}
    state_data = dict(as_dict(row.get("state_data")))
    state_data.update(as_dict(patch))
    try:
        sb.table("proof_utxo").update({"state_data": state_data}).eq("proof_id", normalized_proof_id).execute()
    except Exception:
        return state_data
    return state_data


def update_chain_with_result(*, sb: Any, gate_output: dict[str, Any]) -> dict[str, Any]:
    payload = as_dict(gate_output)
    output_proof_id = to_text(payload.get("output_proof_id") or payload.get("proof_id") or "").strip()
    if not output_proof_id:
        raise HTTPException(400, "update_chain_with_result requires output_proof_id")

    engine = ProofUTXOEngine(sb)
    output_row = engine.get_by_id(output_proof_id)
    if not isinstance(output_row, dict):
        raise HTTPException(404, "output proof_utxo not found")

    state_data = as_dict(output_row.get("state_data"))
    input_proof_id = to_text(payload.get("input_proof_id") or "").strip()
    parent_proof_id = to_text(state_data.get("parent_proof_id") or output_row.get("parent_proof_id") or "").strip()
    if input_proof_id and parent_proof_id and input_proof_id != parent_proof_id:
        raise HTTPException(
            409,
            f"write-back chain mismatch: input={input_proof_id} parent={parent_proof_id}",
        )

    gate_result = dict(as_dict(state_data.get("qc_gate_result")))
    gate_result.update(
        {
            "gate_id": to_text(
                payload.get("gate_id")
                or payload.get("linked_gate_id")
                or gate_result.get("gate_id")
                or state_data.get("linked_gate_id")
                or ""
            ).strip(),
            "linked_gate_id": to_text(
                payload.get("linked_gate_id")
                or gate_result.get("linked_gate_id")
                or state_data.get("linked_gate_id")
                or ""
            ).strip(),
            "linked_gate_ids": as_list(
                payload.get("linked_gate_ids")
                or gate_result.get("linked_gate_ids")
                or state_data.get("linked_gate_ids")
            ),
            "linked_gate_rules": as_list(
                payload.get("linked_gate_rules")
                or gate_result.get("linked_gate_rules")
                or state_data.get("linked_gate_rules")
            ),
            "spec_dict_key": to_text(
                payload.get("spec_dict_key")
                or gate_result.get("spec_dict_key")
                or state_data.get("spec_dict_key")
                or ""
            ).strip(),
            "spec_item": to_text(
                payload.get("spec_item")
                or gate_result.get("spec_item")
                or state_data.get("spec_item")
                or ""
            ).strip(),
            "context_key": to_text(
                payload.get("context_key")
                or gate_result.get("context_key")
                or ""
            ).strip(),
            "result": normalize_result(
                to_text(payload.get("result") or gate_result.get("result") or output_row.get("result") or "PENDING")
            ),
            "result_source": to_text(
                payload.get("result_source")
                or gate_result.get("result_source")
                or state_data.get("result_source")
                or ""
            ).strip(),
            "spec_uri": to_text(
                payload.get("spec_uri")
                or gate_result.get("spec_uri")
                or state_data.get("spec_uri")
                or ""
            ).strip(),
            "spec_snapshot": to_text(
                payload.get("spec_snapshot")
                or gate_result.get("spec_snapshot")
                or state_data.get("spec_snapshot")
                or ""
            ).strip(),
            "quality_hash": to_text(
                payload.get("quality_hash")
                or gate_result.get("quality_hash")
                or state_data.get("quality_hash")
                or ""
            ).strip(),
            "input_proof_id": input_proof_id or parent_proof_id,
            "output_proof_id": output_proof_id,
            "boq_item_uri": to_text(
                payload.get("boq_item_uri")
                or gate_result.get("boq_item_uri")
                or state_data.get("boq_item_uri")
                or _resolve_boq_item_uri(output_row)
            ).strip(),
            "evaluated_at": to_text(
                payload.get("evaluated_at")
                or gate_result.get("evaluated_at")
                or state_data.get("trip_executed_at")
                or output_row.get("created_at")
                or utc_iso()
            ).strip(),
            "write_back_at": utc_iso(),
            "write_back_chain": "same_parent_link",
        }
    )
    gate_result_hash = sha256_json(gate_result)
    history = as_list(state_data.get("qc_gate_history"))
    history.append(
        {
            "output_proof_id": output_proof_id,
            "result": gate_result.get("result"),
            "gate_id": gate_result.get("gate_id"),
            "quality_hash": gate_result.get("quality_hash"),
            "gate_result_hash": gate_result_hash,
            "write_back_at": gate_result.get("write_back_at"),
        }
    )
    if len(history) > 120:
        history = history[-120:]

    patched_state = _patch_state_data_fields(
        sb=sb,
        proof_id=output_proof_id,
        patch={
            "qc_gate_result": gate_result,
            "qc_gate_status": to_text(gate_result.get("result") or "").strip().upper(),
            "qc_gate_result_hash": gate_result_hash,
            "qc_gate_history": history,
            "quality_status_on_chain": to_text(gate_result.get("result") or "").strip().upper(),
        },
    )
    return {
        "ok": True,
        "input_proof_id": input_proof_id or parent_proof_id,
        "output_proof_id": output_proof_id,
        "qc_gate_result_hash": gate_result_hash,
        "state_data": patched_state,
    }


__all__ = [
    "_patch_state_data_fields",
    "update_chain_with_result",
]
