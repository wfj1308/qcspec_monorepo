"""Shadow ledger packet helpers for TripRole execution."""

from __future__ import annotations

from typing import Any

from services.api.domain.execution.triprole_common import as_dict, to_text


def _build_shadow_packet(
    *,
    output_row: dict[str, Any],
    tx: dict[str, Any],
    action: str,
    did_gate: dict[str, Any] | None = None,
    credit_endorsement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state_data = as_dict(output_row.get("state_data"))
    return {
        "proof_id": to_text(output_row.get("proof_id") or "").strip(),
        "proof_hash": to_text(output_row.get("proof_hash") or "").strip(),
        "project_id": to_text(output_row.get("project_id") or "").strip(),
        "project_uri": to_text(output_row.get("project_uri") or "").strip(),
        "segment_uri": to_text(output_row.get("segment_uri") or "").strip(),
        "proof_type": to_text(output_row.get("proof_type") or "").strip(),
        "result": to_text(output_row.get("result") or "").strip(),
        "trip_action": to_text(state_data.get("trip_action") or action).strip(),
        "spatiotemporal_anchor_hash": to_text(state_data.get("spatiotemporal_anchor_hash") or "").strip(),
        "did_gate": as_dict(did_gate) if did_gate else as_dict(state_data.get("did_gate")),
        "credit_endorsement": as_dict(credit_endorsement) if credit_endorsement else as_dict(state_data.get("credit_endorsement")),
        "tx": {
            "tx_id": to_text(tx.get("tx_id") or "").strip(),
            "tx_type": to_text(tx.get("tx_type") or "").strip(),
            "trigger_action": to_text(tx.get("trigger_action") or "").strip(),
            "created_at": to_text(tx.get("created_at") or "").strip(),
        },
        "created_at": to_text(output_row.get("created_at") or "").strip(),
    }


__all__ = [
    "_build_shadow_packet",
]
