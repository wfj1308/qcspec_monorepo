"""
Helpers for create_inspection_flow orchestration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from services.api.normpeg_engine import resolve_normpeg_eval as normpeg_resolve_eval
from services.api.specir_engine import (
    derive_spec_uri as specir_derive_spec_uri,
    evaluate_measurements as specir_evaluate_measurements,
    resolve_spec_rule as specir_resolve_spec_rule,
    spec_excerpt as specir_spec_excerpt,
    threshold_text as specir_threshold_text,
)

from services.api.inspections_utils import (
    evaluate_design_limit_result as _evaluate_design_limit_result,
    extract_photo_hash as _extract_photo_hash,
    extract_photo_media_type as _extract_photo_media_type,
    is_uuid,
    parse_limit_value as _parse_limit_value,
    run_with_retry,
)


def compute_spec_eval_pack(
    *,
    body: Any,
    sb: Any,
) -> dict[str, Any]:
    values_for_eval = [float(v) for v in (body.values or [])]
    if not values_for_eval and body.value is not None:
        values_for_eval = [float(body.value)]

    spec_uri = specir_derive_spec_uri(
        {
            "spec_uri": body.spec_uri,
            "norm_uri": body.norm_uri,
            "norm_ref": body.spec_uri,
            "type": body.type,
            "type_name": body.type_name,
            "component_type": body.component_type,
            "structure_type": body.structure_type,
        },
        row_norm_uri=body.norm_uri,
        fallback_norm_ref=body.spec_uri,
    )
    spec_rule = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=body.type_name or body.type,
        test_type=body.type,
        test_name=body.type_name,
        context={
            "component_type": body.component_type,
            "structure_type": body.structure_type,
            "stake": body.location,
        },
        sb=sb,
    )
    rule_operator = str(spec_rule.get("operator") or "").strip()
    rule_threshold = (
        float(spec_rule["threshold"])
        if spec_rule.get("threshold") is not None
        else (body.standard if body.standard is not None else body.design)
    )
    rule_tolerance = (
        float(spec_rule["tolerance"])
        if spec_rule.get("tolerance") is not None
        else _parse_limit_value(body.limit)
    )

    normpeg_eval = normpeg_resolve_eval(
        spec_uri=spec_uri,
        context={
            "context": body.component_type or body.structure_type,
            "component_type": body.component_type,
            "structure_type": body.structure_type,
            "stake": body.location,
        },
        values=values_for_eval,
        design_value=(body.design if body.design is not None else body.standard),
        sb=sb,
    )
    normpeg_threshold = normpeg_eval.get("threshold") if isinstance(normpeg_eval.get("threshold"), dict) else {}
    normpeg_found = bool(normpeg_eval.get("matched")) and bool(normpeg_threshold.get("found"))
    eval_source = "specir_dynamic"

    if normpeg_found:
        raw_threshold = normpeg_threshold.get("threshold")
        operator = str(normpeg_threshold.get("operator") or "").strip().lower()
        if isinstance(raw_threshold, (list, tuple)) and len(raw_threshold) >= 2:
            lo = float(raw_threshold[0])
            hi = float(raw_threshold[1])
            lower = min(lo, hi)
            upper = max(lo, hi)
            rule_operator = "+/-"
            rule_threshold = round((lower + upper) / 2.0, 6)
            rule_tolerance = round((upper - lower) / 2.0, 6)
        else:
            bound = float(raw_threshold) if raw_threshold is not None else None
            if operator in {"<=", ">=", "=", "<", ">"}:
                rule_operator = operator
            elif operator in {"lt", "max"}:
                rule_operator = "<="
            elif operator in {"gt", "min"}:
                rule_operator = ">="
            else:
                rule_operator = rule_operator or "<="
            rule_threshold = bound
            rule_tolerance = None

        eval_result = {
            "result": str(normpeg_eval.get("result") or "PENDING"),
            "deviation_percent": normpeg_eval.get("deviation_percent"),
            "representative_value": (
                round(sum(values_for_eval) / len(values_for_eval), 4)
                if values_for_eval
                else None
            ),
        }
        spec_rule = {
            **spec_rule,
            "effective_spec_uri": str(normpeg_threshold.get("effective_spec_uri") or spec_rule.get("effective_spec_uri") or spec_uri),
            "version": str(normpeg_threshold.get("version") or spec_rule.get("version") or ""),
            "excerpt": str(normpeg_threshold.get("spec_excerpt") or spec_rule.get("excerpt") or ""),
            "unit": str(normpeg_threshold.get("unit") or spec_rule.get("unit") or body.unit or ""),
            "operator": rule_operator,
            "threshold": rule_threshold,
            "tolerance": rule_tolerance,
            "source": "normpeg",
            "context_matched": bool(normpeg_threshold.get("context_matched")),
            "context_key": str(normpeg_threshold.get("context_key") or ""),
        }
        eval_source = "normpeg_dynamic"
    else:
        eval_result = specir_evaluate_measurements(
            values=values_for_eval,
            operator=rule_operator,
            threshold=rule_threshold,
            tolerance=rule_tolerance,
            fallback_result="PENDING",
        )

    spec_auto_result = str(eval_result.get("result") or "").upper()
    auto_result = _evaluate_design_limit_result(
        design=body.design,
        limit_text=body.limit,
        values=values_for_eval,
    )
    if spec_auto_result in {"PASS", "FAIL"}:
        final_result = spec_auto_result.lower()
        result_source = eval_source
    elif auto_result in {"pass", "fail"}:
        final_result = auto_result
        result_source = "auto_design_limit"
    else:
        final_result = str(body.result or "").strip().lower()
        result_source = "manual"
    if final_result not in {"pass", "warn", "fail"}:
        raise HTTPException(400, "result must be one of pass/warn/fail")

    measured_value = body.value
    if measured_value is None and values_for_eval:
        measured_value = round(sum(values_for_eval) / len(values_for_eval), 4)
    if measured_value is None:
        raise HTTPException(400, "value is required")

    standard_value = body.standard
    if standard_value is None and body.design is not None:
        standard_value = body.design
    if standard_value is None and rule_threshold is not None:
        standard_value = float(rule_threshold)

    effective_spec_uri = str(spec_rule.get("effective_spec_uri") or spec_uri or "")
    spec_snapshot = str(spec_rule.get("excerpt") or specir_spec_excerpt(effective_spec_uri))
    spec_meta = {
        "spec_uri": effective_spec_uri,
        "spec_version": str(spec_rule.get("version") or ""),
        "spec_snapshot": spec_snapshot,
        "captured_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "operator": rule_operator or "",
        "threshold": rule_threshold,
        "tolerance": rule_tolerance,
        "source": str(spec_rule.get("source") or "specir"),
        "context_matched": bool(spec_rule.get("context_matched")),
        "context_key": str(spec_rule.get("context_key") or ""),
    }
    rule_threshold_text = specir_threshold_text(
        rule_operator,
        rule_threshold,
        rule_tolerance,
        spec_rule.get("unit") or body.unit or "",
    )

    return {
        "values_for_eval": values_for_eval,
        "spec_uri": spec_uri,
        "spec_rule": spec_rule,
        "rule_operator": rule_operator,
        "rule_threshold": rule_threshold,
        "rule_tolerance": rule_tolerance,
        "eval_result": eval_result,
        "final_result": final_result,
        "result_source": result_source,
        "measured_value": measured_value,
        "standard_value": standard_value,
        "effective_spec_uri": effective_spec_uri,
        "spec_snapshot": spec_snapshot,
        "spec_meta": spec_meta,
        "rule_threshold_text": rule_threshold_text,
    }


def load_evidence_from_photos(
    *,
    sb: Any,
    project_id: str,
    photo_ids_raw: list[Any] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    photo_ids = [pid for pid in (photo_ids_raw or []) if is_uuid(pid)]
    evidence_list: list[dict[str, Any]] = []
    evidence_hashes: list[str] = []
    evidence_proof_ids: list[str] = []
    if photo_ids:
        try:
            photo_rows = run_with_retry(
                lambda: sb.table("photos")
                .select("*")
                .eq("project_id", project_id)
                .in_("id", photo_ids)
                .execute(),
                retries=1,
            )
            for photo in photo_rows.data or []:
                if not isinstance(photo, dict):
                    continue
                ehash = _extract_photo_hash(photo)
                ppid = str(photo.get("proof_id") or "").strip()
                item = {
                    "id": str(photo.get("id") or ""),
                    "file_name": str(photo.get("file_name") or ""),
                    "media_type": _extract_photo_media_type(photo),
                    "url": str(photo.get("storage_url") or ""),
                    "proof_id": ppid,
                    "proof_hash": str(photo.get("proof_hash") or ""),
                    "evidence_hash": ehash,
                    "size": photo.get("file_size"),
                    "taken_at": str(photo.get("taken_at") or photo.get("created_at") or datetime.utcnow().isoformat()),
                }
                evidence_list.append(item)
                if ehash:
                    evidence_hashes.append(ehash)
                if ppid:
                    evidence_proof_ids.append(ppid)
        except Exception:
            evidence_list = []
            evidence_hashes = []
            evidence_proof_ids = []
    return evidence_list, evidence_hashes, evidence_proof_ids, photo_ids


def build_inspection_create_response(
    *,
    insp: dict[str, Any],
    v_uri: str,
    proof_id: str,
    final_result: str,
    result_source: str,
    measured_value: float,
    body: Any,
    values_for_eval: list[float],
    spec_rule: dict[str, Any],
    spec_uri: str,
    rule_operator: str,
    rule_threshold: float | None,
    rule_tolerance: float | None,
    eval_result: dict[str, Any],
    spec_snapshot: str,
    remediation_task: dict[str, Any] | None,
    evidence_list: list[dict[str, Any]],
    linked_photo_count: int,
    utxo_row: dict[str, Any] | None,
    utxo_auto_consume: dict[str, Any],
    gate: dict[str, Any],
    gate_soft_override_reason: str | None,
    gate_pack: dict[str, Any],
    erpnext_notify: dict[str, Any],
) -> dict[str, Any]:
    return {
        "inspection_id": insp["id"],
        "v_uri": v_uri,
        "proof_id": proof_id,
        "result": final_result,
        "result_source": result_source,
        "computed_value": measured_value,
        "design": body.design,
        "limit": body.limit,
        "values": values_for_eval,
        "spec_uri": str(spec_rule.get("effective_spec_uri") or spec_uri or ""),
        "spec_version": str(spec_rule.get("version") or ""),
        "rule_operator": rule_operator or "",
        "rule_threshold": rule_threshold,
        "rule_tolerance": rule_tolerance,
        "deviation_percent": eval_result.get("deviation_percent"),
        "spec_snapshot": spec_snapshot,
        "action_item_id": (
            ((remediation_task.get("state_data") or {}).get("issue_id") if isinstance(remediation_task, dict) else "")
            or ""
        ),
        "gate_action": "release" if final_result == "pass" else "block",
        "gate_reason": "inspection_not_passed" if final_result != "pass" else "",
        "evidence": evidence_list,
        "linked_photo_count": linked_photo_count,
        "utxo_proof": {
            "proof_id": utxo_row.get("proof_id") if isinstance(utxo_row, dict) else proof_id,
            "proof_hash": utxo_row.get("proof_hash") if isinstance(utxo_row, dict) else None,
            "gitpeg_anchor": utxo_row.get("gitpeg_anchor") if isinstance(utxo_row, dict) else None,
        },
        "utxo_auto_consume": utxo_auto_consume,
        "remediation_task": {
            "proof_id": remediation_task.get("proof_id"),
            "issue_id": (remediation_task.get("state_data") or {}).get("issue_id"),
            "status": (remediation_task.get("state_data") or {}).get("status"),
        } if isinstance(remediation_task, dict) else None,
        "gate": gate,
        "gate_soft_override": bool(gate_soft_override_reason),
        "gate_soft_override_reason": gate_soft_override_reason,
        "metering_lookup": gate_pack.get("metering_lookup"),
        "erpnext_notify": erpnext_notify,
    }
