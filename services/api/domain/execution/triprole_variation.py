"""Variation apply operation for TripRole execution."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.integrations import (
    ProofUTXOEngine,
    calculate_sovereign_credit,
    resolve_required_credential,
    sync_to_mirrors,
    verify_credential,
)
from services.api.domain.execution.triprole_asset import (
    _compute_delta_merge,
    _resolve_transfer_input_row,
)
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    sha256_json as _sha256_json,
    to_text as _to_text,
    utc_iso as _utc_iso,
)
from services.api.domain.execution.triprole_geo_sensor import (
    build_spatiotemporal_anchor as _build_spatiotemporal_anchor,
)
from services.api.domain.execution.triprole_lineage import _is_leaf_boq_row
from services.api.domain.execution.triprole_offline import _resolve_existing_offline_result
from services.api.domain.execution.triprole_shadow import _build_shadow_packet
from services.api.domain.execution.triprole_writeback import _patch_state_data_fields
from services.api.domain.utxo.common import (
    gen_tx_id as _gen_tx_id,
    ordosign as _ordosign,
)


def apply_variation(
    *,
    sb: Any,
    boq_item_uri: str,
    delta_amount: float,
    reason: str = "",
    project_uri: str | None = None,
    executor_uri: str = "v://executor/system/",
    executor_did: str = "",
    executor_role: str = "TRIPROLE",
    offline_packet_id: str = "",
    metadata: dict[str, Any] | None = None,
    credentials_vc: list[dict[str, Any]] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_boq_item_uri = _to_text(boq_item_uri).strip()
    if not normalized_boq_item_uri.startswith("v://"):
        raise HTTPException(400, "boq_item_uri is required and must start with v://")
    normalized_offline_packet_id = _to_text(offline_packet_id).strip()
    if normalized_offline_packet_id:
        reused = _resolve_existing_offline_result(sb=sb, offline_packet_id=normalized_offline_packet_id)
        if reused:
            return {
                "ok": True,
                "replayed": True,
                "boq_item_uri": reused.get("boq_item_uri") or normalized_boq_item_uri,
                "output_proof_id": reused.get("output_proof_id") or "",
                "proof_hash": reused.get("proof_hash") or "",
                "did_gate": reused.get("did_gate") or {},
                "credit_endorsement": reused.get("credit_endorsement") or {},
                "mirror_sync": reused.get("mirror_sync") or {},
                "spatiotemporal_anchor_hash": reused.get("spatiotemporal_anchor_hash") or "",
                "available_balance": reused.get("available_balance"),
                "offline_packet_id": normalized_offline_packet_id,
                "tx": {
                    "tx_id": reused.get("tx_id") or "",
                    "tx_type": reused.get("tx_type") or "",
                    "status": reused.get("tx_status") or "success",
                    "reused": True,
                },
            }

    input_row = _resolve_transfer_input_row(sb=sb, item_id=normalized_boq_item_uri, project_uri=project_uri)
    if not input_row:
        raise HTTPException(404, "no unspent UTXO found for boq_item_uri")
    if bool(input_row.get("spent")):
        raise HTTPException(409, "input_proof already spent")
    if not _is_leaf_boq_row(input_row):
        raise HTTPException(409, "apply_variation is only allowed for leaf BOQ nodes")

    input_proof_id = _to_text(input_row.get("proof_id") or "").strip()
    if not input_proof_id:
        raise HTTPException(500, "invalid input proof row")
    normalized_project_uri = _to_text(input_row.get("project_uri") or project_uri or "").strip()
    normalized_executor_did = _to_text(executor_did).strip()
    required_credential = resolve_required_credential(
        action="variation.delta.apply",
        boq_item_uri=normalized_boq_item_uri,
        payload=_as_dict(metadata),
    )
    did_gate = verify_credential(
        sb=sb,
        user_did=normalized_executor_did,
        required_credential=required_credential,
        project_uri=normalized_project_uri,
        boq_item_uri=normalized_boq_item_uri,
        payload_credentials=credentials_vc,
    )
    if not bool(did_gate.get("ok")):
        raise HTTPException(
            403,
            f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
        )

    now_iso = _utc_iso()
    anchor = _build_spatiotemporal_anchor(
        action="variation.delta.apply",
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        now_iso=now_iso,
        geo_location_raw=geo_location,
        server_timestamp_raw=server_timestamp_proof,
    )
    merge = _compute_delta_merge(input_row=input_row, delta_amount=float(delta_amount))

    input_sd = _as_dict(input_row.get("state_data"))
    base_ledger = dict(_as_dict(input_sd.get("ledger")))
    base_ledger.update(
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
            "last_delta_reason": _to_text(reason).strip(),
            "last_delta_at": now_iso,
            "last_delta_executor_uri": _to_text(executor_uri).strip(),
        }
    )

    variation_entry = {
        "delta_amount": merge["delta_amount"],
        "reason": _to_text(reason).strip() or "variation_instruction",
        "mode": "delta_utxo_fork",
        "applied_at": now_iso,
        "executor_uri": _to_text(executor_uri).strip(),
        "source_input_proof_id": input_proof_id,
        "merged_total_after": merge["merged_total_after"],
        "balance_after": merge["balance_after"],
        "metadata": _as_dict(metadata),
    }
    variation_history = _as_list(input_sd.get("variation_history"))
    variation_history.append(variation_entry)
    if len(variation_history) > 50:
        variation_history = variation_history[-50:]

    next_state = dict(input_sd)
    next_state.update(
        {
            "trip_action": "variation.delta.apply",
            "trip_executor": _to_text(executor_uri).strip(),
            "executor_did": normalized_executor_did,
            "trip_executed_at": now_iso,
            "parent_proof_id": input_proof_id,
            "parent_hash": _to_text(input_row.get("proof_hash") or "").strip(),
            "lifecycle_stage": "VARIATION",
            "status": "VARIATION",
            "boq_item_uri": normalized_boq_item_uri,
            "variation": variation_entry,
            "delta_utxo": {
                "delta_amount": merge["delta_amount"],
                "reason": variation_entry["reason"],
                "merge_strategy": "fork_delta_then_aggregate",
                "parent_proof_id": input_proof_id,
                "merged_total_before": merge["merged_total_before"],
                "merged_total_after": merge["merged_total_after"],
                "previous_balance": merge["previous_balance"],
                "balance_after": merge["balance_after"],
                "approved_total_with_deltas": merge["merged_total_after"],
            },
            "variation_history": variation_history,
            "did_gate": did_gate,
            "available_quantity": merge["balance_after"],
            "remaining_quantity": merge["balance_after"],
            "ledger": base_ledger,
            "compensates": [input_proof_id],
            "source_fail_proof_id": input_proof_id if _to_text(input_row.get("result") or "").strip().upper() == "FAIL" else "",
            "variation_hash": _sha256_json(
                {
                    "input_proof_id": input_proof_id,
                    "delta_amount": merge["delta_amount"],
                    "reason": variation_entry["reason"],
                    "anchor": anchor,
                    "metadata": _as_dict(metadata),
                }
            ),
            **anchor,
        }
    )

    engine = ProofUTXOEngine(sb)
    output_id = f"GP-PROOF-{uuid.uuid4().hex[:16].upper()}"
    created = engine.create(
        proof_id=output_id,
        owner_uri=_to_text(input_row.get("owner_uri") or executor_uri).strip(),
        project_id=input_row.get("project_id"),
        project_uri=_to_text(input_row.get("project_uri") or "").strip(),
        segment_uri=_to_text(input_row.get("segment_uri") or normalized_boq_item_uri).strip(),
        proof_type="archive",
        result="PASS",
        state_data=next_state,
        conditions=_as_list(input_row.get("conditions")),
        parent_proof_id=input_proof_id,
        norm_uri=_to_text(input_row.get("norm_uri") or input_sd.get("norm_uri") or None) or None,
        signer_uri=_to_text(executor_uri).strip(),
        signer_role=_to_text(executor_role).strip() or "TRIPROLE",
        created_at=now_iso,
    )
    output_id = _to_text(created.get("proof_id") or output_id).strip()
    output_row = engine.get_by_id(output_id) if output_id else None

    tx = {
        "tx_id": _gen_tx_id(),
        "tx_type": "fork",
        "tx_semantics": "fork_delta_utxo",
        "input_proofs": [input_proof_id],
        "output_proofs": [output_id] if output_id else [],
        "trigger_action": "TripRole.apply_variation.fork",
        "trigger_data": {
            "boq_item_uri": normalized_boq_item_uri,
            "delta_amount": merge["delta_amount"],
            "reason": variation_entry["reason"],
            "source_input_proof_id": input_proof_id,
            "executor_did": normalized_executor_did,
            "did_gate_hash": _to_text(did_gate.get("did_gate_hash") or "").strip(),
            "required_credential": _to_text(did_gate.get("required_credential") or "").strip(),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "offline_packet_id": normalized_offline_packet_id,
        },
        "executor_uri": _to_text(executor_uri).strip(),
        "ordosign_hash": "",
        "status": "success",
        "error_msg": None,
        "created_at": now_iso,
    }
    tx["ordosign_hash"] = _ordosign(_to_text(tx.get("tx_id") or "").strip(), _to_text(executor_uri).strip())
    try:
        sb.table("proof_transaction").insert(
            {
                "tx_id": tx["tx_id"],
                "tx_type": tx["tx_type"],
                "input_proofs": tx["input_proofs"],
                "output_proofs": tx["output_proofs"],
                "trigger_action": tx["trigger_action"],
                "trigger_data": tx["trigger_data"],
                "executor_uri": tx["executor_uri"],
                "ordosign_hash": tx["ordosign_hash"],
                "status": tx["status"],
                "error_msg": tx["error_msg"],
                "created_at": tx["created_at"],
            }
        ).execute()
    except Exception:
        tx["persisted"] = False
    else:
        tx["persisted"] = True
    credit_endorsement: dict[str, Any] = {}
    mirror_sync: dict[str, Any] = {}
    if isinstance(output_row, dict):
        try:
            credit_endorsement = calculate_sovereign_credit(
                sb=sb,
                project_uri=normalized_project_uri,
                participant_did=normalized_executor_did,
            )
        except Exception:
            credit_endorsement = {}
        try:
            shadow_packet = _build_shadow_packet(
                output_row=output_row,
                tx=tx,
                action="variation.delta.apply",
                did_gate=did_gate,
                credit_endorsement=credit_endorsement,
            )
            mirror_sync = sync_to_mirrors(
                proof_packet=shadow_packet,
                sb=sb,
                project_id=_to_text(output_row.get("project_id") or "").strip(),
                project_uri=_to_text(output_row.get("project_uri") or "").strip(),
            )
        except Exception:
            mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}
        patched_state = _patch_state_data_fields(
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
        "boq_item_uri": normalized_boq_item_uri,
        "input_proof_id": input_proof_id,
        "output_proof_id": output_id,
        "delta_amount": merge["delta_amount"],
        "merged_total_after": merge["merged_total_after"],
        "available_balance": merge["balance_after"],
        "variation_mode": "fork_delta_utxo",
        "did_gate": did_gate,
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
        "offline_packet_id": normalized_offline_packet_id,
        "proof_hash": _to_text((output_row or {}).get("proof_hash") or "").strip(),
        "tx": tx,
    }


__all__ = [
    "apply_variation",
]
