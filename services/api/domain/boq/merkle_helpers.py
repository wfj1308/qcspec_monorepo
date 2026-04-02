"""Merkle snapshot flow helpers for BOQ/unit views."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.boq.merkle import build_unit_merkle_snapshot


def get_unit_merkle_root_flow(
    *,
    project_uri: str,
    unit_code: str,
    proof_id: str,
    max_rows: int,
    sb: Client,
) -> dict[str, Any]:
    return build_unit_merkle_snapshot(
        sb=sb,
        project_uri=project_uri,
        unit_code=unit_code,
        proof_id=proof_id,
        max_rows=max_rows,
    )
