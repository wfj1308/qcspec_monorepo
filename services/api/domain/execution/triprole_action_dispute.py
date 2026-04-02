"""Dispute-resolve transition helper for TripRole execution."""

from __future__ import annotations

from typing import Any

from services.api.domain.execution.triprole_common import (
    sha256_json as _sha256_json,
    to_text as _to_text,
)
from services.api.domain.utxo.common import normalize_result as _normalize_result


def apply_dispute_resolve_transition(
    *,
    payload: dict[str, Any],
    override_result: str,
    now_iso: str,
    next_state: dict[str, Any],
) -> dict[str, Any]:
    next_result = _normalize_result(override_result or _to_text(payload.get("result") or "PASS"))
    resolution_payload = dict(payload)
    resolution_payload["resolved_at"] = now_iso

    merged_state = dict(next_state)
    merged_state.update(
        {
            "lifecycle_stage": "DISPUTE_RESOLUTION",
            "status": "RESOLVED" if next_result == "PASS" else "REJECTED",
            "resolution": resolution_payload,
            "resolution_hash": _sha256_json(resolution_payload),
        }
    )

    return {
        "next_proof_type": "dispute_resolution",
        "next_result": next_result,
        "next_state": merged_state,
    }


__all__ = ["apply_dispute_resolve_transition"]
