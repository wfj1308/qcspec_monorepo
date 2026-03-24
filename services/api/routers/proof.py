"""QCSpec proof routes.
services/api/routers/proof.py
"""

from typing import Optional
from uuid import UUID
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError
from supabase import Client, create_client

router = APIRouter()


def get_supabase() -> Client:
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _run_with_retry(fn, retries: int = 1):
    last_err = None
    for _ in range(retries + 1):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout) as e:
            last_err = e
            continue
    if last_err:
        raise last_err


@router.get("/")
async def list_proofs(
    project_id: str,
    v_uri: Optional[str] = None,
    limit: int = 50,
    sb: Client = Depends(get_supabase),
):
    """List proof records for a project."""
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    def _query():
        q = (
            sb.table("proof_chain")
            .select("proof_id,proof_hash,v_uri,object_type,action,summary,created_at")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 200)))
        )
        if v_uri:
            q = q.eq("v_uri", v_uri)
        return q.execute()

    try:
        res = _run_with_retry(_query, retries=1)
        rows = res.data or []
        return {"data": rows, "count": len(rows)}
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        raise HTTPException(502, "Failed to query proof chain.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        # Keep UI responsive during transient upstream errors.
        return {"data": [], "count": 0}


@router.get("/verify/{proof_id}")
async def verify_proof(
    proof_id: str,
    sb: Client = Depends(get_supabase),
):
    """Verify proof hash and return proof details."""
    try:
        res = _run_with_retry(
            lambda: sb.table("proof_chain").select("*").eq("proof_id", proof_id).single().execute(),
            retries=1,
        )
    except (APIError, httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        return {"valid": False, "proof": None, "message": "Proof verify failed, please retry."}

    if not res.data:
        return {"valid": False, "proof": None, "message": "Proof not found."}

    proof = res.data
    expected_hash = str(proof_id).replace("GP-PROOF-", "").lower()
    hash_valid = proof.get("proof_hash") == expected_hash

    try:
        chain_len = _run_with_retry(
            lambda: sb.table("proof_chain").select("proof_id", count="exact").eq("v_uri", proof.get("v_uri")).execute(),
            retries=1,
        )
        chain_count = chain_len.count or 0
    except Exception:
        chain_count = 0

    return {
        "valid": hash_valid,
        "proof_id": proof_id,
        "v_uri": proof.get("v_uri"),
        "object_type": proof.get("object_type"),
        "action": proof.get("action"),
        "summary": proof.get("summary"),
        "created_at": proof.get("created_at"),
        "chain_length": chain_count,
        "message": "Proof verified." if hash_valid else "Proof hash mismatch.",
    }


@router.get("/node-tree")
async def get_node_tree(
    root_uri: str,
    sb: Client = Depends(get_supabase),
):
    """List v:// nodes under a root URI."""
    try:
        res = _run_with_retry(
            lambda: sb.table("v_nodes")
            .select("uri,parent_uri,node_type,peg_count,status")
            .like("uri", f"{root_uri}%")
            .order("uri")
            .execute(),
            retries=1,
        )
        return {"data": res.data or [], "root": root_uri}
    except Exception:
        return {"data": [], "root": root_uri}


@router.get("/stats/{project_id}")
async def proof_stats(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    """Proof statistics for a project."""
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    try:
        res = _run_with_retry(
            lambda: sb.table("proof_chain").select("object_type, action").eq("project_id", project_id).execute(),
            retries=1,
        )
        rows = res.data or []
    except Exception:
        rows = []

    by_type = {}
    by_action = {}
    for row in rows:
        object_type = row.get("object_type")
        action = row.get("action")
        if object_type:
            by_type[object_type] = by_type.get(object_type, 0) + 1
        if action:
            by_action[action] = by_action.get(action, 0) + 1

    return {
        "total": len(rows),
        "by_type": by_type,
        "by_action": by_action,
    }
