"""
Query helpers for proof UTXO operations.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from supabase import Client


def get_unspent_rows(
    *,
    sb: Client,
    project_uri: str,
    proof_type: Optional[str],
    result: Optional[str],
    segment_uri: Optional[str],
    limit: int,
    normalize_type: Callable[[str], str],
    normalize_result: Callable[[str], str],
) -> List[Dict[str, Any]]:
    q = sb.table("proof_utxo").select("*").eq("project_uri", project_uri).eq("spent", False).limit(
        max(1, min(limit, 500))
    )
    if proof_type:
        q = q.eq("proof_type", normalize_type(proof_type))
    if result:
        q = q.eq("result", normalize_result(result))
    if segment_uri:
        q = q.eq("segment_uri", segment_uri)
    res = q.execute()
    return res.data or []


def get_by_id_row(*, sb: Client, proof_id: str) -> Optional[Dict[str, Any]]:
    res = sb.table("proof_utxo").select("*").eq("proof_id", proof_id).limit(1).execute()
    data = res.data or []
    return data[0] if data else None


def get_chain_rows(
    *,
    proof_id: str,
    max_depth: int,
    get_by_id: Callable[[str], Optional[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    chain: List[Dict[str, Any]] = []
    seen: set[str] = set()
    current_id = str(proof_id)
    while current_id and len(chain) < max_depth and current_id not in seen:
        seen.add(current_id)
        current = get_by_id(current_id)
        if not current:
            break
        chain.append(current)
        current_id = str(current.get("parent_proof_id") or "")
    return list(reversed(chain))
