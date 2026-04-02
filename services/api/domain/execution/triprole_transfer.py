"""Asset transfer operation for TripRole execution."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.triprole_asset import (
    _resolve_ledger_balance,
    _resolve_transfer_input_row,
)
from services.api.domain.execution.triprole_common import (
    as_dict,
    as_list,
    sha256_json,
    to_float,
    to_text,
    utc_iso,
)
from services.api.domain.execution.integrations import ProofUTXOEngine
from services.api.domain.utxo.common import normalize_result


def transfer_asset(
    *,
    sb: Any,
    item_id: str,
    amount: float,
    executor_uri: str = "v://executor/system/",
    executor_role: str = "DOCPEG",
    docpeg_proof_id: str = "",
    docpeg_hash: str = "",
    metadata: dict[str, Any] | None = None,
    project_uri: str | None = None,
) -> dict[str, Any]:
    """
    Consume one BOQ-related UTXO and mint next UTXO with debited ledger balance.
    `item_id` can be a proof_id or boq_item_uri.
    """
    transfer_amount = to_float(amount)
    if transfer_amount is None or transfer_amount <= 0:
        raise HTTPException(400, "amount must be > 0")

    input_row = _resolve_transfer_input_row(sb=sb, item_id=item_id, project_uri=project_uri)
    if not input_row:
        raise HTTPException(404, "transfer input item not found")
    if bool(input_row.get("spent")):
        raise HTTPException(409, "transfer input already spent")

    balance = _resolve_ledger_balance(input_row)
    if transfer_amount > balance + 1e-9:
        raise HTTPException(409, f"insufficient_balance: balance={balance}, amount={transfer_amount}")
    remaining = max(0.0, float(balance - transfer_amount))

    engine = ProofUTXOEngine(sb)
    input_proof_id = to_text(input_row.get("proof_id") or "").strip()
    sd = as_dict(input_row.get("state_data"))
    ledger = dict(as_dict(sd.get("ledger")))
    prev_transferred = to_float(ledger.get("transferred_total")) or 0.0
    ledger.update(
        {
            "previous_balance": round(balance, 6),
            "current_balance": round(remaining, 6),
            "balance": round(remaining, 6),
            "transferred_total": round(prev_transferred + transfer_amount, 6),
            "last_transfer_at": utc_iso(),
            "last_transfer_amount": round(float(transfer_amount), 6),
            "last_transfer_docpeg_proof_id": to_text(docpeg_proof_id).strip(),
            "last_transfer_docpeg_hash": to_text(docpeg_hash).strip(),
        }
    )

    history = as_list(sd.get("transfer_history"))
    history.append(
        {
            "amount": round(float(transfer_amount), 6),
            "balance_after": round(remaining, 6),
            "executor_uri": to_text(executor_uri).strip(),
            "docpeg_proof_id": to_text(docpeg_proof_id).strip(),
            "docpeg_hash": to_text(docpeg_hash).strip(),
            "at": utc_iso(),
            "metadata": as_dict(metadata),
        }
    )
    if len(history) > 30:
        history = history[-30:]

    next_state = dict(sd)
    next_state.update(
        {
            "lifecycle_stage": "ASSET_TRANSFER",
            "status": "ASSET_TRANSFER",
            "ledger": ledger,
            "transfer_history": history,
            "transfer_hash": sha256_json(
                {
                    "input_proof_id": input_proof_id,
                    "amount": round(float(transfer_amount), 6),
                    "remaining": round(remaining, 6),
                    "docpeg_proof_id": to_text(docpeg_proof_id).strip(),
                    "docpeg_hash": to_text(docpeg_hash).strip(),
                }
            ),
        }
    )

    tx = engine.consume(
        input_proof_ids=[input_proof_id],
        output_states=[
            {
                "owner_uri": to_text(input_row.get("owner_uri") or executor_uri).strip(),
                "project_id": input_row.get("project_id"),
                "project_uri": to_text(input_row.get("project_uri") or "").strip(),
                "segment_uri": to_text(input_row.get("segment_uri") or "").strip(),
                "proof_type": to_text(input_row.get("proof_type") or "zero_ledger").strip() or "zero_ledger",
                "result": normalize_result(to_text(input_row.get("result") or "PASS")),
                "state_data": next_state,
                "conditions": as_list(input_row.get("conditions")),
                "parent_proof_id": input_proof_id,
                "norm_uri": to_text(input_row.get("norm_uri") or sd.get("norm_uri") or None) or None,
            }
        ],
        executor_uri=executor_uri,
        executor_role=executor_role,
        trigger_action="DocPeg.transfer_asset",
        trigger_data={
            "item_id": to_text(item_id).strip(),
            "input_proof_id": input_proof_id,
            "amount": round(float(transfer_amount), 6),
            "docpeg_proof_id": to_text(docpeg_proof_id).strip(),
            "docpeg_hash": to_text(docpeg_hash).strip(),
        },
        tx_type="consume",
    )

    output_ids = [to_text(x).strip() for x in as_list(tx.get("output_proofs")) if to_text(x).strip()]
    output_id = output_ids[0] if output_ids else ""
    output_row = engine.get_by_id(output_id) if output_id else None

    return {
        "ok": True,
        "item_id": to_text(item_id).strip(),
        "input_proof_id": input_proof_id,
        "output_proof_id": output_id,
        "balance_before": round(balance, 6),
        "amount": round(float(transfer_amount), 6),
        "balance_after": round(remaining, 6),
        "transfer_hash": to_text(as_dict(output_row.get("state_data") if isinstance(output_row, dict) else {}).get("transfer_hash") or "").strip(),
        "tx": tx,
    }


__all__ = [
    "transfer_asset",
]
