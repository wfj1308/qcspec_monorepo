"""Measure/variation transition helpers for TripRole execution."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_asset import (
    _compute_delta_merge,
    _extract_variation_delta_amount,
)
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    sha256_json as _sha256_json,
    to_text as _to_text,
)
from services.api.domain.execution.lineage.triprole_lineage import _build_variation_compensates
from services.api.domain.utxo.common import normalize_result as _normalize_result


def apply_measure_record_transition(
    *,
    input_proof_id: str,
    payload: dict[str, Any],
    segment_uri: str,
    boq_item_uri: str,
    geo_compliance: dict[str, Any],
    next_state: dict[str, Any],
) -> dict[str, Any]:
    outside_fence = bool(geo_compliance.get("outside"))
    merged_state = dict(next_state)
    merged_state.update(
        {
            "lifecycle_stage": "INSTALLATION",
            "status": "INSTALLATION",
            "measurement": payload,
            "measurement_hash": _sha256_json(
                {
                    "input_proof_id": input_proof_id,
                    "payload": payload,
                    "segment_uri": segment_uri,
                    "boq_item_uri": boq_item_uri,
                }
            ),
            "trust_level": "LOW" if outside_fence else "HIGH",
            "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
        }
    )
    sensor_hardware = _as_dict(payload.get("sensor_hardware"))
    if sensor_hardware:
        merged_state["sensor_hardware"] = sensor_hardware
        merged_state["sensor_hardware_fingerprint"] = _sha256_json(sensor_hardware)
    if outside_fence and bool(geo_compliance.get("strict_mode")):
        raise HTTPException(409, "geo-fence violation: measure.record blocked by strict_mode")

    return {
        "next_proof_type": "approval",
        "next_state": merged_state,
    }


def apply_variation_record_transition(
    *,
    input_row: dict[str, Any],
    input_proof_id: str,
    payload: dict[str, Any],
    override_result: str,
    now_iso: str,
    executor_uri: str,
    next_state: dict[str, Any],
    extract_variation_delta_amount_fn: Callable[[dict[str, Any]], float | None] = _extract_variation_delta_amount,
    build_variation_compensates_fn: Callable[[dict[str, Any], str], list[str]] = _build_variation_compensates,
    compute_delta_merge_fn: Callable[..., dict[str, Any]] = _compute_delta_merge,
) -> dict[str, Any]:
    merged_state = dict(next_state)
    next_result = _normalize_result(override_result or _to_text(payload.get("result") or "PASS"))
    delta_amount = extract_variation_delta_amount_fn(payload)
    compensates = build_variation_compensates_fn(payload, input_proof_id)
    variation_payload = dict(payload)
    if delta_amount is not None:
        variation_payload["delta_amount"] = round(float(delta_amount), 6)
    merged_state.update(
        {
            "lifecycle_stage": "VARIATION",
            "status": "VARIATION",
            "variation": variation_payload,
            "compensates": compensates,
            "source_fail_proof_id": input_proof_id,
            "variation_hash": _sha256_json(
                {
                    "input_proof_id": input_proof_id,
                    "payload": variation_payload,
                    "compensates": compensates,
                }
            ),
        }
    )
    if delta_amount is not None and abs(float(delta_amount)) > 1e-9:
        merge = compute_delta_merge_fn(input_row=input_row, delta_amount=float(delta_amount))
        ledger = dict(_as_dict(merged_state.get("ledger")))
        ledger.update(
            {
                "initial_balance": merge["initial_balance"],
                "delta_total": merge["delta_total_after"],
                "merged_total": merge["merged_total_after"],
                "transferred_total": merge["transferred_total"],
                "previous_balance": merge["previous_balance"],
                "current_balance": merge["balance_after"],
                "remaining_balance": merge["balance_after"],
                "balance": merge["balance_after"],
                "last_delta_amount": merge["delta_amount"],
                "last_delta_reason": _to_text(payload.get("reason") or "").strip() or "variation.record",
                "last_delta_at": now_iso,
                "last_delta_executor_uri": executor_uri,
            }
        )
        merged_state.update(
            {
                "ledger": ledger,
                "available_quantity": merge["balance_after"],
                "remaining_quantity": merge["balance_after"],
                "delta_utxo": {
                    "delta_amount": merge["delta_amount"],
                    "merge_strategy": "genesis_plus_delta_minus_transferred",
                    "merged_total_before": merge["merged_total_before"],
                    "merged_total_after": merge["merged_total_after"],
                    "previous_balance": merge["previous_balance"],
                    "balance_after": merge["balance_after"],
                },
            }
        )

    return {
        "next_proof_type": "archive",
        "next_result": next_result,
        "next_state": merged_state,
    }


__all__ = [
    "apply_measure_record_transition",
    "apply_variation_record_transition",
]
