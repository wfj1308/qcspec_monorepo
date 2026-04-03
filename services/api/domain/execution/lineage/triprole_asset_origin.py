"""Asset origin trace helpers for TripRole execution."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    safe_path_token as _safe_path_token,
    sha256_json as _sha256_json,
    to_float as _to_float,
    to_text as _to_text,
)
from services.api.domain.execution.lineage.triprole_lineage import (
    _extract_settled_quantity,
    _item_no_from_boq_uri,
    _resolve_boq_item_uri,
    _smu_id_from_item_no,
)


def _resolve_contract_quantity_from_row(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    ledger = _as_dict(sd.get("ledger"))
    for candidate in (
        sd.get("contract_quantity"),
        sd.get("approved_quantity"),
        sd.get("design_quantity"),
        _as_dict(sd.get("genesis_proof")).get("contract_quantity"),
        _as_dict(sd.get("genesis_proof")).get("initial_quantity"),
        ledger.get("initial_balance"),
    ):
        num = _to_float(candidate)
        if num is not None:
            return float(num)
    return 0.0


def _variation_delta_from_row(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    variation = _as_dict(sd.get("variation"))
    delta_utxo = _as_dict(sd.get("delta_utxo"))
    ledger = _as_dict(sd.get("ledger"))
    for candidate in (
        variation.get("delta_amount"),
        variation.get("delta_quantity"),
        variation.get("change_amount"),
        delta_utxo.get("delta_amount"),
        ledger.get("last_delta_amount"),
    ):
        num = _to_float(candidate)
        if num is not None:
            return float(num)
    return 0.0


def _variation_reference_from_row(row: dict[str, Any]) -> dict[str, Any]:
    sd = _as_dict(row.get("state_data"))
    variation = _as_dict(sd.get("variation"))
    meta = _as_dict(variation.get("metadata"))

    def _pick(*keys: str) -> str:
        for key in keys:
            text = _to_text(variation.get(key) or meta.get(key) or sd.get(key) or "").strip()
            if text:
                return text
        return ""

    ref_no = _pick(
        "design_change_no",
        "change_order_no",
        "change_no",
        "variation_order_no",
        "document_no",
        "reference_no",
    )
    ref_date = _pick(
        "design_change_date",
        "change_date",
        "approved_at",
        "verified_at",
    ) or _to_text(row.get("created_at") or "").strip()
    reason = _pick("reason", "description", "change_reason")
    return {
        "reference_no": ref_no,
        "reference_date": ref_date,
        "reason": reason,
    }


def _format_qty(value: float) -> str:
    text = f"{float(value):.4f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def trace_asset_origin(
    *,
    sb: Any,
    utxo_id: str = "",
    boq_item_uri: str = "",
    project_uri: str = "",
    max_depth: int = 512,
    get_by_id_fn: Callable[[str], dict[str, Any] | None],
    get_chain_fn: Callable[[str, int], list[dict[str, Any]]],
    get_proof_chain_fn: Callable[[str, Any, int], list[dict[str, Any]]],
    resolve_latest_boq_row_fn: Callable[[Any, str, str], dict[str, Any] | None],
    get_boq_realtime_status_fn: Callable[[Any, str, int], dict[str, Any]],
) -> dict[str, Any]:
    """Trace quantity origin: contract(genesis) -> variation deltas -> measured(settlement)."""
    normalized_utxo = _to_text(utxo_id).strip()
    normalized_boq = _to_text(boq_item_uri).strip()
    normalized_project = _to_text(project_uri).strip()
    if not normalized_utxo and not normalized_boq:
        raise HTTPException(400, "utxo_id or boq_item_uri is required")

    latest: dict[str, Any] | None = None
    if normalized_utxo:
        latest = get_by_id_fn(normalized_utxo)
    if latest and not normalized_boq:
        normalized_boq = _resolve_boq_item_uri(latest)
    if not latest and normalized_boq:
        latest = resolve_latest_boq_row_fn(sb, normalized_boq, normalized_project)
    if not latest:
        raise HTTPException(404, "asset origin trace target not found")
    if not normalized_boq:
        normalized_boq = _resolve_boq_item_uri(latest)
    if not normalized_boq:
        raise HTTPException(404, "boq_item_uri cannot be resolved for lineage trace")

    chain_rows = get_proof_chain_fn(normalized_boq, sb, max_depth)
    if normalized_project:
        scoped = [x for x in chain_rows if _to_text((x or {}).get("project_uri") or "").strip() == normalized_project]
        if scoped:
            chain_rows = scoped
    if not chain_rows and normalized_utxo:
        chain_rows = get_chain_fn(normalized_utxo, max_depth)
    if not chain_rows:
        raise HTTPException(404, "proof chain not found for asset origin trace")
    chain_rows.sort(key=lambda row: _to_text((row or {}).get("created_at") or ""))

    genesis = next(
        (
            row
            for row in chain_rows
            if _to_text((row or {}).get("proof_type") or "").strip().lower() == "zero_ledger"
            or _to_text(_as_dict((row or {}).get("state_data")).get("lifecycle_stage") or "").strip().upper() == "INITIAL"
        ),
        chain_rows[0],
    )
    genesis_id = _to_text(genesis.get("proof_id") or "").strip()
    contract_qty = _resolve_contract_quantity_from_row(genesis)
    if contract_qty <= 1e-12:
        scoped_project_for_baseline = _to_text(latest.get("project_uri") or normalized_project).strip()
        if scoped_project_for_baseline:
            try:
                status = get_boq_realtime_status_fn(sb, scoped_project_for_baseline, 10000)
                matched = next(
                    (
                        _as_dict(x)
                        for x in _as_list(status.get("items"))
                        if _to_text(_as_dict(x).get("boq_item_uri") or "").strip() == normalized_boq
                    ),
                    {},
                )
                contract_qty = (
                    _to_float(matched.get("contract_quantity"))
                    or _to_float(matched.get("approved_quantity"))
                    or _to_float(matched.get("design_quantity"))
                    or contract_qty
                )
                contract_qty = float(contract_qty or 0.0)
            except Exception:
                contract_qty = float(contract_qty or 0.0)

    variation_sources: list[dict[str, Any]] = []
    total_variation_delta = 0.0
    for row in chain_rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
        action = _to_text(sd.get("trip_action") or "").strip().lower()
        if stage != "VARIATION" and action not in {"variation.record", "variation.delta.apply"}:
            continue
        delta = _variation_delta_from_row(row)
        if abs(delta) <= 1e-12:
            continue
        total_variation_delta += float(delta)
        ref = _variation_reference_from_row(row)
        variation_sources.append(
            {
                "proof_id": _to_text(row.get("proof_id") or "").strip(),
                "delta_quantity": round(float(delta), 6),
                "reference_no": _to_text(ref.get("reference_no") or "").strip(),
                "reference_date": _to_text(ref.get("reference_date") or "").strip(),
                "reason": _to_text(ref.get("reason") or "").strip(),
                "verified": _to_text(row.get("result") or "").strip().upper() == "PASS",
                "created_at": _to_text(row.get("created_at") or "").strip(),
            }
        )
    variation_sources.sort(key=lambda x: _to_text(x.get("created_at") or ""))

    settlement_rows = [
        row
        for row in chain_rows
        if _to_text(_as_dict((row or {}).get("state_data")).get("lifecycle_stage") or "").strip().upper() == "SETTLEMENT"
        and _to_text((row or {}).get("result") or "").strip().upper() == "PASS"
    ]
    measured_qty = 0.0
    if settlement_rows:
        for row in settlement_rows:
            measured_qty += _extract_settled_quantity(row, fallback_design=None)
    if measured_qty <= 1e-12:
        measured_qty = _extract_settled_quantity(chain_rows[-1], fallback_design=contract_qty)
    if measured_qty <= 1e-12:
        scoped_project_for_settled = _to_text(latest.get("project_uri") or normalized_project).strip()
        if scoped_project_for_settled:
            try:
                status = get_boq_realtime_status_fn(sb, scoped_project_for_settled, 10000)
                matched = next(
                    (
                        _as_dict(x)
                        for x in _as_list(status.get("items"))
                        if _to_text(_as_dict(x).get("boq_item_uri") or "").strip() == normalized_boq
                    ),
                    {},
                )
                measured_qty = float(_to_float(matched.get("settled_quantity")) or measured_qty)
            except Exception:
                pass

    delta_vs_contract = float(measured_qty - contract_qty)
    unexplained_delta = float(delta_vs_contract - total_variation_delta)

    item_no = _item_no_from_boq_uri(normalized_boq)
    smu_id = _smu_id_from_item_no(item_no)
    scoped_project = _to_text(latest.get("project_uri") or normalized_project).strip()
    lineage_base = scoped_project.rstrip("/") if scoped_project.startswith("v://") else "v://lineage"
    lineage_path: list[dict[str, Any]] = []
    for idx, row in enumerate(chain_rows, start=1):
        sd = _as_dict(row.get("state_data"))
        stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
        proof_id = _to_text(row.get("proof_id") or "").strip()
        lineage_path.append(
            {
                "index": idx,
                "proof_id": proof_id,
                "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                "stage": stage or _to_text(row.get("proof_type") or "").strip().upper(),
                "action": _to_text(sd.get("trip_action") or "").strip().lower(),
                "result": _to_text(row.get("result") or "").strip().upper(),
                "created_at": _to_text(row.get("created_at") or "").strip(),
                "lineage_uri": f"{lineage_base}/lineage/{_safe_path_token(item_no or 'item', fallback='item')}/{idx:03d}",
            }
        )

    highlighted = None
    if variation_sources:
        highlighted = max(variation_sources, key=lambda x: abs(float(x.get("delta_quantity") or 0.0)))

    statement = (
        f"本表实测量为 {_format_qty(measured_qty)}，合同量 {_format_qty(contract_qty)}，差异 {_format_qty(delta_vs_contract)}。"
    )
    if highlighted:
        ref_no = _to_text(highlighted.get("reference_no") or "设计变更单").strip()
        ref_date = _to_text(highlighted.get("reference_date") or "").strip()
        ver = "已验真" if bool(highlighted.get("verified")) else "待复核"
        statement += (
            f" 其中 {_format_qty(float(highlighted.get('delta_quantity') or 0.0))} "
            f"来自于 {ref_date or '-'} 的 {ref_no}（{ver}）。"
        )

    payload = {
        "ok": True,
        "project_uri": scoped_project,
        "smu_id": smu_id,
        "boq_item_uri": normalized_boq,
        "item_no": item_no,
        "latest_proof_id": _to_text(chain_rows[-1].get("proof_id") or "").strip(),
        "genesis_utxo_id": genesis_id,
        "contract_quantity": round(contract_qty, 6),
        "measured_quantity": round(float(measured_qty), 6),
        "delta_vs_contract": round(delta_vs_contract, 6),
        "variation_total_delta": round(total_variation_delta, 6),
        "unexplained_delta": round(unexplained_delta, 6),
        "variation_sources": variation_sources,
        "lineage_path": lineage_path,
        "lineage_uri": f"{lineage_base}/lineage/{_safe_path_token(item_no or 'item', fallback='item')}/",
        "statement": statement,
    }
    payload["lineage_proof_hash"] = _sha256_json(
        {
            "project_uri": payload["project_uri"],
            "boq_item_uri": payload["boq_item_uri"],
            "latest_proof_id": payload["latest_proof_id"],
            "genesis_utxo_id": payload["genesis_utxo_id"],
            "contract_quantity": payload["contract_quantity"],
            "measured_quantity": payload["measured_quantity"],
            "delta_vs_contract": payload["delta_vs_contract"],
            "variation_sources": payload["variation_sources"],
        }
    )
    return payload


__all__ = ["trace_asset_origin"]
