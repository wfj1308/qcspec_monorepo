"""Settlement-confirm transition helpers for TripRole execution."""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    safe_path_token as _safe_path_token,
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
        }
    )

    return {
        "next_proof_type": "payment",
        "tx_type": "settle",
        "next_state": merged_state,
        "biometric_check": biometric_check,
    }


__all__ = ["apply_settlement_confirm_transition"]
