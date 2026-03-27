"""QCSpec proof routes.
services/api/routers/proof.py
"""

from typing import Any, Optional
from uuid import UUID
import uuid
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field
from supabase import Client, create_client

from .proof_utxo_engine import ProofUTXOEngine

router = APIRouter()


def get_supabase() -> Client:
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


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


def _utxo_to_legacy_row(row: dict) -> dict:
    return {
        "proof_id": row.get("proof_id"),
        "proof_hash": row.get("proof_hash"),
        "v_uri": (row.get("state_data") or {}).get("v_uri") or row.get("project_uri"),
        "object_type": row.get("proof_type"),
        "action": "consume" if row.get("spent") else "create",
        "summary": f"{row.get('proof_type')}:{row.get('result')}",
        "created_at": row.get("created_at"),
    }


class UTXOCreateBody(BaseModel):
    proof_id: Optional[str] = None
    owner_uri: str
    project_uri: str
    project_id: Optional[str] = None
    segment_uri: Optional[str] = None
    proof_type: str = "inspection"
    result: str = "PENDING"
    state_data: dict = Field(default_factory=dict)
    conditions: list = Field(default_factory=list)
    parent_proof_id: Optional[str] = None
    norm_uri: Optional[str] = None
    signer_uri: Optional[str] = None
    signer_role: str = "AI"
    gitpeg_anchor: Optional[str] = None


class UTXOConsumeBody(BaseModel):
    input_proof_ids: list
    output_states: list
    executor_uri: str
    executor_role: str = "AI"
    trigger_action: Optional[str] = None
    trigger_data: dict = Field(default_factory=dict)
    tx_type: str = "consume"


class UTXOAutoSettleBody(BaseModel):
    inspection_proof_id: str
    executor_uri: str
    executor_role: str = "AI"
    trigger_action: str = "railpact.settle"
    anchor_config: Optional[dict[str, Any]] = None


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
        # Fallback to proof_utxo if proof_chain is unavailable.
        try:
            proj = (
                sb.table("projects")
                .select("v_uri")
                .eq("id", project_id)
                .limit(1)
                .execute()
            )
            rows = []
            if proj.data:
                engine = ProofUTXOEngine(sb)
                rows = [_utxo_to_legacy_row(x) for x in engine.get_unspent(project_uri=proj.data[0]["v_uri"], limit=limit)]
            return {"data": rows, "count": len(rows)}
        except Exception:
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
        res = None

    if not res or not res.data:
        try:
            utxo = ProofUTXOEngine(sb).get_by_id(proof_id)
        except Exception:
            utxo = None
        if not utxo:
            return {"valid": False, "proof": None, "message": "Proof not found."}
        anchor = str(utxo.get("gitpeg_anchor") or "").strip()
        anchor_status = "anchored" if anchor and anchor != "待锚定" else "pending"
        return {
            "valid": True,
            "proof_id": proof_id,
            "proof_hash": utxo.get("proof_hash"),
            "v_uri": (utxo.get("state_data") or {}).get("v_uri") or utxo.get("project_uri"),
            "project_uri": utxo.get("project_uri"),
            "segment_uri": utxo.get("segment_uri"),
            "object_type": utxo.get("proof_type"),
            "action": "consume" if utxo.get("spent") else "create",
            "summary": f"{utxo.get('proof_type')}:{utxo.get('result')}",
            "created_at": utxo.get("created_at"),
            "chain_length": int(utxo.get("depth") or 0) + 1,
            "gitpeg_anchor": anchor or None,
            "anchor_status": anchor_status,
            "message": "Proof verified via proof_utxo.",
        }

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

    utxo_extra = {}
    try:
        utxo = ProofUTXOEngine(sb).get_by_id(proof_id)
    except Exception:
        utxo = None
    if isinstance(utxo, dict):
        anchor = str(utxo.get("gitpeg_anchor") or "").strip()
        utxo_extra = {
            "project_uri": utxo.get("project_uri"),
            "segment_uri": utxo.get("segment_uri"),
            "proof_hash": utxo.get("proof_hash"),
            "gitpeg_anchor": anchor or None,
            "anchor_status": "anchored" if anchor and anchor != "待锚定" else "pending",
        }

    return {
        "valid": hash_valid,
        "proof_id": proof_id,
        "proof_hash": proof.get("proof_hash"),
        "v_uri": proof.get("v_uri"),
        "object_type": proof.get("object_type"),
        "action": proof.get("action"),
        "summary": proof.get("summary"),
        "created_at": proof.get("created_at"),
        "chain_length": chain_count,
        "message": "Proof verified." if hash_valid else "Proof hash mismatch.",
        **utxo_extra,
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


@router.get("/utxo/unspent")
async def list_unspent_utxo(
    project_uri: str,
    proof_type: Optional[str] = None,
    result: Optional[str] = None,
    segment_uri: Optional[str] = None,
    limit: int = 200,
    sb: Client = Depends(get_supabase),
):
    rows = ProofUTXOEngine(sb).get_unspent(
        project_uri=project_uri,
        proof_type=proof_type,
        result=result,
        segment_uri=segment_uri,
        limit=limit,
    )
    return {"data": rows, "count": len(rows)}


@router.post("/utxo/create")
async def create_utxo(body: UTXOCreateBody, sb: Client = Depends(get_supabase)):
    proof_id = str(body.proof_id or f"GP-PROOF-{uuid.uuid4().hex[:16].upper()}")
    row = ProofUTXOEngine(sb).create(
        proof_id=proof_id,
        owner_uri=body.owner_uri,
        project_id=body.project_id,
        project_uri=body.project_uri,
        segment_uri=body.segment_uri,
        proof_type=body.proof_type,
        result=body.result,
        state_data=body.state_data or {},
        conditions=body.conditions or [],
        parent_proof_id=body.parent_proof_id,
        norm_uri=body.norm_uri,
        signer_uri=body.signer_uri,
        signer_role=body.signer_role,
        gitpeg_anchor=body.gitpeg_anchor,
    )
    return row


@router.post("/utxo/consume")
async def consume_utxo(body: UTXOConsumeBody, sb: Client = Depends(get_supabase)):
    tx = ProofUTXOEngine(sb).consume(
        input_proof_ids=[str(x) for x in (body.input_proof_ids or [])],
        output_states=list(body.output_states or []),
        executor_uri=body.executor_uri,
        executor_role=body.executor_role,
        trigger_action=body.trigger_action,
        trigger_data=body.trigger_data or {},
        tx_type=body.tx_type,
    )
    return tx


@router.post("/utxo/auto/inspection-settle")
async def auto_settle_from_inspection(body: UTXOAutoSettleBody, sb: Client = Depends(get_supabase)):
    result = ProofUTXOEngine(sb).auto_consume_inspection_pass(
        inspection_proof_id=body.inspection_proof_id,
        executor_uri=body.executor_uri,
        executor_role=body.executor_role,
        trigger_action=body.trigger_action,
        anchor_config=body.anchor_config or {},
    )
    return result


@router.get("/utxo/{proof_id}")
async def get_utxo(proof_id: str, sb: Client = Depends(get_supabase)):
    row = ProofUTXOEngine(sb).get_by_id(proof_id)
    if not row:
        raise HTTPException(404, "proof_utxo not found")
    return row


@router.get("/utxo/{proof_id}/chain")
async def get_utxo_chain(proof_id: str, sb: Client = Depends(get_supabase)):
    chain = ProofUTXOEngine(sb).get_chain(proof_id)
    if not chain:
        raise HTTPException(404, "proof chain not found")
    return {"proof_id": proof_id, "depth": len(chain), "chain": chain}


@router.get("/utxo/transactions/list")
async def list_utxo_transactions(
    project_uri: Optional[str] = None,
    limit: int = 100,
    sb: Client = Depends(get_supabase),
):
    q = (
        sb.table("proof_transaction")
        .select("*")
        .order("created_at", desc=True)
        .limit(max(1, min(limit, 500)))
    )
    rows = q.execute().data or []
    if project_uri:
        filtered = []
        engine = ProofUTXOEngine(sb)
        for tx in rows:
            outputs = tx.get("output_proofs") or []
            matched = False
            for pid in outputs:
                row = engine.get_by_id(str(pid))
                if row and row.get("project_uri") == project_uri:
                    matched = True
                    break
            if matched:
                filtered.append(tx)
        rows = filtered
    return {"data": rows, "count": len(rows)}
