"""Action branch dispatcher for TripRole execution."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.actions.triprole_action_dispute import (
    apply_dispute_resolve_transition,
)
from services.api.domain.execution.actions.triprole_action_measure_variation import (
    apply_measure_record_transition,
    apply_variation_record_transition,
)
from services.api.domain.execution.actions.triprole_action_quality import (
    apply_quality_check_transition,
)
from services.api.domain.execution.actions.triprole_action_settlement import (
    apply_settlement_confirm_transition,
)
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    to_text as _to_text,
)
from services.api.domain.utxo.common import normalize_result as _normalize_result


def dispatch_triprole_transition(
    *,
    action: str,
    sb: Any,
    body: Any,
    input_row: dict[str, Any],
    input_sd: dict[str, Any],
    input_proof_id: str,
    payload: dict[str, Any],
    project_uri: str,
    boq_item_uri: str,
    segment_uri: str,
    executor_uri: str,
    override_result: str,
    now_iso: str,
    next_state: dict[str, Any],
    geo_compliance: dict[str, Any],
    gate_binding: dict[str, Any],
    signer_metadata_raw: Any,
    normalized_signer_metadata: dict[str, Any],
    consensus_required_roles: tuple[str, ...],
    aggregate_provenance_chain_fn: Callable[[str, Any], dict[str, Any]],
    resolve_dual_pass_gate_fn: Callable[..., dict[str, Any]],
    normalize_consensus_signatures_fn: Callable[[Any], list[dict[str, Any]]],
    validate_consensus_signatures_fn: Callable[..., dict[str, Any]],
    verify_biometric_status_fn: Callable[..., dict[str, Any]],
    detect_consensus_deviation_fn: Callable[..., dict[str, Any]],
    create_consensus_dispute_fn: Callable[..., dict[str, Any]],
    apply_quality_check_transition_fn: Callable[..., dict[str, Any]] = apply_quality_check_transition,
    apply_measure_record_transition_fn: Callable[..., dict[str, Any]] = apply_measure_record_transition,
    apply_variation_record_transition_fn: Callable[..., dict[str, Any]] = apply_variation_record_transition,
    apply_dispute_resolve_transition_fn: Callable[..., dict[str, Any]] = apply_dispute_resolve_transition,
    apply_settlement_confirm_transition_fn: Callable[..., dict[str, Any]] = apply_settlement_confirm_transition,
) -> dict[str, Any]:
    next_proof_type = "inspection"
    next_result = _normalize_result(override_result or _to_text(payload.get("result") or "PASS"))
    tx_type = "consume"
    biometric_check: dict[str, Any] = {}
    merged_state = dict(next_state)

    if action == "quality.check":
        next_proof_type = "inspection"
        quality_transition = apply_quality_check_transition_fn(
            sb=sb,
            input_proof_id=input_proof_id,
            payload=payload,
            input_sd=input_sd,
            gate_binding=gate_binding,
            boq_item_uri=boq_item_uri,
            segment_uri=segment_uri,
            override_result=override_result,
            now_iso=now_iso,
            next_state=merged_state,
        )
        next_result = _normalize_result(_to_text(quality_transition.get("next_result") or next_result))
        merged_state = dict(_as_dict(quality_transition.get("next_state")))

    elif action == "measure.record":
        measure_transition = apply_measure_record_transition_fn(
            input_proof_id=input_proof_id,
            payload=payload,
            segment_uri=segment_uri,
            boq_item_uri=boq_item_uri,
            geo_compliance=geo_compliance,
            next_state=merged_state,
        )
        next_proof_type = _to_text(measure_transition.get("next_proof_type") or "approval").strip() or "approval"
        merged_state = dict(_as_dict(measure_transition.get("next_state")))

    elif action == "variation.record":
        variation_transition = apply_variation_record_transition_fn(
            input_row=input_row,
            input_proof_id=input_proof_id,
            payload=payload,
            override_result=override_result,
            now_iso=now_iso,
            executor_uri=executor_uri,
            next_state=merged_state,
        )
        next_proof_type = _to_text(variation_transition.get("next_proof_type") or "archive").strip() or "archive"
        next_result = _normalize_result(_to_text(variation_transition.get("next_result") or next_result))
        merged_state = dict(_as_dict(variation_transition.get("next_state")))

    elif action == "dispute.resolve":
        dispute_transition = apply_dispute_resolve_transition_fn(
            payload=payload,
            override_result=override_result,
            now_iso=now_iso,
            next_state=merged_state,
        )
        next_proof_type = (
            _to_text(dispute_transition.get("next_proof_type") or "dispute_resolution").strip() or "dispute_resolution"
        )
        next_result = _normalize_result(_to_text(dispute_transition.get("next_result") or next_result))
        merged_state = dict(_as_dict(dispute_transition.get("next_state")))

    elif action == "settlement.confirm":
        settlement_transition = apply_settlement_confirm_transition_fn(
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
            signer_metadata_raw=signer_metadata_raw,
            normalized_signer_metadata=normalized_signer_metadata,
            now_iso=now_iso,
            next_state=merged_state,
            consensus_required_roles=consensus_required_roles,
            aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
            resolve_dual_pass_gate_fn=resolve_dual_pass_gate_fn,
            normalize_consensus_signatures_fn=normalize_consensus_signatures_fn,
            validate_consensus_signatures_fn=validate_consensus_signatures_fn,
            verify_biometric_status_fn=verify_biometric_status_fn,
            detect_consensus_deviation_fn=detect_consensus_deviation_fn,
            create_consensus_dispute_fn=create_consensus_dispute_fn,
        )
        next_proof_type = _to_text(settlement_transition.get("next_proof_type") or "payment").strip() or "payment"
        tx_type = _to_text(settlement_transition.get("tx_type") or "settle").strip() or "settle"
        merged_state = dict(_as_dict(settlement_transition.get("next_state")))
        biometric_check = dict(_as_dict(settlement_transition.get("biometric_check")))

    return {
        "next_proof_type": next_proof_type,
        "next_result": next_result,
        "tx_type": tx_type,
        "next_state": merged_state,
        "biometric_check": biometric_check,
    }


__all__ = ["dispatch_triprole_transition"]
