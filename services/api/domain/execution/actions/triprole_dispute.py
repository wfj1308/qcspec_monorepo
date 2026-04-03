"""Dispute-proof helpers for TripRole execution."""

from __future__ import annotations

from typing import Any

from services.api.domain.execution.triprole_common import sha256_json, to_text, utc_iso
from services.api.domain.execution.integrations import ProofUTXOEngine


def create_consensus_dispute(
    *,
    sb: Any,
    input_row: dict[str, Any],
    project_uri: str,
    boq_item_uri: str,
    executor_uri: str,
    conflict: dict[str, Any],
    consensus_signatures: list[dict[str, Any]],
    signer_metadata: dict[str, Any],
) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    input_id = to_text(input_row.get("proof_id") or "").strip()
    now_iso = utc_iso()
    state_data = {
        "doc_type": "consensus_dispute",
        "status": "DISPUTE",
        "lifecycle_stage": "DISPUTE",
        "trip_action": "consensus.dispute",
        "boq_item_uri": boq_item_uri,
        "project_uri": project_uri,
        "source_proof_id": input_id,
        "conflict": conflict,
        "consensus_signatures": consensus_signatures,
        "signer_metadata": signer_metadata,
        "locked": True,
        "created_at": now_iso,
    }
    proof_id = f"GP-DSPT-{sha256_json(state_data)[:16].upper()}"
    try:
        row = engine.create(
            proof_id=proof_id,
            owner_uri=to_text(executor_uri).strip() or "v://executor/system/",
            project_uri=project_uri,
            project_id=to_text(input_row.get("project_id") or "").strip() or None,
            segment_uri=boq_item_uri,
            proof_type="dispute",
            result="FAIL",
            state_data=state_data,
            conditions=[],
            parent_proof_id=input_id or None,
            norm_uri="v://norm/CoordOS/Consensus/1.0#dispute",
            signer_uri=to_text(executor_uri).strip() or "v://executor/system/",
            signer_role="ARBITER",
        )
        return {"ok": True, "proof_id": to_text(row.get("proof_id") or proof_id).strip()}
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}


__all__ = [
    "create_consensus_dispute",
]
