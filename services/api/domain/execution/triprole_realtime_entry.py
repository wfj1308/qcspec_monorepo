"""Realtime status entry wiring."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.triprole_realtime_query import (
    fetch_boq_realtime_status as _fetch_boq_realtime_status,
)
from services.api.domain.execution.triprole_realtime_status import (
    build_boq_realtime_status as _build_boq_realtime_status,
)


def get_boq_realtime_status(
    *,
    sb: Any,
    project_uri: str,
    limit: int = 2000,
    aggregate_provenance_chain_fn: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    return _fetch_boq_realtime_status(
        sb=sb,
        project_uri=project_uri,
        limit=limit,
        aggregate_provenance_chain_fn=aggregate_provenance_chain_fn,
        build_boq_realtime_status_fn=_build_boq_realtime_status,
    )
