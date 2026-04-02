"""Runtime materialization helpers for TripRole action execution."""

from __future__ import annotations

from typing import Any

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    to_text as _to_text,
)
from services.api.domain.utxo.common import normalize_result as _normalize_result


def materialize_action_context(
    *,
    action_context: dict[str, Any],
    executor_uri: str,
    offline_packet_id: str,
) -> dict[str, Any]:
    input_sd = _as_dict(action_context.get("input_sd"))
    project_uri = _to_text(action_context.get("project_uri") or "").strip()
    project_id = action_context.get("project_id")
    owner_uri = _to_text(action_context.get("owner_uri") or "").strip() or executor_uri
    segment_uri = _to_text(action_context.get("segment_uri") or "").strip()
    boq_item_uri = _to_text(action_context.get("boq_item_uri") or "").strip()
    did_gate = _as_dict(action_context.get("did_gate"))
    gate_binding = _as_dict(action_context.get("gate_binding"))
    parent_hash = _to_text(action_context.get("parent_hash") or "").strip()
    now_iso = _to_text(action_context.get("now_iso") or "").strip()
    anchor = _as_dict(action_context.get("anchor"))
    normalized_signer_metadata = _as_dict(action_context.get("normalized_signer_metadata"))
    geo_compliance = _as_dict(action_context.get("geo_compliance"))

    next_state: dict[str, Any] = dict(_as_dict(action_context.get("next_state")))
    next_state["offline_packet_id"] = offline_packet_id

    return {
        "input_sd": input_sd,
        "project_uri": project_uri,
        "project_id": project_id,
        "owner_uri": owner_uri,
        "segment_uri": segment_uri,
        "boq_item_uri": boq_item_uri,
        "did_gate": did_gate,
        "gate_binding": gate_binding,
        "parent_hash": parent_hash,
        "now_iso": now_iso,
        "anchor": anchor,
        "normalized_signer_metadata": normalized_signer_metadata,
        "geo_compliance": geo_compliance,
        "next_state": next_state,
    }


def materialize_transition(
    *,
    transition: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    next_proof_type = _to_text(transition.get("next_proof_type") or "inspection").strip() or "inspection"
    next_result = _normalize_result(_to_text(transition.get("next_result") or payload.get("result") or "PASS"))
    tx_type = _to_text(transition.get("tx_type") or "consume").strip() or "consume"
    next_state = dict(_as_dict(transition.get("next_state")))
    biometric_check = dict(_as_dict(transition.get("biometric_check")))

    return {
        "next_proof_type": next_proof_type,
        "next_result": next_result,
        "tx_type": tx_type,
        "next_state": next_state,
        "biometric_check": biometric_check,
    }


def materialize_parsed_request(
    *,
    parsed_request: dict[str, Any],
) -> dict[str, Any]:
    action = _to_text(parsed_request.get("action") or "").strip()
    input_proof_id = _to_text(parsed_request.get("input_proof_id") or "").strip()
    executor_uri = _to_text(parsed_request.get("executor_uri") or "").strip()
    executor_role = _to_text(parsed_request.get("executor_role") or "").strip() or "TRIPROLE"
    executor_did = _to_text(parsed_request.get("executor_did") or "").strip()
    override_result = _to_text(parsed_request.get("override_result") or "").strip()
    offline_packet_id = _to_text(parsed_request.get("offline_packet_id") or "").strip()
    payload = _as_dict(parsed_request.get("payload"))
    credentials_vc_raw = parsed_request.get("credentials_vc_raw")
    signer_metadata_raw = parsed_request.get("signer_metadata_raw")
    body_geo_location_raw = parsed_request.get("body_geo_location_raw")
    body_server_timestamp_raw = parsed_request.get("body_server_timestamp_raw")
    boq_item_uri_override = _to_text(parsed_request.get("boq_item_uri_override") or "").strip()
    segment_uri_override = _to_text(parsed_request.get("segment_uri_override") or "").strip()

    return {
        "action": action,
        "input_proof_id": input_proof_id,
        "executor_uri": executor_uri,
        "executor_role": executor_role,
        "executor_did": executor_did,
        "override_result": override_result,
        "offline_packet_id": offline_packet_id,
        "payload": payload,
        "credentials_vc_raw": credentials_vc_raw,
        "signer_metadata_raw": signer_metadata_raw,
        "body_geo_location_raw": body_geo_location_raw,
        "body_server_timestamp_raw": body_server_timestamp_raw,
        "boq_item_uri_override": boq_item_uri_override,
        "segment_uri_override": segment_uri_override,
    }


def materialize_execution_io(*, execution_io: dict[str, Any]) -> dict[str, Any]:
    return {
        "tx": _as_dict(execution_io.get("tx")),
        "output_proof_id": _to_text(execution_io.get("output_proof_id") or "").strip(),
        "output_row": _as_dict(execution_io.get("output_row")),
    }


def materialize_postprocess(*, postprocess: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_row": _as_dict(postprocess.get("output_row")),
        "quality_chain_writeback": _as_dict(postprocess.get("quality_chain_writeback")),
        "remediation": _as_dict(postprocess.get("remediation")),
        "credit_endorsement": _as_dict(postprocess.get("credit_endorsement")),
        "mirror_sync": _as_dict(postprocess.get("mirror_sync")),
    }


__all__ = [
    "materialize_action_context",
    "materialize_execution_io",
    "materialize_parsed_request",
    "materialize_postprocess",
    "materialize_transition",
]
