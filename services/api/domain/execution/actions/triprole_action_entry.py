"""TripRole action entry wiring for execute_triprole_action."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.integrations import (
    ProofUTXOEngine,
    calculate_sovereign_credit,
    open_remediation_trip,
    resolve_dual_pass_gate,
    sync_to_mirrors,
)
from services.api.domain.execution.actions.triprole_action_context import (
    build_triprole_action_context as _build_triprole_action_context,
)
from services.api.domain.execution.actions.triprole_action_dispatch import (
    dispatch_triprole_transition as _dispatch_triprole_transition,
)
from services.api.domain.execution.actions.triprole_action_execute import (
    execute_triprole_action_flow as _execute_triprole_action_flow,
)
from services.api.domain.execution.actions.triprole_action_finalize import (
    finalize_triprole_action as _finalize_triprole_action,
)
from services.api.domain.execution.actions.triprole_action_input import (
    prepare_triprole_action_input as _prepare_triprole_action_input,
)
from services.api.domain.execution.actions.triprole_action_output import (
    build_triprole_action_response as _build_triprole_action_response,
    consume_triprole_transition as _consume_triprole_transition,
)
from services.api.domain.execution.actions.triprole_action_postprocess import (
    run_triprole_postprocess as _run_triprole_postprocess,
)
from services.api.domain.execution.actions.triprole_action_request import (
    build_triprole_replayed_response as _build_triprole_replayed_response,
    parse_triprole_action_request as _parse_triprole_action_request,
)
from services.api.domain.execution.actions.triprole_action_runtime import (
    materialize_action_context as _materialize_action_context,
    materialize_execution_io as _materialize_execution_io,
    materialize_parsed_request as _materialize_parsed_request,
    materialize_postprocess as _materialize_postprocess,
    materialize_transition as _materialize_transition,
)
from services.api.domain.execution.actions.triprole_action_special import (
    execute_gateway_style_action as _execute_gateway_style_action,
    maybe_execute_special_action as _maybe_execute_special_action,
    execute_scan_entry_action as _execute_scan_entry_action,
)
from services.api.domain.execution.actions.triprole_action_transition_runtime import (
    resolve_triprole_transition_runtime as _resolve_triprole_transition_runtime,
)
from services.api.domain.execution.actions.triprole_action_validate import (
    validate_transition as _validate_transition,
)
from services.api.domain.execution.actions.triprole_consensus import (
    _normalize_consensus_signatures,
    _validate_consensus_signatures,
    detect_consensus_deviation,
    verify_biometric_status,
)
from services.api.domain.execution.actions.triprole_dispute import (
    create_consensus_dispute as _create_consensus_dispute,
)
from services.api.domain.execution.offline.triprole_offline import (
    _resolve_existing_offline_result,
)
from services.api.domain.execution.asset.triprole_shadow import (
    _build_shadow_packet,
)
from services.api.domain.execution.asset.triprole_writeback import (
    _patch_state_data_fields,
    update_chain_with_result,
)
from services.api.domain.execution.lineage.triprole_lineage import (
    _is_leaf_boq_row,
)


def execute_triprole_action(
    *,
    sb: Any,
    body: Any,
    valid_actions: set[str],
    consensus_required_roles: tuple[str, ...],
    aggregate_provenance_chain_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    return _execute_triprole_action_flow(
        sb=sb,
        body=body,
        valid_actions=valid_actions,
        consensus_required_roles=consensus_required_roles,
        parse_triprole_action_request_fn=_parse_triprole_action_request,
        materialize_parsed_request_fn=_materialize_parsed_request,
        prepare_triprole_action_input_fn=_prepare_triprole_action_input,
        resolve_existing_offline_result_fn=_resolve_existing_offline_result,
        build_triprole_replayed_response_fn=_build_triprole_replayed_response,
        is_leaf_boq_row_fn=_is_leaf_boq_row,
        proof_utxo_engine_cls=ProofUTXOEngine,
        maybe_execute_special_action_fn=_maybe_execute_special_action,
        execute_scan_entry_action_fn=_execute_scan_entry_action,
        execute_gateway_style_action_fn=_execute_gateway_style_action,
        resolve_triprole_transition_runtime_fn=_resolve_triprole_transition_runtime,
        validate_transition_fn=_validate_transition,
        build_triprole_action_context_fn=_build_triprole_action_context,
        materialize_action_context_fn=_materialize_action_context,
        dispatch_triprole_transition_fn=_dispatch_triprole_transition,
        materialize_transition_fn=_materialize_transition,
        aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
        resolve_dual_pass_gate_fn=resolve_dual_pass_gate,
        normalize_consensus_signatures_fn=_normalize_consensus_signatures,
        validate_consensus_signatures_fn=_validate_consensus_signatures,
        verify_biometric_status_fn=verify_biometric_status,
        detect_consensus_deviation_fn=detect_consensus_deviation,
        create_consensus_dispute_fn=_create_consensus_dispute,
        finalize_triprole_action_fn=_finalize_triprole_action,
        consume_triprole_transition_fn=_consume_triprole_transition,
        materialize_execution_io_fn=_materialize_execution_io,
        run_triprole_postprocess_fn=_run_triprole_postprocess,
        materialize_postprocess_fn=_materialize_postprocess,
        build_triprole_action_response_fn=_build_triprole_action_response,
        update_chain_with_result_fn=update_chain_with_result,
        open_remediation_trip_fn=open_remediation_trip,
        calculate_sovereign_credit_fn=calculate_sovereign_credit,
        sync_to_mirrors_fn=sync_to_mirrors,
        build_shadow_packet_fn=_build_shadow_packet,
        patch_state_data_fields_fn=_patch_state_data_fields,
    )
