"""DocFinal runtime orchestration helpers for chain loading and optional side-effects."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    to_float as _to_float,
    to_text as _to_text,
)


def load_docfinal_chain(
    *,
    boq_item_uri: str,
    sb: Any,
    project_meta: dict[str, Any] | None,
    load_chain: Callable[[str, Any], list[dict[str, Any]]],
) -> tuple[str, list[dict[str, Any]]]:
    normalized_uri = _to_text(boq_item_uri).strip()
    if not normalized_uri:
        raise HTTPException(400, "boq_item_uri is required")

    chain = load_chain(normalized_uri, sb) or []
    if not chain:
        raise HTTPException(404, "no proof chain found for boq_item_uri")

    scoped_project_uri = _to_text((project_meta or {}).get("project_uri") or "").strip()
    if scoped_project_uri:
        scoped_chain = [row for row in chain if _to_text((row or {}).get("project_uri") or "").strip() == scoped_project_uri]
        if scoped_chain:
            chain = scoped_chain

    return normalized_uri, chain


def resolve_docfinal_lineage_and_asset_origin(
    *,
    latest_proof_id: str,
    sb: Any,
    boq_item_uri: str,
    project_uri: str,
    get_full_lineage: Callable[[str, Any], dict[str, Any]],
    trace_asset_origin: Callable[..., dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    proof_id = _to_text(latest_proof_id).strip()
    if not proof_id:
        return None, None

    lineage_snapshot: dict[str, Any] | None = None
    asset_origin: dict[str, Any] | None = None

    try:
        lineage_snapshot = get_full_lineage(proof_id, sb)
    except Exception:
        lineage_snapshot = None

    try:
        asset_origin = trace_asset_origin(
            sb=sb,
            utxo_id=proof_id,
            boq_item_uri=_to_text(boq_item_uri).strip(),
            project_uri=_to_text(project_uri).strip(),
        )
    except Exception:
        asset_origin = None

    return lineage_snapshot, asset_origin


def resolve_docfinal_transfer_receipt(
    *,
    apply_asset_transfer: bool,
    sb: Any,
    transfer_amount: float | None,
    latest_row: dict[str, Any],
    boq_item_uri: str,
    transfer_executor_uri: str,
    verify_uri: str,
    settled_quantity: Callable[[dict[str, Any]], float | None],
    transfer_asset: Callable[..., dict[str, Any]],
) -> dict[str, Any] | None:
    if not apply_asset_transfer:
        return None

    resolved_amount = _to_float(transfer_amount)
    if resolved_amount is None or resolved_amount <= 0:
        resolved_amount = _to_float(settled_quantity(latest_row))

    normalized_item_uri = _to_text(boq_item_uri).strip()
    if resolved_amount is None or resolved_amount <= 0:
        return {
            "ok": False,
            "error": "no_valid_transfer_amount",
            "item_id": normalized_item_uri,
            "amount": resolved_amount,
        }

    try:
        return transfer_asset(
            sb=sb,
            item_id=normalized_item_uri,
            amount=float(resolved_amount),
            executor_uri=transfer_executor_uri,
            executor_role="DOCPEG",
            docpeg_proof_id=_to_text(latest_row.get("proof_id") or "").strip(),
            docpeg_hash=_to_text(latest_row.get("proof_hash") or "").strip(),
            project_uri=_to_text(latest_row.get("project_uri") or "").strip(),
            metadata={
                "source": "docpeg_package",
                "boq_item_uri": normalized_item_uri,
                "verify_uri": _to_text(verify_uri).strip(),
            },
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{exc.__class__.__name__}: {exc}",
            "item_id": normalized_item_uri,
            "amount": float(resolved_amount),
        }


__all__ = [
    "load_docfinal_chain",
    "resolve_docfinal_lineage_and_asset_origin",
    "resolve_docfinal_transfer_receipt",
]
