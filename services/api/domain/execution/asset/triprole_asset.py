"""Asset transfer and variation helpers for TripRole execution."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import as_dict, to_float, to_text
from services.api.domain.execution.integrations import ProofUTXOEngine


def _resolve_latest_boq_row(
    *,
    sb: Any,
    boq_item_uri: str,
    project_uri: str | None = None,
) -> dict[str, Any] | None:
    normalized = to_text(boq_item_uri).strip()
    if not normalized:
        return None
    scoped_project_uri = to_text(project_uri or "").strip()
    try:
        q = sb.table("proof_utxo").select("*").filter("state_data->>boq_item_uri", "eq", normalized)
        if scoped_project_uri:
            q = q.eq("project_uri", scoped_project_uri)
        rows = q.order("created_at", desc=True).limit(1).execute().data or []
        if rows:
            return rows[0]
    except Exception:
        pass
    try:
        q = sb.table("proof_utxo").select("*").eq("segment_uri", normalized)
        if scoped_project_uri:
            q = q.eq("project_uri", scoped_project_uri)
        rows = q.order("created_at", desc=True).limit(1).execute().data or []
        if rows:
            return rows[0]
    except Exception:
        pass
    return None


def _resolve_transfer_input_row(*, sb: Any, item_id: str, project_uri: str | None = None) -> dict[str, Any] | None:
    normalized = to_text(item_id).strip()
    if not normalized:
        return None
    scoped_project_uri = to_text(project_uri or "").strip()

    engine = ProofUTXOEngine(sb)
    if normalized.upper().startswith("GP-"):
        row = engine.get_by_id(normalized)
        if row and scoped_project_uri and to_text(row.get("project_uri") or "").strip() != scoped_project_uri:
            return None
        return row

    try:
        q = sb.table("proof_utxo").select("*").eq("spent", False).filter("state_data->>boq_item_uri", "eq", normalized)
        if scoped_project_uri:
            q = q.eq("project_uri", scoped_project_uri)
        rows = q.order("created_at", desc=True).limit(1).execute().data or []
        if rows:
            return rows[0]
    except Exception:
        pass

    # fallback scan for old records without JSON index
    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("spent", False)
            .order("created_at", desc=True)
            .limit(5000)
            .execute()
            .data
            or []
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            if scoped_project_uri and to_text(row.get("project_uri") or "").strip() != scoped_project_uri:
                continue
            sd = as_dict(row.get("state_data"))
            if to_text(sd.get("boq_item_uri") or sd.get("item_uri") or sd.get("boq_uri") or "").strip() == normalized:
                return row
    except Exception:
        return None
    return None


def _resolve_ledger_balance(row: dict[str, Any]) -> float:
    sd = as_dict(row.get("state_data"))
    ledger = as_dict(sd.get("ledger"))
    for candidate in (
        ledger.get("current_balance"),
        ledger.get("remaining_balance"),
        ledger.get("balance"),
        sd.get("remaining_quantity"),
        sd.get("available_quantity"),
        sd.get("design_quantity"),
        ledger.get("initial_balance"),
    ):
        num = to_float(candidate)
        if num is not None:
            return max(0.0, float(num))
    return 0.0


def _resolve_genesis_balance(row: dict[str, Any]) -> float:
    sd = as_dict(row.get("state_data"))
    ledger = as_dict(sd.get("ledger"))
    for candidate in (
        ledger.get("initial_balance"),
        sd.get("design_quantity"),
        as_dict(sd.get("genesis_proof")).get("initial_quantity"),
        _resolve_ledger_balance(row),
    ):
        num = to_float(candidate)
        if num is not None:
            return float(num)
    return 0.0


def _extract_variation_delta_amount(payload: dict[str, Any]) -> float | None:
    for key in ("delta_amount", "delta_quantity", "quantity_delta", "change_amount"):
        val = to_float(payload.get(key))
        if val is not None:
            return float(val)
    return None


def _compute_delta_merge(
    *,
    input_row: dict[str, Any],
    delta_amount: float,
) -> dict[str, Any]:
    if abs(float(delta_amount)) <= 1e-9:
        raise HTTPException(400, "delta_amount must not be zero")

    sd = as_dict(input_row.get("state_data"))
    ledger = as_dict(sd.get("ledger"))
    current_balance = _resolve_ledger_balance(input_row)
    initial_balance = _resolve_genesis_balance(input_row)
    delta_total_prev = to_float(ledger.get("delta_total")) or 0.0
    merged_total_prev = to_float(ledger.get("merged_total"))
    if merged_total_prev is None:
        merged_total_prev = float(initial_balance + delta_total_prev)

    transferred_total = to_float(ledger.get("transferred_total"))
    if transferred_total is None:
        transferred_total = max(0.0, float(merged_total_prev - current_balance))

    merged_total = float(merged_total_prev + delta_amount)
    balance_after = float(merged_total - transferred_total)
    if balance_after < -1e-9:
        raise HTTPException(
            409,
            f"delta underflow: balance_after={balance_after:.6f}; delta_amount={delta_amount:.6f}",
        )
    delta_total_after = float(delta_total_prev + delta_amount)

    return {
        "delta_amount": round(float(delta_amount), 6),
        "previous_balance": round(float(current_balance), 6),
        "balance_after": round(max(0.0, balance_after), 6),
        "initial_balance": round(float(initial_balance), 6),
        "transferred_total": round(float(transferred_total), 6),
        "delta_total_before": round(float(delta_total_prev), 6),
        "delta_total_after": round(float(delta_total_after), 6),
        "merged_total_before": round(float(merged_total_prev), 6),
        "merged_total_after": round(float(merged_total), 6),
    }


__all__ = [
    "_resolve_latest_boq_row",
    "_resolve_transfer_input_row",
    "_resolve_ledger_balance",
    "_resolve_genesis_balance",
    "_extract_variation_delta_amount",
    "_compute_delta_merge",
]
