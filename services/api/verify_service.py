"""
Verify data access service helpers.
services/api/verify_service.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from supabase import Client


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return str(value)


def _parse_dt_for_sort(value: Any) -> datetime:
    text = _to_text(value).strip()
    if not text:
        return datetime.min
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized).replace(tzinfo=None)
    except Exception:
        return datetime.min


def get_proof_ancestry(
    engine: Any,
    proof_id: str,
    *,
    max_depth: int = 128,
    _seen: set[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively trace parent_proof_id upward until initial_import or root.
    Returns ancestry ordered from root -> current proof.
    """
    current_id = _to_text(proof_id).strip()
    if not current_id or max_depth <= 0:
        return []

    seen = _seen or set()
    if current_id in seen:
        return []
    seen.add(current_id)

    row = engine.get_by_id(current_id)
    if not isinstance(row, dict):
        return []

    proof_type = _to_text(row.get("proof_type") or "").strip().lower()
    parent_id = _to_text(row.get("parent_proof_id") or "").strip()

    if proof_type == "initial_import" or not parent_id:
        return [row]

    parent_chain = get_proof_ancestry(engine, parent_id, max_depth=max_depth - 1, _seen=seen)
    return parent_chain + [row]


def get_proof_descendants(
    engine: Any,
    proof_id: str,
    *,
    max_depth: int = 8,
    max_nodes: int = 256,
) -> list[dict[str, Any]]:
    """
    Breadth-first descendants traversal (children -> deeper descendants).
    Ordered by created_at ascending.
    """
    root_id = _to_text(proof_id).strip()
    if not root_id:
        return []

    queue: list[tuple[str, int]] = [(root_id, 0)]
    seen: set[str] = {root_id}
    out: list[dict[str, Any]] = []

    while queue and len(out) < max_nodes:
        node_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        try:
            children = (
                engine.sb.table("proof_utxo")
                .select("*")
                .eq("parent_proof_id", node_id)
                .order("created_at", desc=False)
                .limit(200)
                .execute()
                .data
                or []
            )
        except Exception:
            children = []

        for child in children:
            cid = _to_text((child or {}).get("proof_id") or "").strip()
            if not cid or cid in seen:
                continue
            seen.add(cid)
            out.append(child)
            queue.append((cid, depth + 1))
            if len(out) >= max_nodes:
                break

    out.sort(key=lambda row: _parse_dt_for_sort(row.get("created_at")))
    return out


def get_project_name_by_id(
    sb: Client,
    project_id: str,
    *,
    default: str = "-",
) -> str:
    pid = _to_text(project_id).strip()
    if not pid:
        return default
    try:
        res = (
            sb.table("projects")
            .select("id,name")
            .eq("id", pid)
            .limit(1)
            .execute()
        )
    except Exception:
        return default
    data = res.data or []
    if not data:
        return default
    return _to_text((data[0] or {}).get("name") or default) or default


def list_photos_for_inspection(
    sb: Client,
    inspection_id: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    iid = _to_text(inspection_id).strip()
    if not iid:
        return []
    try:
        rows = (
            sb.table("photos")
            .select("*")
            .eq("inspection_id", iid)
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 500)))
            .execute()
            .data
            or []
        )
    except Exception:
        return []
    return [row for row in rows if isinstance(row, dict)]
