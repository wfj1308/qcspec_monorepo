"""Realtime BOQ status aggregation helpers."""

from __future__ import annotations

import re
from typing import Any, Callable

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    to_float as _to_float,
    to_text as _to_text,
)
from services.api.domain.execution.triprole_lineage import (
    _boq_item_from_row,
    _effective_design_quantity,
    _extract_settled_quantity,
    _is_leaf_boq_row,
    _item_no_from_boq_uri,
)


def build_boq_realtime_status(
    *,
    rows: list[dict[str, Any]],
    project_uri: str,
    aggregate_provenance_chain_fn: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_leaf_boq_row(row):
            continue
        boq_item_uri = _boq_item_from_row(row)
        if not boq_item_uri.startswith("v://"):
            continue
        grouped.setdefault(boq_item_uri, []).append(row)

    items: list[dict[str, Any]] = []
    total_design = 0.0
    total_settled = 0.0
    total_consumed = 0.0
    total_approved = 0.0

    for boq_item_uri, bucket in grouped.items():
        bucket.sort(key=lambda r: _to_text(r.get("created_at") or ""))
        genesis_rows = []
        settlement_rows = []
        consume_rows = []
        candidate_rows = []
        for row in bucket:
            sd = _as_dict(row.get("state_data"))
            stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
            ptype = _to_text(row.get("proof_type") or "").strip().lower()
            if stage == "INITIAL" or ptype == "zero_ledger":
                genesis_rows.append(row)
            if stage == "SETTLEMENT" and _to_text(row.get("result") or "").strip().upper() == "PASS":
                settlement_rows.append(row)
            if stage == "INSTALLATION":
                consume_rows.append(row)
            if bool(row.get("spent")) is False and stage in {"INSTALLATION", "VARIATION"}:
                candidate_rows.append(row)

        genesis = genesis_rows[0] if genesis_rows else (bucket[0] if bucket else {})
        gsd = _as_dict(genesis.get("state_data"))
        design_qty = float(_effective_design_quantity(genesis, bucket))
        total_design += design_qty
        unit_price = _to_float(gsd.get("unit_price"))
        contract_qty = _to_float(gsd.get("contract_quantity"))
        if contract_qty is None:
            contract_qty = _to_float(gsd.get("approved_quantity"))
        approved_qty = _to_float(gsd.get("approved_quantity"))
        if approved_qty is not None:
            total_approved += approved_qty
        design_total = _to_float(gsd.get("design_total"))
        if design_total is None and unit_price is not None:
            design_total = float(unit_price) * float(_to_float(gsd.get("design_quantity")) or 0.0)
        contract_total = _to_float(gsd.get("contract_total"))
        if contract_total is None and unit_price is not None:
            contract_total = float(unit_price) * float(contract_qty or 0.0)

        settled_qty = 0.0
        if settlement_rows:
            for row in settlement_rows:
                settled_qty += _extract_settled_quantity(row, fallback_design=None)
            if settled_qty <= 0 and design_qty > 0:
                settled_qty = design_qty
        total_settled += settled_qty

        consumed_qty = 0.0
        if consume_rows:
            for row in consume_rows:
                consumed_qty += _extract_settled_quantity(row, fallback_design=None)
        total_consumed += consumed_qty

        latest_settlement = settlement_rows[-1] if settlement_rows else None
        latest_settlement_id = _to_text((latest_settlement or {}).get("proof_id") or "").strip()

        sign_candidate = candidate_rows[-1] if candidate_rows else None
        sign_ready = False
        sign_block_reason = "no_installation_candidate"
        sign_candidate_id = _to_text((sign_candidate or {}).get("proof_id") or "").strip()
        gate = {}
        if sign_candidate_id:
            try:
                agg = aggregate_provenance_chain_fn(sign_candidate_id)
                gate = _as_dict(agg.get("gate"))
                sign_ready = not bool(gate.get("blocked"))
                sign_block_reason = ""
                if not sign_ready:
                    sign_block_reason = f"gate_locked:{_to_text(gate.get('reason') or '')}"
            except Exception as exc:
                sign_ready = False
                sign_block_reason = f"gate_check_failed:{exc.__class__.__name__}"

        baseline_qty = approved_qty if (approved_qty is not None and approved_qty > 0) else (contract_qty or design_qty)
        progress = 0.0
        if baseline_qty > 1e-9:
            progress = max(0.0, min(1.0, settled_qty / baseline_qty))

        item_no = _item_no_from_boq_uri(boq_item_uri)
        unit_price_val = round(unit_price or 0.0, 4)
        design_total_val = round(design_total or 0.0, 4)
        contract_total_val = round(contract_total or 0.0, 4)
        contract_qty_val = contract_qty if contract_qty is not None else (approved_qty or 0.0)
        items.append(
            {
                "boq_item_uri": boq_item_uri,
                "item_no": item_no,
                "item_name": _to_text(gsd.get("item_name") or ""),
                "unit": _to_text(gsd.get("unit") or ""),
                "design_quantity": round(design_qty, 4),
                "approved_quantity": round(approved_qty or 0.0, 4),
                "contract_quantity": round(contract_qty_val, 4),
                "unit_price": unit_price_val,
                "design_total": design_total_val,
                "contract_total": contract_total_val,
                "settled_quantity": round(settled_qty, 4),
                "consumed_quantity": round(consumed_qty, 4),
                "remaining_quantity": round(max(0.0, design_qty - settled_qty), 4),
                "consumption_rate": round(progress, 6),
                "consumption_percent": round(progress * 100.0, 2),
                "progress_percent": round(progress * 100.0, 2),
                "settlement_count": len(settlement_rows),
                "latest_settlement_proof_id": latest_settlement_id,
                "latest_settlement_at": _to_text((latest_settlement or {}).get("created_at") or ""),
                "proof_chain_view": f"/v1/proof/docfinal/context?boq_item_uri={boq_item_uri}",
                "sign_ready": sign_ready,
                "sign_block_reason": sign_block_reason,
                "sign_candidate_proof_id": sign_candidate_id,
                "gate": gate,
            }
        )

    def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
        code = _to_text(item.get("item_no") or "")
        nums = [int(x) for x in re.findall(r"\d+", code)]
        return (nums[0] if nums else 9999, code)

    items.sort(key=_sort_key)

    project_progress = 0.0
    baseline_total = total_approved if total_approved > 1e-9 else total_design
    if baseline_total > 1e-9:
        project_progress = max(0.0, min(1.0, total_settled / baseline_total))

    return {
        "ok": True,
        "project_uri": _to_text(project_uri),
        "summary": {
            "boq_item_count": len(items),
            "design_total": round(total_design, 6),
            "approved_total": round(total_approved, 6),
            "settled_total": round(total_settled, 6),
            "consumed_total": round(total_consumed, 6),
            "progress_percent": round(project_progress * 100.0, 2),
        },
        "items": items,
    }


__all__ = ["build_boq_realtime_status"]
