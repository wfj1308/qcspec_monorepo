"""Settlement-confirm transition helpers for TripRole execution."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.component.triprole_component_utxo import (
    build_component_utxo_verification as _build_component_utxo_verification,
)
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    safe_path_token as _safe_path_token,
    to_float as _to_float,
    to_text as _to_text,
)


def _resolve_consensus_signatures_raw(*, payload: dict[str, Any], body: Any) -> Any:
    signatures_raw = payload.get("signatures")
    if signatures_raw is None:
        signatures_raw = payload.get("consensus_signatures")
    if signatures_raw is None and not isinstance(body, dict):
        signatures_raw = getattr(body, "signatures", None)
    if signatures_raw is None and not isinstance(body, dict):
        signatures_raw = getattr(body, "consensus_signatures", None)
    elif signatures_raw is None and isinstance(body, dict):
        signatures_raw = body.get("signatures")
    if signatures_raw is None and isinstance(body, dict):
        signatures_raw = body.get("consensus_signatures")
    return signatures_raw


def _resolve_stage_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    if stage:
        return stage
    proof_type = _to_text(row.get("proof_type") or "").strip().lower()
    if proof_type == "zero_ledger":
        return "INITIAL"
    return "UNKNOWN"


def _extract_quantity_from_row(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    settlement = _as_dict(sd.get("settlement"))
    measurement = _as_dict(sd.get("measurement"))
    for candidate in (
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        settlement.get("confirmed_quantity"),
        measurement.get("quantity"),
        measurement.get("used_quantity"),
        sd.get("settled_quantity"),
        sd.get("quantity"),
    ):
        value = _to_float(candidate)
        if value is not None:
            return max(0.0, float(value))
    return 0.0


def _load_rows_for_boq(*, sb: Any, project_uri: str, boq_item_uri: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        query = sb.table("proof_utxo").select(
            "proof_id,parent_proof_id,proof_type,result,project_uri,segment_uri,state_data,created_at"
        )
        if _to_text(project_uri).strip():
            query = query.eq("project_uri", _to_text(project_uri).strip())
        query = query.filter("state_data->>boq_item_uri", "eq", _to_text(boq_item_uri).strip())
        query = query.order("created_at", desc=False).limit(5000)
        rows = query.execute().data or []
    except Exception:
        rows = []

    if rows:
        return [row for row in rows if isinstance(row, dict)]

    try:
        query = sb.table("proof_utxo").select(
            "proof_id,parent_proof_id,proof_type,result,project_uri,segment_uri,state_data,created_at"
        )
        if _to_text(project_uri).strip():
            query = query.eq("project_uri", _to_text(project_uri).strip())
        query = query.eq("segment_uri", _to_text(boq_item_uri).strip()).order("created_at", desc=False).limit(5000)
        rows = query.execute().data or []
    except Exception:
        rows = []
    return [row for row in rows if isinstance(row, dict)]


def _resolve_approved_total(*, payload: dict[str, Any], input_sd: dict[str, Any]) -> float:
    from_payload = _to_float(payload.get("approved_total"))
    if from_payload is not None:
        return max(0.0, float(from_payload))

    ledger = _as_dict(input_sd.get("ledger"))
    merged_total = _to_float(ledger.get("merged_total"))
    if merged_total is not None:
        return max(0.0, float(merged_total))

    initial = _to_float(ledger.get("initial_balance"))
    delta_total = _to_float(ledger.get("delta_total"))
    if initial is not None:
        return max(0.0, float(initial + (delta_total or 0.0)))

    for candidate in (
        input_sd.get("approved_quantity"),
        input_sd.get("contract_quantity"),
        input_sd.get("design_quantity"),
    ):
        value = _to_float(candidate)
        if value is not None:
            return max(0.0, float(value))
    return 0.0


def _resolve_used_total(*, payload: dict[str, Any], input_sd: dict[str, Any], all_rows: list[dict[str, Any]]) -> float:
    from_payload = _to_float(payload.get("used_total"))
    if from_payload is not None:
        return max(0.0, float(from_payload))

    ledger = _as_dict(input_sd.get("ledger"))
    transferred_total = _to_float(ledger.get("transferred_total"))
    if transferred_total is not None and float(transferred_total) > 0:
        return max(0.0, float(transferred_total))

    used_rows = [
        row
        for row in all_rows
        if _resolve_stage_from_row(row) == "INSTALLATION"
        and _to_text(row.get("result") or "").strip().upper() == "PASS"
    ]
    if used_rows:
        return max(0.0, float(sum(_extract_quantity_from_row(row) for row in used_rows)))

    settled_total = _to_float(payload.get("settled_total"))
    if settled_total is not None:
        return max(0.0, float(settled_total))
    return 0.0


def _resolve_settlement_preconditions(
    *,
    payload: dict[str, Any],
    input_sd: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    approved_total = _resolve_approved_total(payload=payload, input_sd=input_sd)
    used_total = _resolve_used_total(payload=payload, input_sd=input_sd, all_rows=rows)
    tolerance_abs = float(_to_float(payload.get("conservation_tolerance_abs")) or 1e-6)
    tolerance_ratio = float(_to_float(payload.get("conservation_tolerance_ratio")) or 0.0)
    gap = abs(approved_total - used_total)
    allowed_gap = max(tolerance_abs, abs(approved_total) * tolerance_ratio)
    conservation_ok = gap <= allowed_gap

    by_id = {
        _to_text(row.get("proof_id") or "").strip(): row
        for row in rows
        if _to_text(row.get("proof_id") or "").strip()
    }
    used_rows = [
        row
        for row in rows
        if _resolve_stage_from_row(row) == "INSTALLATION"
        and _to_text(row.get("result") or "").strip().upper() == "PASS"
    ]

    missing_qc_for_used: list[str] = []
    if used_total > allowed_gap and not used_rows:
        missing_qc_for_used.append("no_used_records_for_positive_total")
    else:
        for row in used_rows:
            current = row
            seen: set[str] = set()
            has_qc_pass = False
            for _ in range(256):
                proof_id = _to_text(current.get("proof_id") or "").strip()
                if not proof_id or proof_id in seen:
                    break
                seen.add(proof_id)

                stage = _resolve_stage_from_row(current)
                result = _to_text(current.get("result") or "").strip().upper()
                if stage == "ENTRY" and result == "PASS":
                    has_qc_pass = True
                    break

                parent_id = _to_text(current.get("parent_proof_id") or "").strip()
                if not parent_id or parent_id not in by_id:
                    break
                current = by_id[parent_id]

            if not has_qc_pass:
                missing_qc_for_used.append(_to_text(row.get("proof_id") or "").strip() or "unknown_used_proof")

    return {
        "approved_total": round(float(approved_total), 6),
        "used_total": round(float(used_total), 6),
        "gap": round(float(gap), 6),
        "allowed_gap": round(float(allowed_gap), 6),
        "conservation_ok": conservation_ok,
        "used_qc_ok": not missing_qc_for_used,
        "missing_qc_for_used": missing_qc_for_used,
    }


def _resolve_component_payload(
    *,
    payload: dict[str, Any],
    input_sd: dict[str, Any],
    project_uri: str,
    boq_item_uri: str,
) -> dict[str, Any]:
    component_payload = _as_dict(payload.get("component_utxo"))
    if not component_payload:
        component_payload = _as_dict(input_sd.get("component_utxo"))

    def _read(name: str, default: Any = None) -> Any:
        if name in payload:
            return payload.get(name)
        return input_sd.get(name, default)

    if not component_payload:
        component_id = _to_text(_read("component_id") or "").strip()
        if component_id:
            component_payload = {
                "component_id": component_id,
                "kind": _to_text(_read("component_kind") or "component").strip() or "component",
                "boq_items": _as_list(_read("component_boq_items") or _read("boq_items")),
                "bom": _read("component_bom") if _read("component_bom") is not None else _read("bom"),
                "material_inputs": _as_list(_read("component_material_inputs") or _read("material_inputs")),
                "material_input_proof_ids": _as_list(
                    _read("component_material_input_proof_ids") or _read("material_input_proof_ids")
                ),
                "material_bindings": _as_list(_read("component_material_bindings") or _read("material_bindings")),
                "default_tolerance_ratio": _read("component_default_tolerance_ratio"),
            }

    if not component_payload:
        return {}

    if not _to_text(component_payload.get("project_uri") or "").strip():
        component_payload["project_uri"] = _to_text(project_uri).strip()
    if not _to_text(component_payload.get("component_uri") or "").strip():
        component_id = _to_text(component_payload.get("component_id") or "").strip()
        if component_id and _to_text(project_uri).strip():
            component_payload["component_uri"] = f"{_to_text(project_uri).strip().rstrip('/')}/component/{component_id}"

    boq_items = _as_list(component_payload.get("boq_items"))
    if not boq_items and _to_text(boq_item_uri).strip():
        component_payload["boq_items"] = [{"item_id": _to_text(boq_item_uri).strip()}]

    return component_payload


def _hash_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def apply_settlement_confirm_transition(
    *,
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
    signer_metadata_raw: Any,
    normalized_signer_metadata: dict[str, Any],
    now_iso: str,
    next_state: dict[str, Any],
    consensus_required_roles: tuple[str, ...],
    aggregate_provenance_chain_fn: Callable[[str, Any], dict[str, Any]],
    resolve_dual_pass_gate_fn: Callable[..., dict[str, Any]],
    normalize_consensus_signatures_fn: Callable[[Any], list[dict[str, Any]]],
    validate_consensus_signatures_fn: Callable[..., dict[str, Any]],
    verify_biometric_status_fn: Callable[..., dict[str, Any]],
    detect_consensus_deviation_fn: Callable[..., dict[str, Any]],
    create_consensus_dispute_fn: Callable[..., dict[str, Any]],
    build_component_utxo_verification_fn: Callable[..., dict[str, Any]] = _build_component_utxo_verification,
) -> dict[str, Any]:
    # Block if any unresolved dispute exists.
    try:
        open_dispute = (
            sb.table("proof_utxo")
            .select("proof_id")
            .eq("segment_uri", boq_item_uri)
            .eq("proof_type", "dispute")
            .eq("spent", False)
            .limit(1)
            .execute()
            .data
            or []
        )
        if open_dispute:
            raise HTTPException(409, f"consensus_dispute_open: {open_dispute[0].get('proof_id')}")
    except HTTPException:
        raise
    except Exception:
        pass

    agg_before = aggregate_provenance_chain_fn(input_proof_id, sb)
    gate = _as_dict(agg_before.get("gate"))
    if bool(gate.get("blocked")):
        raise HTTPException(
            409,
            f"QCGate locked: {gate.get('reason')}; uncompensated={','.join(gate.get('uncompensated_fail_proof_ids') or [])}",
        )
    dual_gate = resolve_dual_pass_gate_fn(
        sb=sb,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
    )
    if not bool(dual_gate.get("ok")):
        raise HTTPException(
            409,
            f"dual_pass_gate_failed: qc_pass={dual_gate.get('qc_pass_count')} lab_pass={dual_gate.get('lab_pass_count')}",
        )

    settlement_rows = _load_rows_for_boq(
        sb=sb,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
    )
    preconditions = _resolve_settlement_preconditions(
        payload=payload,
        input_sd=input_sd,
        rows=settlement_rows,
    )

    signatures_raw = _resolve_consensus_signatures_raw(payload=payload, body=body)
    consensus_signatures = normalize_consensus_signatures_fn(signatures_raw)
    consensus_check = validate_consensus_signatures_fn(consensus_signatures)
    if not consensus_check.get("ok"):
        missing = ",".join(consensus_check.get("missing_roles") or [])
        invalid = ",".join(consensus_check.get("invalid") or [])
        raise HTTPException(
            409,
            f"consensus_signatures_incomplete; missing={missing or '-'}; invalid={invalid or '-'}",
        )
    biometric_check = verify_biometric_status_fn(
        signer_metadata=normalized_signer_metadata,
        consensus_signatures=consensus_signatures,
        required_roles=consensus_required_roles,
    )
    if not bool(biometric_check.get("ok")):
        missing = ",".join(_as_list(biometric_check.get("missing")))
        failed = ",".join(_as_list(biometric_check.get("failed")))
        raise HTTPException(
            409,
            f"biometric_verification_incomplete; missing={missing or '-'}; failed={failed or '-'}",
        )

    consensus_complete = bool(consensus_check.get("ok"))
    preconditions["consensus_complete"] = consensus_complete

    allow_legacy_settlement = bool(payload.get("allow_legacy_settlement", False))
    enforce_component_utxo = bool(payload.get("enforce_component_utxo", True))
    component_payload = _resolve_component_payload(
        payload=payload,
        input_sd=input_sd,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
    )
    component_verification: dict[str, Any] = {}
    if component_payload:
        component_verification = _as_dict(
            build_component_utxo_verification_fn(
                sb=sb,
                component_id=_to_text(component_payload.get("component_id") or "").strip(),
                component_uri=_to_text(component_payload.get("component_uri") or "").strip(),
                project_uri=_to_text(component_payload.get("project_uri") or "").strip(),
                kind=_to_text(component_payload.get("kind") or "component").strip() or "component",
                boq_items=_as_list(component_payload.get("boq_items")),
                bom=component_payload.get("bom"),
                material_inputs=_as_list(component_payload.get("material_inputs")),
                material_input_proof_ids=_as_list(component_payload.get("material_input_proof_ids")),
                material_bindings=_as_list(component_payload.get("material_bindings")),
                default_tolerance_ratio=float(component_payload.get("default_tolerance_ratio") or 0.05),
                render_docpeg=False,
                include_docx_base64=False,
            )
        )
        preconditions["component_present"] = True
        preconditions["component_conservation_ok"] = bool(component_verification.get("passed"))
    else:
        preconditions["component_present"] = False
        preconditions["component_conservation_ok"] = False
        if enforce_component_utxo and not allow_legacy_settlement:
            raise HTTPException(409, "settlement_precondition_failed: component_utxo_missing")

    if component_verification and not bool(component_verification.get("passed")):
        raise HTTPException(409, "settlement_precondition_failed: component_conservation_failed")

    if not bool(preconditions.get("conservation_ok")):
        raise HTTPException(
            409,
            "settlement_precondition_failed: conservation_mismatch"
            f" approved={preconditions.get('approved_total')} used={preconditions.get('used_total')}"
            f" gap={preconditions.get('gap')} allowed={preconditions.get('allowed_gap')}",
        )
    if not bool(preconditions.get("used_qc_ok")):
        missing_qc = ",".join(_as_list(preconditions.get("missing_qc_for_used")))
        raise HTTPException(
            409,
            f"settlement_precondition_failed: used_without_quality_proof; missing={missing_qc or '-'}",
        )
    if not consensus_complete:
        raise HTTPException(409, "settlement_precondition_failed: consensus_incomplete")

    conflict = detect_consensus_deviation_fn(
        signer_metadata_raw=signer_metadata_raw,
        payload=payload,
        input_sd=input_sd,
    )
    if conflict.get("conflict"):
        dispute = create_consensus_dispute_fn(
            sb=sb,
            input_row=input_row,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
            executor_uri=executor_uri,
            conflict=conflict,
            consensus_signatures=consensus_signatures,
            signer_metadata=normalized_signer_metadata,
        )
        dispute_id = _to_text(dispute.get("proof_id") or "").strip()
        raise HTTPException(
            409,
            f"consensus_conflict_detected; dispute_proof_id={dispute_id or '-'}",
        )

    artifact_seed = hashlib.sha256(f"{input_proof_id}|{now_iso}|{project_uri}".encode("utf-8")).hexdigest()[:16]
    artifact_uri = _to_text(payload.get("artifact_uri") or "").strip()
    if not artifact_uri:
        base = project_uri.rstrip("/") if project_uri else "v://project"
        artifact_token = _safe_path_token(boq_item_uri or segment_uri or "settlement", fallback="settlement")
        artifact_uri = f"{base}/artifact/{artifact_token}/{artifact_seed}"

    merged_state = dict(next_state)
    component_factors = _as_dict(component_verification.get("proof_factors"))
    final_proof_factors = {
        "material_chain_root_hash": _to_text(component_factors.get("material_chain_root_hash") or "").strip(),
        "bom_deviation_hash": _to_text(component_factors.get("bom_deviation_hash") or "").strip(),
        "norm_acceptance_hash": _to_text(component_factors.get("norm_acceptance_hash") or "").strip(),
        "lineage_total_hash": _to_text(agg_before.get("total_proof_hash") or "").strip(),
    }
    final_proof_factors["final_proof_hash"] = _hash_json(final_proof_factors)
    merged_state.update(
        {
            "lifecycle_stage": "SETTLEMENT",
            "status": "SETTLEMENT",
            "settlement": payload,
            "settlement_confirmed_at": now_iso,
            "pre_settlement_total_hash": _to_text(agg_before.get("total_proof_hash") or "").strip(),
            "artifact_uri": artifact_uri,
            "consensus": {
                "required_roles": list(consensus_required_roles),
                "signatures": consensus_check.get("consensus_payload", {}).get("signatures") or [],
                "consensus_hash": _to_text(consensus_check.get("consensus_hash") or ""),
                "consensus_complete": True,
            },
            "signatures": consensus_check.get("consensus_payload", {}).get("signatures") or [],
            "biometric_verification": biometric_check,
            "dual_pass_gate": dual_gate,
            "settlement_preconditions": preconditions,
            "component_utxo": component_verification,
            "final_proof_factors": final_proof_factors,
            "final_proof_ready": True,
        }
    )

    return {
        "next_proof_type": "payment",
        "tx_type": "settle",
        "next_state": merged_state,
        "biometric_check": biometric_check,
    }


__all__ = ["apply_settlement_confirm_transition"]
