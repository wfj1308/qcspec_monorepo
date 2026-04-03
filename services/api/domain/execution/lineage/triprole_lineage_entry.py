"""Lineage and asset-origin entry wiring."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.integrations import (
    ProofUTXOEngine,
    get_proof_chain,
)
from services.api.domain.execution.triprole_asset import (
    _resolve_latest_boq_row,
)
from services.api.domain.execution.lineage.triprole_asset_origin import (
    trace_asset_origin as _trace_asset_origin,
)
from services.api.domain.execution.lineage.triprole_full_lineage import (
    build_full_lineage as _build_full_lineage,
)
from services.api.domain.execution.lineage.triprole_provenance_aggregate import (
    build_provenance_aggregate as _build_provenance_aggregate,
)


def aggregate_provenance_chain(
    *,
    utxo_id: str,
    sb: Any,
    max_depth: int = 256,
) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    return _build_provenance_aggregate(
        utxo_id=utxo_id,
        sb=sb,
        max_depth=max_depth,
        get_chain_fn=lambda normalized_utxo_id, chain_max_depth: engine.get_chain(
            normalized_utxo_id,
            max_depth=chain_max_depth,
        ),
    )


def get_full_lineage(
    *,
    utxo_id: str,
    sb: Any,
    max_depth: int = 256,
    aggregate_provenance_chain_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    return _build_full_lineage(
        utxo_id=utxo_id,
        sb=sb,
        max_depth=max_depth,
        aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
        get_proof_chain_fn=lambda boq_uri, supabase: get_proof_chain(boq_uri, supabase),
        get_chain_fn=lambda normalized_utxo_id, chain_max_depth: engine.get_chain(
            normalized_utxo_id,
            max_depth=chain_max_depth,
        ),
    )


def trace_asset_origin(
    *,
    sb: Any,
    utxo_id: str = "",
    boq_item_uri: str = "",
    project_uri: str = "",
    max_depth: int = 512,
    get_boq_realtime_status_fn: Callable[[Any, str, int], dict[str, Any]],
) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    return _trace_asset_origin(
        sb=sb,
        utxo_id=utxo_id,
        boq_item_uri=boq_item_uri,
        project_uri=project_uri,
        max_depth=max_depth,
        get_by_id_fn=lambda proof_id: engine.get_by_id(proof_id),
        get_chain_fn=lambda proof_id, depth: engine.get_chain(proof_id, max_depth=depth),
        get_proof_chain_fn=lambda item_uri, supabase, depth: get_proof_chain(item_uri, supabase, max_depth=depth),
        resolve_latest_boq_row_fn=lambda supabase, item_uri, scoped_project: _resolve_latest_boq_row(
            sb=supabase,
            boq_item_uri=item_uri,
            project_uri=scoped_project,
        ),
        get_boq_realtime_status_fn=lambda supabase, scoped_project, limit: get_boq_realtime_status_fn(
            supabase,
            scoped_project,
            limit,
        ),
    )
