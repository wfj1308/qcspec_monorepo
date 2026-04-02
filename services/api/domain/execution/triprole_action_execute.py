"""Top-level TripRole action execution orchestrator."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    to_text as _to_text,
)


def execute_triprole_action_flow(
    *,
    sb: Any,
    body: Any,
    valid_actions: set[str],
    consensus_required_roles: tuple[str, ...],
    parse_triprole_action_request_fn: Callable[..., dict[str, Any]],
    materialize_parsed_request_fn: Callable[..., dict[str, Any]],
    prepare_triprole_action_input_fn: Callable[..., dict[str, Any]],
    resolve_existing_offline_result_fn: Callable[..., dict[str, Any] | None],
    build_triprole_replayed_response_fn: Callable[..., dict[str, Any]],
    is_leaf_boq_row_fn: Callable[[dict[str, Any]], bool],
    proof_utxo_engine_cls: Callable[[Any], Any],
    maybe_execute_special_action_fn: Callable[..., dict[str, Any] | None],
    execute_scan_entry_action_fn: Callable[..., dict[str, Any]],
    execute_gateway_style_action_fn: Callable[..., dict[str, Any]],
    resolve_triprole_transition_runtime_fn: Callable[..., dict[str, Any]],
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
    finalize_triprole_action_fn: Callable[..., dict[str, Any]],
    consume_triprole_transition_fn: Callable[..., dict[str, Any]],
    materialize_execution_io_fn: Callable[..., dict[str, Any]],
    run_triprole_postprocess_fn: Callable[..., dict[str, Any]],
    materialize_postprocess_fn: Callable[..., dict[str, Any]],
    build_triprole_action_response_fn: Callable[..., dict[str, Any]],
    update_chain_with_result_fn: Callable[..., dict[str, Any]],
    open_remediation_trip_fn: Callable[..., dict[str, Any]],
    calculate_sovereign_credit_fn: Callable[..., dict[str, Any]],
    sync_to_mirrors_fn: Callable[..., dict[str, Any]],
    build_shadow_packet_fn: Callable[..., dict[str, Any]],
    patch_state_data_fields_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    parsed_request = parse_triprole_action_request_fn(body=body, valid_actions=valid_actions)
    runtime_request = materialize_parsed_request_fn(parsed_request=parsed_request)
    action = _to_text(runtime_request.get("action") or "").strip()
    input_proof_id = _to_text(runtime_request.get("input_proof_id") or "").strip()
    executor_uri = _to_text(runtime_request.get("executor_uri") or "").strip()
    executor_role = _to_text(runtime_request.get("executor_role") or "").strip() or "TRIPROLE"
    executor_did = _to_text(runtime_request.get("executor_did") or "").strip()
    override_result = _to_text(runtime_request.get("override_result") or "").strip()
    offline_packet_id = _to_text(runtime_request.get("offline_packet_id") or "").strip()
    payload = _as_dict(runtime_request.get("payload"))
    credentials_vc_raw = runtime_request.get("credentials_vc_raw")
    signer_metadata_raw = runtime_request.get("signer_metadata_raw")
    body_geo_location_raw = runtime_request.get("body_geo_location_raw")
    body_server_timestamp_raw = runtime_request.get("body_server_timestamp_raw")
    boq_item_uri_override = _to_text(runtime_request.get("boq_item_uri_override") or "").strip()
    segment_uri_override = _to_text(runtime_request.get("segment_uri_override") or "").strip()

    prepared_input = prepare_triprole_action_input_fn(
        sb=sb,
        action=action,
        input_proof_id=input_proof_id,
        offline_packet_id=offline_packet_id,
        resolve_existing_offline_result_fn=resolve_existing_offline_result_fn,
        build_triprole_replayed_response_fn=build_triprole_replayed_response_fn,
        is_leaf_boq_row_fn=is_leaf_boq_row_fn,
        proof_utxo_engine_cls=proof_utxo_engine_cls,
    )
    replayed_response = prepared_input.get("replayed_response")
    if replayed_response is not None:
        return _as_dict(replayed_response)
    engine = prepared_input.get("engine")
    input_row = _as_dict(prepared_input.get("input_row"))

    maybe_special_result = maybe_execute_special_action_fn(
        action=action,
        sb=sb,
        engine=engine,
        input_row=input_row,
        payload=payload,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        executor_role=executor_role,
        executor_did=executor_did,
        credentials_vc_raw=credentials_vc_raw,
        segment_uri_override=segment_uri_override,
        boq_item_uri_override=boq_item_uri_override,
        body_geo_location_raw=body_geo_location_raw,
        body_server_timestamp_raw=body_server_timestamp_raw,
        execute_scan_entry_action_fn=execute_scan_entry_action_fn,
        execute_gateway_style_action_fn=execute_gateway_style_action_fn,
    )
    if maybe_special_result is not None:
        return maybe_special_result

    transition_runtime = resolve_triprole_transition_runtime_fn(
        sb=sb,
        body=body,
        input_row=input_row,
        action=action,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        executor_did=executor_did,
        override_result=override_result,
        offline_packet_id=offline_packet_id,
        payload=payload,
        credentials_vc_raw=credentials_vc_raw,
        signer_metadata_raw=signer_metadata_raw,
        body_geo_location_raw=body_geo_location_raw,
        body_server_timestamp_raw=body_server_timestamp_raw,
        segment_uri_override=segment_uri_override,
        boq_item_uri_override=boq_item_uri_override,
        consensus_required_roles=consensus_required_roles,
        validate_transition_fn=validate_transition_fn,
        build_triprole_action_context_fn=build_triprole_action_context_fn,
        materialize_action_context_fn=materialize_action_context_fn,
        dispatch_triprole_transition_fn=dispatch_triprole_transition_fn,
        materialize_transition_fn=materialize_transition_fn,
        aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
        resolve_dual_pass_gate_fn=resolve_dual_pass_gate_fn,
        normalize_consensus_signatures_fn=normalize_consensus_signatures_fn,
        validate_consensus_signatures_fn=validate_consensus_signatures_fn,
        verify_biometric_status_fn=verify_biometric_status_fn,
        detect_consensus_deviation_fn=detect_consensus_deviation_fn,
        create_consensus_dispute_fn=create_consensus_dispute_fn,
    )
    input_sd = _as_dict(transition_runtime.get("input_sd"))
    project_uri = _to_text(transition_runtime.get("project_uri") or "").strip()
    project_id = transition_runtime.get("project_id")
    owner_uri = _to_text(transition_runtime.get("owner_uri") or "").strip() or executor_uri
    segment_uri = _to_text(transition_runtime.get("segment_uri") or "").strip()
    boq_item_uri = _to_text(transition_runtime.get("boq_item_uri") or "").strip()
    did_gate = _as_dict(transition_runtime.get("did_gate"))
    parent_hash = _to_text(transition_runtime.get("parent_hash") or "").strip()
    now_iso = _to_text(transition_runtime.get("now_iso") or "").strip()
    anchor = _as_dict(transition_runtime.get("anchor"))
    geo_compliance = _as_dict(transition_runtime.get("geo_compliance"))
    next_state = dict(_as_dict(transition_runtime.get("next_state")))
    next_proof_type = _to_text(transition_runtime.get("next_proof_type") or "inspection").strip() or "inspection"
    next_result = _to_text(transition_runtime.get("next_result") or "PASS").strip().upper() or "PASS"
    tx_type = _to_text(transition_runtime.get("tx_type") or "consume").strip() or "consume"
    biometric_check = dict(_as_dict(transition_runtime.get("biometric_check")))

    return finalize_triprole_action_fn(
        sb=sb,
        engine=engine,
        input_row=input_row,
        input_sd=input_sd,
        input_proof_id=input_proof_id,
        action=action,
        payload=payload,
        executor_uri=executor_uri,
        executor_role=executor_role,
        executor_did=executor_did,
        offline_packet_id=offline_packet_id,
        owner_uri=owner_uri,
        project_id=project_id,
        project_uri=project_uri,
        segment_uri=segment_uri,
        boq_item_uri=boq_item_uri,
        parent_hash=parent_hash,
        now_iso=now_iso,
        did_gate=did_gate,
        anchor=anchor,
        geo_compliance=geo_compliance,
        next_proof_type=next_proof_type,
        next_result=next_result,
        tx_type=tx_type,
        next_state=next_state,
        biometric_check=biometric_check,
        consume_triprole_transition_fn=consume_triprole_transition_fn,
        materialize_execution_io_fn=materialize_execution_io_fn,
        run_triprole_postprocess_fn=run_triprole_postprocess_fn,
        materialize_postprocess_fn=materialize_postprocess_fn,
        aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
        build_triprole_action_response_fn=build_triprole_action_response_fn,
        update_chain_with_result_fn=update_chain_with_result_fn,
        open_remediation_trip_fn=open_remediation_trip_fn,
        calculate_sovereign_credit_fn=calculate_sovereign_credit_fn,
        sync_to_mirrors_fn=sync_to_mirrors_fn,
        build_shadow_packet_fn=build_shadow_packet_fn,
        patch_state_data_fields_fn=patch_state_data_fields_fn,
    )


__all__ = ["execute_triprole_action_flow"]
