"""Provenance-chain aggregation helper for TripRole."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    to_text as _to_text,
)
from services.api.domain.execution.lineage.triprole_lineage import (
    _build_provenance_nodes,
    _gate_lock,
    _resolve_boq_item_uri,
)
from services.api.domain.execution.triprole_common import (
    sha256_json as _sha256_json,
)


def build_provenance_aggregate(
    *,
    utxo_id: str,
    sb: Any,
    max_depth: int = 256,
    get_chain_fn: Callable[..., list[dict[str, Any]]],
    build_provenance_nodes_fn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] = _build_provenance_nodes,
    sha256_json_fn: Callable[[Any], str] = _sha256_json,
    gate_lock_fn: Callable[[list[dict[str, Any]]], dict[str, Any]] = _gate_lock,
    resolve_boq_item_uri_fn: Callable[[dict[str, Any]], str] = _resolve_boq_item_uri,
) -> dict[str, Any]:
    normalized = _to_text(utxo_id).strip()
    if not normalized:
        raise HTTPException(400, "utxo_id is required")

    chain_rows = get_chain_fn(normalized, max_depth=max_depth)
    if not chain_rows:
        raise HTTPException(404, "proof chain not found")

    nodes = build_provenance_nodes_fn(chain_rows)
    total_proof_hash = sha256_json_fn(
        [
            {
                "proof_id": node.get("proof_id"),
                "proof_hash": node.get("proof_hash"),
                "parent_proof_id": node.get("parent_proof_id"),
                "parent_hash": node.get("parent_hash"),
                "lifecycle_stage": node.get("lifecycle_stage"),
                "trip_action": node.get("trip_action"),
                "result": node.get("result"),
            }
            for node in nodes
        ]
    )

    latest = chain_rows[-1]
    latest_sd = _as_dict(latest.get("state_data"))
    gate = gate_lock_fn(nodes)

    return {
        "ok": True,
        "utxo_id": normalized,
        "root_proof_id": _to_text(chain_rows[0].get("proof_id") or "").strip(),
        "latest_proof_id": _to_text(latest.get("proof_id") or "").strip(),
        "project_uri": _to_text(latest.get("project_uri") or "").strip(),
        "segment_uri": _to_text(latest.get("segment_uri") or "").strip(),
        "boq_item_uri": resolve_boq_item_uri_fn(latest),
        "artifact_uri": _to_text(latest_sd.get("artifact_uri") or "").strip(),
        "chain_depth": len(nodes),
        "total_proof_hash": total_proof_hash,
        "nodes": nodes,
        "gate": gate,
    }


__all__ = ["build_provenance_aggregate"]
