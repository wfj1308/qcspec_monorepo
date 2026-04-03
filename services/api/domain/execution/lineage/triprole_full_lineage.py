"""Full-lineage aggregation helper for one BOQ asset branch."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)
from services.api.domain.execution.lineage.triprole_lineage import (
    _collect_evidence_hashes_from_row,
    _collect_norm_refs_from_row,
    _extract_qc_conclusion,
)


def build_full_lineage(
    *,
    utxo_id: str,
    sb: Any,
    max_depth: int = 256,
    aggregate_provenance_chain_fn: Callable[..., dict[str, Any]],
    get_proof_chain_fn: Callable[..., list[dict[str, Any]]],
    get_chain_fn: Callable[..., list[dict[str, Any]]],
    collect_norm_refs_from_row_fn: Callable[[dict[str, Any]], list[str]] = _collect_norm_refs_from_row,
    collect_evidence_hashes_from_row_fn: Callable[[dict[str, Any]], list[dict[str, Any]]] = _collect_evidence_hashes_from_row,
    extract_qc_conclusion_fn: Callable[[dict[str, Any]], dict[str, Any]] = _extract_qc_conclusion,
) -> dict[str, Any]:
    agg = aggregate_provenance_chain_fn(utxo_id=utxo_id, sb=sb, max_depth=max_depth)
    boq_item_uri = _to_text(agg.get("boq_item_uri") or "").strip()

    rows: list[dict[str, Any]] = []
    if boq_item_uri.startswith("v://"):
        rows = get_proof_chain_fn(boq_item_uri, sb)
    if not rows:
        rows = get_chain_fn(_to_text(utxo_id).strip(), max_depth=max_depth)

    project_uri = _to_text(agg.get("project_uri") or "").strip()
    if project_uri:
        scoped_rows = [row for row in rows if _to_text((row or {}).get("project_uri") or "").strip() == project_uri]
        if scoped_rows:
            rows = scoped_rows

    norm_refs: set[str] = set()
    evidence_hashes: list[dict[str, Any]] = []
    qc_conclusions: list[dict[str, Any]] = []
    signatures: list[dict[str, Any]] = []
    spatiotemporal_anchors: list[dict[str, Any]] = []
    seen_anchor_hash: set[str] = set()
    seen_signature_hash: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        for uri in collect_norm_refs_from_row_fn(row):
            norm_refs.add(uri)
        evidence_hashes.extend(collect_evidence_hashes_from_row_fn(row))
        qc_conclusions.append(extract_qc_conclusion_fn(row))
        anchor_hash = _to_text(sd.get("spatiotemporal_anchor_hash") or "").strip()
        if anchor_hash and anchor_hash not in seen_anchor_hash:
            seen_anchor_hash.add(anchor_hash)
            spatiotemporal_anchors.append(
                {
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "spatiotemporal_anchor_hash": anchor_hash,
                    "geo_location": _as_dict(sd.get("geo_location")),
                    "server_timestamp_proof": _as_dict(sd.get("server_timestamp_proof")),
                    "trip_action": _to_text(sd.get("trip_action") or "").strip().lower(),
                    "created_at": _to_text(row.get("created_at") or "").strip(),
                }
            )
        consensus = _as_dict(sd.get("consensus"))
        for item in _as_list(consensus.get("signatures")):
            if not isinstance(item, dict):
                continue
            sig_hash = _to_text(item.get("signature_hash") or "").strip().lower()
            if not sig_hash or sig_hash in seen_signature_hash:
                continue
            seen_signature_hash.add(sig_hash)
            signatures.append(item)

    qc_conclusions.sort(key=lambda x: _to_text(x.get("created_at") or ""))
    evidence_hashes.sort(key=lambda x: (_to_text(x.get("proof_id") or ""), _to_text(x.get("hash") or "")))

    return {
        **agg,
        "norm_refs": sorted(norm_refs),
        "evidence_hashes": evidence_hashes,
        "qc_conclusions": qc_conclusions,
        "consensus_signatures": signatures,
        "spatiotemporal_anchors": spatiotemporal_anchors,
    }


__all__ = ["build_full_lineage"]
