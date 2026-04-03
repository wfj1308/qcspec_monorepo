"""Realtime-status query orchestration for TripRole BOQ views."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    to_text as _to_text,
)
from services.api.domain.execution.realtime.triprole_realtime_status import (
    build_boq_realtime_status,
)


def fetch_boq_realtime_status(
    *,
    sb: Any,
    project_uri: str,
    limit: int = 2000,
    aggregate_provenance_chain_fn: Callable[[str], dict[str, Any]],
    build_boq_realtime_status_fn: Callable[..., dict[str, Any]] = build_boq_realtime_status,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .order("created_at", desc=False)
            .limit(max(1, min(limit, 10000)))
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to load proof_utxo: {exc}") from exc

    return build_boq_realtime_status_fn(
        rows=rows,
        project_uri=normalized_project_uri,
        aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
    )


__all__ = ["fetch_boq_realtime_status"]
