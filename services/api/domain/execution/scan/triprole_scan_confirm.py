"""Scan-confirm signature execution flow for TripRole."""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    normalize_role as _normalize_role,
    to_text as _to_text,
    utc_iso as _utc_iso,
)
from services.api.domain.execution.actions.triprole_consensus import (
    _looks_like_sig_hash,
    _normalize_consensus_signatures,
    _normalize_signer_metadata,
    _validate_consensus_signatures,
)
from services.api.domain.execution.geo.triprole_geo_sensor import (
    build_spatiotemporal_anchor as _build_spatiotemporal_anchor,
)
from services.api.domain.execution.scan.triprole_scan import (
    validate_scan_confirm_payload as _validate_scan_confirm_payload,
)
from services.api.domain.execution.asset.triprole_shadow import (
    _build_shadow_packet,
)
from services.api.domain.execution.asset.triprole_writeback import (
    _patch_state_data_fields,
)
from services.api.domain.execution.integrations import (
    ProofUTXOEngine,
    calculate_sovereign_credit,
    sync_to_mirrors,
)
from services.api.domain.utxo.common import normalize_result as _normalize_result


def execute_scan_confirm_signature(
    *,
    sb: Any,
    input_proof_id: str,
    scan_payload: Any,
    scanner_did: str,
    scanner_role: str,
    executor_uri: str = "v://executor/system/",
    executor_role: str = "SUPERVISOR",
    signature_hash: str = "",
    signer_metadata: dict[str, Any] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
    consensus_required_roles: tuple[str, ...] = ("contractor", "supervisor", "owner"),
    proof_utxo_engine_cls: Callable[[Any], Any] = ProofUTXOEngine,
    validate_scan_confirm_payload_fn: Callable[[Any], dict[str, Any]] = _validate_scan_confirm_payload,
    normalize_role_fn: Callable[[Any], str] = _normalize_role,
    utc_iso_fn: Callable[[], str] = _utc_iso,
    build_spatiotemporal_anchor_fn: Callable[..., dict[str, Any]] = _build_spatiotemporal_anchor,
    normalize_consensus_signatures_fn: Callable[[Any], list[dict[str, Any]]] = _normalize_consensus_signatures,
    looks_like_sig_hash_fn: Callable[[str], bool] = _looks_like_sig_hash,
    validate_consensus_signatures_fn: Callable[[Any], dict[str, Any]] = _validate_consensus_signatures,
    normalize_signer_metadata_fn: Callable[[Any], dict[str, Any]] = _normalize_signer_metadata,
    normalize_result_fn: Callable[[str], str] = _normalize_result,
    calculate_sovereign_credit_fn: Callable[..., dict[str, Any]] = calculate_sovereign_credit,
    sync_to_mirrors_fn: Callable[..., dict[str, Any]] = sync_to_mirrors,
    build_shadow_packet_fn: Callable[..., dict[str, Any]] = _build_shadow_packet,
    patch_state_data_fields_fn: Callable[..., dict[str, Any]] = _patch_state_data_fields,
) -> dict[str, Any]:
    proof_id = _to_text(input_proof_id).strip()
    if not proof_id:
        raise HTTPException(400, "input_proof_id is required")
    normalized_scanner_did = _to_text(scanner_did).strip()
    if not normalized_scanner_did.startswith("did:"):
        raise HTTPException(400, "scanner_did must start with did:")
    normalized_scanner_role = normalize_role_fn(scanner_role) or _to_text(scanner_role).strip().lower()
    if not normalized_scanner_role:
        raise HTTPException(400, "scanner_role is required")

    payload = validate_scan_confirm_payload_fn(scan_payload)
    if _to_text(payload.get("proof_id") or "").strip() != proof_id:
        raise HTTPException(409, "scan payload proof_id mismatch")

    engine = proof_utxo_engine_cls(sb)
    input_row = engine.get_by_id(proof_id)
    if not input_row:
        raise HTTPException(404, "input proof_utxo not found")
    if bool(input_row.get("spent")):
        raise HTTPException(409, "input_proof already spent")

    now_iso = utc_iso_fn()
    anchor = build_spatiotemporal_anchor_fn(
        action="scan.confirm",
        input_proof_id=proof_id,
        executor_uri=executor_uri,
        now_iso=now_iso,
        geo_location_raw=geo_location,
        server_timestamp_raw=server_timestamp_proof,
    )

    input_sd = _as_dict(input_row.get("state_data"))
    signatures = normalize_consensus_signatures_fn(_as_list(_as_dict(input_sd.get("consensus")).get("signatures")))
    if not signatures:
        signatures = normalize_consensus_signatures_fn(input_sd.get("signatures"))

    if not looks_like_sig_hash_fn(signature_hash):
        signature_hash = hashlib.sha256(
            f"{proof_id}|{normalized_scanner_did}|{normalized_scanner_role}|{payload.get('token_hash')}|{now_iso}".encode(
                "utf-8"
            )
        ).hexdigest()

    by_role: dict[str, dict[str, Any]] = {}
    for sig in signatures:
        role = normalize_role_fn(sig.get("role"))
        if role:
            by_role[role] = sig
    by_role[normalized_scanner_role] = {
        "role": normalized_scanner_role,
        "did": normalized_scanner_did,
        "signature_hash": signature_hash,
        "signed_at": now_iso,
        "mode": "scan_confirm",
    }
    next_signatures = [by_role[r] for r in sorted(by_role.keys())]
    consensus_check = validate_consensus_signatures_fn(next_signatures)

    scan_record = {
        "scan_at": now_iso,
        "input_proof_id": proof_id,
        "scanner_role": normalized_scanner_role,
        "scanner_did": normalized_scanner_did,
        "scanned_signer_role": _to_text(payload.get("signer_role") or "").strip(),
        "scanned_signer_did": _to_text(payload.get("signer_did") or "").strip(),
        "token_hash": _to_text(payload.get("token_hash") or "").strip(),
        "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
    }
    scan_history = _as_list(input_sd.get("scan_confirmations"))
    scan_history.append(scan_record)
    if len(scan_history) > 50:
        scan_history = scan_history[-50:]
    normalized_signer_metadata = normalize_signer_metadata_fn(signer_metadata or {})

    next_state = dict(input_sd)
    next_state.update(
        {
            "trip_action": "scan.confirm",
            "trip_executor": _to_text(executor_uri).strip(),
            "trip_executed_at": now_iso,
            "parent_proof_id": proof_id,
            "parent_hash": _to_text(input_row.get("proof_hash") or "").strip(),
            "scan_confirmation": scan_record,
            "scan_confirmations": scan_history,
            "consensus": {
                "required_roles": list(consensus_required_roles),
                "signatures": next_signatures,
                "consensus_hash": _to_text(consensus_check.get("consensus_hash") or ""),
                "consensus_complete": bool(consensus_check.get("ok")),
                "missing_roles": consensus_check.get("missing_roles") or [],
                "invalid": consensus_check.get("invalid") or [],
            },
            "signatures": next_signatures,
            **anchor,
        }
    )
    if _as_list(normalized_signer_metadata.get("signers")):
        next_state["signer_metadata"] = normalized_signer_metadata

    tx = engine.consume(
        input_proof_ids=[proof_id],
        output_states=[
            {
                "owner_uri": _to_text(input_row.get("owner_uri") or executor_uri).strip(),
                "project_id": input_row.get("project_id"),
                "project_uri": _to_text(input_row.get("project_uri") or "").strip(),
                "segment_uri": _to_text(input_row.get("segment_uri") or "").strip(),
                "proof_type": _to_text(input_row.get("proof_type") or "approval").strip() or "approval",
                "result": normalize_result_fn(_to_text(input_row.get("result") or "PENDING")),
                "state_data": next_state,
                "conditions": _as_list(input_row.get("conditions")),
                "parent_proof_id": proof_id,
                "norm_uri": _to_text(input_row.get("norm_uri") or input_sd.get("norm_uri") or None) or None,
            }
        ],
        executor_uri=_to_text(executor_uri).strip() or "v://executor/system/",
        executor_role=_to_text(executor_role).strip() or "SUPERVISOR",
        trigger_action="TripRole.scan_confirm",
        trigger_data={
            "input_proof_id": proof_id,
            "scanner_role": normalized_scanner_role,
            "scanner_did": normalized_scanner_did,
            "scanned_signer_role": _to_text(payload.get("signer_role") or "").strip(),
            "scanned_signer_did": _to_text(payload.get("signer_did") or "").strip(),
            "scan_token_hash": _to_text(payload.get("token_hash") or "").strip(),
            "biometric_metadata_hash": _to_text(normalized_signer_metadata.get("metadata_hash") or "").strip(),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
        },
        tx_type="consume",
    )

    output_ids = [_to_text(x).strip() for x in _as_list(tx.get("output_proofs")) if _to_text(x).strip()]
    output_id = output_ids[0] if output_ids else ""
    output_row = engine.get_by_id(output_id) if output_id else None
    credit_endorsement: dict[str, Any] = {}
    mirror_sync: dict[str, Any] = {}
    if isinstance(output_row, dict):
        try:
            credit_endorsement = calculate_sovereign_credit_fn(
                sb=sb,
                project_uri=_to_text(output_row.get("project_uri") or "").strip(),
                participant_did=normalized_scanner_did,
            )
        except Exception:
            credit_endorsement = {}
        try:
            mirror_sync = sync_to_mirrors_fn(
                proof_packet=build_shadow_packet_fn(
                    output_row=output_row,
                    tx=tx,
                    action="scan.confirm",
                    did_gate={
                        "ok": True,
                        "user_did": normalized_scanner_did,
                        "required_credential": "scan_confirm_signatory",
                        "source": "scan_confirm",
                    },
                    credit_endorsement=credit_endorsement,
                ),
                sb=sb,
                project_id=_to_text(output_row.get("project_id") or "").strip(),
                project_uri=_to_text(output_row.get("project_uri") or "").strip(),
            )
        except Exception:
            mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}
        patched_state = patch_state_data_fields_fn(
            sb=sb,
            proof_id=output_id,
            patch={
                "credit_endorsement": credit_endorsement,
                "shadow_mirror_sync": mirror_sync,
            },
        )
        output_row["state_data"] = patched_state
    return {
        "ok": True,
        "input_proof_id": proof_id,
        "output_proof_id": output_id,
        "proof_hash": _to_text((output_row or {}).get("proof_hash") or "").strip(),
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "consensus_complete": bool(consensus_check.get("ok")),
        "missing_roles": consensus_check.get("missing_roles") or [],
        "invalid": consensus_check.get("invalid") or [],
        "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
        "tx": tx,
    }


__all__ = ["execute_scan_confirm_signature"]
