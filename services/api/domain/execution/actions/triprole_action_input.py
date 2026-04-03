"""Input preparation helpers for TripRole action execution."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import as_dict as _as_dict
from services.api.domain.execution.lineage.triprole_lineage import _is_leaf_boq_row
from services.api.domain.execution.offline.triprole_offline import (
    _resolve_existing_offline_result,
)
from services.api.domain.execution.actions.triprole_action_request import (
    build_triprole_replayed_response,
)
from services.api.domain.execution.integrations import ProofUTXOEngine


def prepare_triprole_action_input(
    *,
    sb: Any,
    action: str,
    input_proof_id: str,
    offline_packet_id: str,
    resolve_existing_offline_result_fn: Callable[..., dict[str, Any] | None] = _resolve_existing_offline_result,
    build_triprole_replayed_response_fn: Callable[..., dict[str, Any]] = build_triprole_replayed_response,
    is_leaf_boq_row_fn: Callable[[dict[str, Any]], bool] = _is_leaf_boq_row,
    proof_utxo_engine_cls: Callable[[Any], Any] = ProofUTXOEngine,
) -> dict[str, Any]:
    engine = proof_utxo_engine_cls(sb)

    if offline_packet_id:
        reused = resolve_existing_offline_result_fn(sb=sb, offline_packet_id=offline_packet_id)
        if reused:
            replayed_response = build_triprole_replayed_response_fn(
                action=action,
                offline_packet_id=offline_packet_id,
                reused=_as_dict(reused),
            )
            return {
                "engine": engine,
                "input_row": None,
                "replayed_response": replayed_response,
            }

    input_row = engine.get_by_id(input_proof_id)
    if not input_row:
        raise HTTPException(404, "input proof_utxo not found")
    if not is_leaf_boq_row_fn(input_row):
        raise HTTPException(409, f"{action} is only allowed for leaf BOQ nodes")

    return {
        "engine": engine,
        "input_row": input_row,
        "replayed_response": None,
    }


__all__ = ["prepare_triprole_action_input"]
