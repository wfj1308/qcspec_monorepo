"""Storage/persistence helper functions for SMU orchestration."""

from __future__ import annotations

from typing import Any

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    to_text as _to_text,
)


def patch_state_data(sb: Any, proof_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    rows = (
        sb.table("proof_utxo")
        .select("state_data")
        .eq("proof_id", proof_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return {}
    sd = _as_dict(rows[0].get("state_data"))
    sd.update(patch)
    sb.table("proof_utxo").update({"state_data": sd}).eq("proof_id", proof_id).execute()
    return sd


def boq_rows(
    sb: Any,
    *,
    project_uri: str,
    boq_item_uri: str = "",
    only_unspent: bool = False,
    limit: int = 50000,
) -> list[dict[str, Any]]:
    q = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", project_uri)
        .order("created_at", desc=False)
        .limit(max(1, min(limit, 50000)))
    )
    if only_unspent:
        q = q.eq("spent", False)
    rows = q.execute().data or []
    if boq_item_uri:
        uri = boq_item_uri.rstrip("/")
        out: list[dict[str, Any]] = []
        for row in rows:
            seg = _to_text(row.get("segment_uri") or "").strip().rstrip("/")
            sd = _as_dict(row.get("state_data"))
            item_uri = _to_text(sd.get("boq_item_uri") or seg).strip().rstrip("/")
            if item_uri == uri or seg == uri:
                out.append(row)
        rows = out
    return [x for x in rows if isinstance(x, dict)]


def latest_unspent_leaf(sb: Any, *, project_uri: str, boq_item_uri: str) -> dict[str, Any]:
    rows = boq_rows(sb, project_uri=project_uri, boq_item_uri=boq_item_uri, only_unspent=True, limit=20000)
    if not rows:
        return {}
    rows.sort(key=lambda r: _to_text(r.get("created_at") or ""))
    return rows[-1]


__all__ = [
    "boq_rows",
    "latest_unspent_leaf",
    "patch_state_data",
]

