"""Transition-runtime assembly for TripRole standard actions."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    to_text as _to_text,
)


def resolve_triprole_transition_runtime(
    *,
    sb: Any,
    body: Any,
    input_row: dict[str, Any],
    action: str,
    input_proof_id: str,
    executor_uri: str,
    executor_did: str,
    override_result: str,
    offline_packet_id: str,
    payload: dict[str, Any],
    credentials_vc_raw: Any,
    signer_metadata_raw: Any,
    body_geo_location_raw: Any,
    body_server_timestamp_raw: Any,
    segment_uri_override: str,
    boq_item_uri_override: str,
    consensus_required_roles: tuple[str, ...],
    validate_transition_fn: Callable[[str, dict[str, Any]], None],
    build_triprole_action_context_fn: Callable[..., dict[str, Any]],
    materialize_action_context_fn: Callable[..., dict[str, Any]],
    dispatch_triprole_transition_fn: Callable[..., dict[str, Any]],
    materialize_transition_fn: Callable[..., dict[str, Any]],
    aggregate_provenance_chain_fn: Callable[..., dict[str, Any]],
    resolve_dual_pass_gate_fn: Callable[..., dict[str, Any]],
    normalize_consensus_signatures_fn: Callable[[Any], list[dict[str, Any]]],
    validate_consensus_signatures_fn: Callable[..., dict[str, Any]],
    verify_biometric_status_fn: Callable[..., dict[str, Any]],
    detect_consensus_deviation_fn: Callable[..., dict[str, Any]],
    create_consensus_dispute_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    validate_transition_fn(action, input_row)

    action_context = build_triprole_action_context_fn(
        sb=sb,
        input_row=input_row,
        payload=payload,
        action=action,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        executor_did=executor_did,
        credentials_vc_raw=credentials_vc_raw,
        signer_metadata_raw=signer_metadata_raw,
        body_geo_location_raw=body_geo_location_raw,
        body_server_timestamp_raw=body_server_timestamp_raw,
        segment_uri_override=segment_uri_override,
        boq_item_uri_override=boq_item_uri_override,
    )
    runtime_context = materialize_action_context_fn(
        action_context=action_context,
        executor_uri=executor_uri,
        offline_packet_id=offline_packet_id,
    )
    input_sd = _as_dict(runtime_context.get("input_sd"))
    project_uri = _to_text(runtime_context.get("project_uri") or "").strip()
    project_id = runtime_context.get("project_id")
    owner_uri = _to_text(runtime_context.get("owner_uri") or "").strip() or executor_uri
    segment_uri = _to_text(runtime_context.get("segment_uri") or "").strip()
    boq_item_uri = _to_text(runtime_context.get("boq_item_uri") or "").strip()
    did_gate = _as_dict(runtime_context.get("did_gate"))
    gate_binding = _as_dict(runtime_context.get("gate_binding"))
    parent_hash = _to_text(runtime_context.get("parent_hash") or "").strip()
    now_iso = _to_text(runtime_context.get("now_iso") or "").strip()
    anchor = _as_dict(runtime_context.get("anchor"))
    normalized_signer_metadata = _as_dict(runtime_context.get("normalized_signer_metadata"))
    geo_compliance = _as_dict(runtime_context.get("geo_compliance"))
    next_state = dict(_as_dict(runtime_context.get("next_state")))

    transition = dispatch_triprole_transition_fn(
        action=action,
        sb=sb,
        body=body,
        input_row=input_row,
        input_sd=input_sd,
        input_proof_id=input_proof_id,
        payload=payload,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
        segment_uri=segment_uri,
        executor_uri=executor_uri,
        override_result=override_result,
        now_iso=now_iso,
        next_state=next_state,
        geo_compliance=geo_compliance,
        gate_binding=gate_binding,
        signer_metadata_raw=signer_metadata_raw,
        normalized_signer_metadata=normalized_signer_metadata,
        consensus_required_roles=consensus_required_roles,
        aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
        resolve_dual_pass_gate_fn=resolve_dual_pass_gate_fn,
        normalize_consensus_signatures_fn=normalize_consensus_signatures_fn,
        validate_consensus_signatures_fn=validate_consensus_signatures_fn,
        verify_biometric_status_fn=verify_biometric_status_fn,
        detect_consensus_deviation_fn=detect_consensus_deviation_fn,
        create_consensus_dispute_fn=create_consensus_dispute_fn,
    )
    runtime_transition = materialize_transition_fn(
        transition=transition,
        payload=payload,
    )
    next_proof_type = _to_text(runtime_transition.get("next_proof_type") or "inspection").strip() or "inspection"
    next_result = _to_text(runtime_transition.get("next_result") or "PASS").strip().upper() or "PASS"
    tx_type = _to_text(runtime_transition.get("tx_type") or "consume").strip() or "consume"
    next_state = dict(_as_dict(runtime_transition.get("next_state")))
    biometric_check = dict(_as_dict(runtime_transition.get("biometric_check")))

    return {
        "input_sd": input_sd,
        "project_uri": project_uri,
        "project_id": project_id,
        "owner_uri": owner_uri,
        "segment_uri": segment_uri,
        "boq_item_uri": boq_item_uri,
        "did_gate": did_gate,
        "parent_hash": parent_hash,
        "now_iso": now_iso,
        "anchor": anchor,
        "geo_compliance": geo_compliance,
        "next_state": next_state,
        "next_proof_type": next_proof_type,
        "next_result": next_result,
        "tx_type": tx_type,
        "biometric_check": biometric_check,
    }


__all__ = ["resolve_triprole_transition_runtime"]
