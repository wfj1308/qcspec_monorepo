"""Shared helpers for BOQ item sovereign history/reconciliation logic."""

from __future__ import annotations

from typing import Any

from services.api.domain.boq.runtime.audit_common import (
    as_dict,
    as_list,
    extract_boq_item_uri,
    item_code_from_boq_uri,
    to_float as common_to_float,
    to_text,
)


def extract_item_code(row: dict[str, Any]) -> str:
    sd = as_dict(row.get("state_data"))
    code = to_text(sd.get("item_no") or "").strip()
    if code:
        return code
    return item_code_from_boq_uri(extract_boq_item_uri(row))


def extract_settled_quantity(row: dict[str, Any]) -> float:
    sd = as_dict(row.get("state_data"))
    settlement = as_dict(sd.get("settlement"))
    for candidate in (
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        settlement.get("confirmed_quantity"),
        settlement.get("approved_quantity"),
        sd.get("settled_quantity"),
    ):
        v = common_to_float(candidate, allow_commas=True)
        if v is not None:
            return float(v)
    return 0.0


def extract_variation_delta(row: dict[str, Any]) -> float:
    sd = as_dict(row.get("state_data"))
    delta = common_to_float(as_dict(sd.get("delta_utxo")).get("delta_amount"), allow_commas=True)
    if delta is None:
        delta = common_to_float(as_dict(sd.get("variation")).get("delta_amount"), allow_commas=True)
    if delta is None:
        delta = common_to_float(as_dict(sd.get("ledger")).get("last_delta_amount"), allow_commas=True)
    return float(delta or 0.0)


def is_initial_row(row: dict[str, Any]) -> bool:
    sd = as_dict(row.get("state_data"))
    lifecycle = to_text(sd.get("lifecycle_stage") or "").strip().upper()
    status = to_text(sd.get("status") or "").strip().upper()
    ptype = to_text(row.get("proof_type") or "").strip().lower()
    if lifecycle == "INITIAL" or status == "INITIAL":
        return True
    return ptype == "zero_ledger"


def is_variation_row(row: dict[str, Any]) -> bool:
    sd = as_dict(row.get("state_data"))
    action = to_text(sd.get("trip_action") or "").strip().lower()
    lifecycle = to_text(sd.get("lifecycle_stage") or "").strip().upper()
    return action == "variation.delta.apply" or lifecycle == "VARIATION" or bool(as_dict(sd.get("delta_utxo")))


def is_settlement_row(row: dict[str, Any]) -> bool:
    sd = as_dict(row.get("state_data"))
    ptype = to_text(row.get("proof_type") or "").strip().lower()
    action = to_text(sd.get("trip_action") or "").strip().lower()
    lifecycle = to_text(sd.get("lifecycle_stage") or "").strip().upper()
    return ptype == "payment" or action == "settlement.confirm" or lifecycle == "SETTLEMENT"


def is_document_row(row: dict[str, Any]) -> bool:
    ptype = to_text(row.get("proof_type") or "").strip().lower()
    if ptype in {"document", "photo", "erpnext_receipt"}:
        return True
    sd = as_dict(row.get("state_data"))
    return bool(to_text(sd.get("doc_type") or "").strip())


def source_utxo_refs(row: dict[str, Any]) -> list[str]:
    sd = as_dict(row.get("state_data"))
    refs: list[str] = []
    direct = to_text(sd.get("source_utxo_id") or "").strip()
    if direct:
        refs.append(direct)
    refs.extend([to_text(x).strip() for x in as_list(sd.get("source_utxo_ids")) if to_text(x).strip()])
    refs.extend([to_text(x).strip() for x in as_list(sd.get("compensates")) if to_text(x).strip()])
    return sorted(set(refs))
