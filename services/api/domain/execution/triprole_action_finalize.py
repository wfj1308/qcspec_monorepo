"""Finalization pipeline for standard TripRole action execution."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    to_text as _to_text,
)


def finalize_triprole_action(
    *,
    sb: Any,
    engine: Any,
    input_row: dict[str, Any],
    input_sd: dict[str, Any],
    input_proof_id: str,
    action: str,
    payload: dict[str, Any],
    executor_uri: str,
    executor_role: str,
    executor_did: str,
    offline_packet_id: str,
    owner_uri: str,
    project_id: Any,
    project_uri: str,
    segment_uri: str,
    boq_item_uri: str,
    parent_hash: str,
    now_iso: str,
    did_gate: dict[str, Any],
    anchor: dict[str, Any],
    geo_compliance: dict[str, Any],
    next_proof_type: str,
    next_result: str,
    tx_type: str,
    next_state: dict[str, Any],
    biometric_check: dict[str, Any],
    consume_triprole_transition_fn: Callable[..., dict[str, Any]],
    materialize_execution_io_fn: Callable[..., dict[str, Any]],
    run_triprole_postprocess_fn: Callable[..., dict[str, Any]],
    materialize_postprocess_fn: Callable[..., dict[str, Any]],
    aggregate_provenance_chain_fn: Callable[[str, Any], dict[str, Any]],
    build_triprole_action_response_fn: Callable[..., dict[str, Any]],
    update_chain_with_result_fn: Callable[..., dict[str, Any]],
    open_remediation_trip_fn: Callable[..., dict[str, Any]],
    calculate_sovereign_credit_fn: Callable[..., dict[str, Any]],
    sync_to_mirrors_fn: Callable[..., dict[str, Any]],
    build_shadow_packet_fn: Callable[..., dict[str, Any]],
    patch_state_data_fields_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    execution_io = consume_triprole_transition_fn(
        engine=engine,
        input_row=input_row,
        input_sd=input_sd,
        input_proof_id=input_proof_id,
        owner_uri=owner_uri,
        project_id=project_id,
        project_uri=project_uri,
        segment_uri=segment_uri,
        next_proof_type=next_proof_type,
        next_result=next_result,
        next_state=next_state,
        executor_uri=executor_uri,
        executor_role=executor_role,
        action=action,
        boq_item_uri=boq_item_uri,
        executor_did=executor_did,
        did_gate=did_gate,
        anchor=anchor,
        geo_compliance=geo_compliance,
        biometric_check=biometric_check,
        offline_packet_id=offline_packet_id,
        tx_type=tx_type,
    )
    runtime_execution = materialize_execution_io_fn(execution_io=execution_io)
    tx = _as_dict(runtime_execution.get("tx"))
    output_proof_id = _to_text(runtime_execution.get("output_proof_id") or "").strip()
    output_row = _as_dict(runtime_execution.get("output_row"))
    postprocess = run_triprole_postprocess_fn(
        sb=sb,
        action=action,
        payload=payload,
        output_proof_id=output_proof_id,
        output_row=_as_dict(output_row),
        next_state=next_state,
        input_proof_id=input_proof_id,
        next_result=next_result,
        boq_item_uri=boq_item_uri,
        now_iso=now_iso,
        executor_uri=executor_uri,
        project_uri=project_uri,
        executor_did=executor_did,
        did_gate=did_gate,
        tx=tx,
        update_chain_with_result_fn=update_chain_with_result_fn,
        open_remediation_trip_fn=open_remediation_trip_fn,
        calculate_sovereign_credit_fn=calculate_sovereign_credit_fn,
        sync_to_mirrors_fn=sync_to_mirrors_fn,
        build_shadow_packet_fn=build_shadow_packet_fn,
        patch_state_data_fields_fn=patch_state_data_fields_fn,
    )
    runtime_postprocess = materialize_postprocess_fn(postprocess=postprocess)
    output_row = _as_dict(runtime_postprocess.get("output_row"))
    quality_chain_writeback = _as_dict(runtime_postprocess.get("quality_chain_writeback"))
    remediation = _as_dict(runtime_postprocess.get("remediation"))
    credit_endorsement = _as_dict(runtime_postprocess.get("credit_endorsement"))
    mirror_sync = _as_dict(runtime_postprocess.get("mirror_sync"))

    agg_after = aggregate_provenance_chain_fn(output_proof_id, sb)
    return build_triprole_action_response_fn(
        action=action,
        input_proof_id=input_proof_id,
        output_proof_id=output_proof_id,
        parent_hash=parent_hash,
        output_row=output_row,
        did_gate=did_gate,
        credit_endorsement=credit_endorsement,
        mirror_sync=mirror_sync,
        quality_chain_writeback=quality_chain_writeback,
        remediation=remediation,
        offline_packet_id=offline_packet_id,
        tx=tx,
        provenance=agg_after,
    )


__all__ = ["finalize_triprole_action"]
