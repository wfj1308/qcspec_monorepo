"""Transition prechecks for TripRole actions."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import to_text as _to_text
from services.api.domain.execution.triprole_lineage import _stage_from_row


def validate_transition(
    action: str,
    input_row: dict[str, Any],
    stage_from_row_fn: Callable[[dict[str, Any]], str] = _stage_from_row,
) -> None:
    if bool(input_row.get("spent")):
        raise HTTPException(409, "input_proof already spent")

    stage = stage_from_row_fn(input_row)
    result = _to_text(input_row.get("result") or "").strip().upper()

    if action == "quality.check" and stage not in {"INITIAL", "UNKNOWN"}:
        raise HTTPException(409, f"quality.check expects INITIAL input, got {stage}")

    if action == "measure.record" and stage not in {"ENTRY", "VARIATION"}:
        raise HTTPException(409, f"measure.record expects ENTRY/VARIATION input, got {stage}")
    if action == "measure.record" and stage == "ENTRY" and result != "PASS":
        raise HTTPException(409, "measure.record requires quality.check PASS or variation compensation")

    if action == "variation.record" and result != "FAIL":
        raise HTTPException(409, "variation.record requires FAIL input")

    if action == "settlement.confirm" and stage not in {"INSTALLATION", "VARIATION"}:
        raise HTTPException(409, f"settlement.confirm expects INSTALLATION/VARIATION input, got {stage}")
    if action == "dispute.resolve":
        ptype = _to_text(input_row.get("proof_type") or "").strip().lower()
        if ptype != "dispute":
            raise HTTPException(409, f"dispute.resolve expects dispute input, got {ptype or '-'}")


__all__ = ["validate_transition"]
