"""Quality-check transition helpers for TripRole execution."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    sha256_json as _sha256_json,
    to_float as _to_float,
    to_text as _to_text,
)
from services.api.domain.execution.triprole_geo_sensor import (
    extract_values as _extract_values,
)
from services.api.domain.execution.integrations import (
    evaluate_with_threshold_pack,
    resolve_dynamic_threshold,
    resolve_normpeg_eval,
)
from services.api.domain.execution.triprole_lineage import _item_no_from_boq_uri
from services.api.domain.utxo.common import normalize_result as _normalize_result


def apply_quality_check_transition(
    *,
    sb: Any,
    input_proof_id: str,
    payload: dict[str, Any],
    input_sd: dict[str, Any],
    gate_binding: dict[str, Any],
    boq_item_uri: str,
    segment_uri: str,
    override_result: str,
    now_iso: str,
    next_state: dict[str, Any],
    resolve_dynamic_threshold_fn: Callable[..., dict[str, Any]] = resolve_dynamic_threshold,
    evaluate_with_threshold_pack_fn: Callable[..., dict[str, Any]] = evaluate_with_threshold_pack,
    resolve_normpeg_eval_fn: Callable[..., dict[str, Any]] = resolve_normpeg_eval,
    extract_values_fn: Callable[[dict[str, Any]], list[float]] = _extract_values,
) -> dict[str, Any]:
    requested_spec_uri = _to_text(payload.get("spec_uri") or payload.get("norm_uri") or "").strip()
    bound_spec_uri = _to_text(
        gate_binding.get("linked_spec_uri")
        or input_sd.get("linked_spec_uri")
        or input_sd.get("spec_uri")
        or ""
    ).strip()
    if bool(gate_binding.get("gate_template_lock")) and bound_spec_uri:
        if requested_spec_uri and requested_spec_uri != bound_spec_uri:
            raise HTTPException(
                409,
                f"spec_template_locked: {boq_item_uri} is bound to {bound_spec_uri}",
            )
        spec_uri = bound_spec_uri
    else:
        spec_uri = requested_spec_uri or _to_text(input_sd.get("spec_uri") or "").strip()

    design_value = _to_float(payload.get("design"))
    if design_value is None:
        design_value = _to_float(payload.get("standard"))
    values_for_eval = extract_values_fn(payload)
    norm_eval: dict[str, Any] = {}
    threshold_pack: dict[str, Any] = {}
    context_payload = {
        "context": payload.get("context") or payload.get("component_type") or payload.get("part"),
        "component_type": payload.get("component_type") or payload.get("part"),
        "structure_type": payload.get("structure_type"),
        "stake": payload.get("stake") or payload.get("location"),
    }
    dynamic_pack = resolve_dynamic_threshold_fn(
        sb=sb,
        gate_id=_to_text(gate_binding.get("linked_gate_id") or "").strip(),
        context=context_payload,
    )
    if bool(dynamic_pack.get("found")):
        threshold_pack = dynamic_pack
        norm_eval = evaluate_with_threshold_pack_fn(
            threshold_pack=threshold_pack,
            values=values_for_eval,
            design_value=design_value,
        )
    elif spec_uri:
        norm_eval = resolve_normpeg_eval_fn(
            spec_uri=spec_uri,
            context=context_payload,
            values=values_for_eval,
            design_value=design_value,
            sb=sb,
        )
        threshold_pack = _as_dict(norm_eval.get("threshold"))

    auto_result = _to_text(norm_eval.get("result") or "").strip().upper()
    if override_result:
        next_result = _normalize_result(override_result)
    elif auto_result in {"PASS", "FAIL", "OBSERVE", "PENDING"}:
        next_result = _normalize_result(auto_result)
    else:
        next_result = _normalize_result(_to_text(payload.get("result") or "PASS"))

    merged_state = dict(next_state)
    merged_state.update(
        {
            "lifecycle_stage": "ENTRY",
            "status": "ENTRY",
            "quality_payload": payload,
            "result_source": "normpeg_dynamic" if threshold_pack.get("found") else "manual",
            "spec_uri": _to_text(
                threshold_pack.get("effective_spec_uri")
                or threshold_pack.get("spec_uri")
                or spec_uri
                or input_sd.get("spec_uri")
                or ""
            ).strip(),
            "spec_snapshot": _to_text(
                threshold_pack.get("spec_excerpt") or input_sd.get("spec_snapshot") or ""
            ).strip(),
            "qc_gate_binding": {
                "linked_gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
                "linked_gate_ids": _as_list(gate_binding.get("linked_gate_ids")),
                "linked_gate_rules": _as_list(gate_binding.get("linked_gate_rules")),
                "linked_spec_uri": _to_text(gate_binding.get("linked_spec_uri") or "").strip(),
                "spec_dict_key": _to_text(gate_binding.get("spec_dict_key") or "").strip(),
                "spec_item": _to_text(gate_binding.get("spec_item") or "").strip(),
                "gate_template_lock": bool(gate_binding.get("gate_template_lock")),
                "gate_binding_hash": _to_text(gate_binding.get("gate_binding_hash") or "").strip(),
            },
            "norm_evaluation": {
                "matched": bool(norm_eval.get("matched")) if norm_eval else False,
                "result": _to_text(norm_eval.get("result") or "").strip().upper() if norm_eval else "",
                "deviation_percent": norm_eval.get("deviation_percent") if norm_eval else None,
                "values_for_eval": norm_eval.get("values_for_eval") if norm_eval else values_for_eval,
                "design_value": norm_eval.get("design_value") if norm_eval else design_value,
                "lower": norm_eval.get("lower") if norm_eval else None,
                "upper": norm_eval.get("upper") if norm_eval else None,
                "center": norm_eval.get("center") if norm_eval else None,
                "tolerance": norm_eval.get("tolerance") if norm_eval else None,
                "threshold": threshold_pack,
            },
            "quality_hash": _sha256_json(
                {
                    "input_proof_id": input_proof_id,
                    "payload": payload,
                    "boq_item_uri": boq_item_uri,
                    "segment_uri": segment_uri,
                    "spec_uri": _to_text(
                        threshold_pack.get("effective_spec_uri")
                        or threshold_pack.get("spec_uri")
                        or spec_uri
                    ).strip(),
                    "spec_snapshot": _to_text(threshold_pack.get("spec_excerpt") or "").strip(),
                    "result": next_result,
                    "values_for_eval": values_for_eval,
                }
            ),
        }
    )
    gate_result_payload = {
        "gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
        "linked_gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
        "linked_gate_ids": _as_list(gate_binding.get("linked_gate_ids")),
        "linked_gate_rules": _as_list(gate_binding.get("linked_gate_rules")),
        "spec_dict_key": _to_text(gate_binding.get("spec_dict_key") or "").strip(),
        "spec_item": _to_text(gate_binding.get("spec_item") or "").strip(),
        "context_key": _to_text(threshold_pack.get("context_key") or "").strip(),
        "result": _to_text(next_result or "").strip().upper(),
        "result_source": _to_text(merged_state.get("result_source") or "").strip(),
        "spec_uri": _to_text(merged_state.get("spec_uri") or "").strip(),
        "spec_snapshot": _to_text(merged_state.get("spec_snapshot") or "").strip(),
        "quality_hash": _to_text(merged_state.get("quality_hash") or "").strip(),
        "input_proof_id": input_proof_id,
        "boq_item_uri": boq_item_uri,
        "item_code": _to_text(input_sd.get("item_no") or _item_no_from_boq_uri(boq_item_uri)).strip(),
        "evaluated_at": now_iso,
    }
    merged_state["qc_gate_result"] = gate_result_payload
    merged_state["qc_gate_status"] = _to_text(next_result or "").strip().upper()
    merged_state["qc_gate_result_hash"] = _sha256_json(gate_result_payload)

    return {
        "next_result": next_result,
        "next_state": merged_state,
    }


__all__ = ["apply_quality_check_transition"]
